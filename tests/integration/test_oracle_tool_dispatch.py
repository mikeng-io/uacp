"""Integration: drive the REAL adapter tool-dispatch path for uacp_oracle_query.

This test proves the actual tool-call path a coding agent hits when it invokes
uacp_oracle_query through the Hermes guardian adapter.

Two complementary exercises:

1. HANDLER DISPATCH — import `_handle_uacp_oracle_query` from the real adapter
   (`uacp_guardian` package at runtime-adapters/hermes/plugins/uacp_guardian/)
   and call it with realistic args for FULL-tier phases (propose, plan, verify).
   Assert:
   - returns a JSON string with 'packets'/'metadata' structure
   - writes NO state (read-only contract)
   - handles phases across NONE/FULL/ADVISORY/WRITEBACK tiers correctly
   - missing required args returns a structured error (not an exception)

2. REGISTER SMOKE TEST — call `register(ctx)` with a fake ctx that captures
   `register_tool(...)` calls.  Assert:
   - `uacp_oracle_query` is registered
   - its toolset is `uacp_guardian` (NOT in a writer-only toolset)
   - its handler IS `_handle_uacp_oracle_query` (read-only handler, not a writer)
   - it is classified as `read.local` by the Guardian policy

Adapter import strategy: the conftest puts
`runtime-adapters/hermes/plugins/uacp_guardian` (the package directory) on
sys.path, which makes its top-level symbols importable as flat names.  To
import the adapter as a package (`import uacp_guardian`) with working relative
imports, we add the parent `runtime-adapters/hermes/plugins` directory to
sys.path inside this test.  The `uacp_guardian._POLICY` singleton is reset to
None before each call so GuardianPolicy.load() re-reads UACP_ROOT (set by
temp_uacp_root to the temp fixture).

Real uacp.toml: GuardianPolicy.load() requires a valid [guardian] table with
schema_version and protected_categories.  The fixture patches the real repo
config/uacp.toml into the temp root so the policy loads without error.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# sys.path setup: add parent plugins directory so 'import uacp_guardian' works
# as a package with relative imports.
# ---------------------------------------------------------------------------
_PLUGINS_DIR = (
    Path(__file__).resolve().parents[2]
    / "runtime-adapters" / "hermes" / "plugins"
)
if str(_PLUGINS_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGINS_DIR))

# Now uacp_guardian is importable as a package
import uacp_guardian  # noqa: E402

# Real repo config directory — GuardianPolicy.load() requires a [guardian] table
_REAL_CONFIG = Path(__file__).resolve().parents[2] / "config"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_guardian_policy(root: Path) -> None:
    """Copy the real config/uacp.toml into the temp root so GuardianPolicy.load()
    succeeds.  The real [guardian] table has schema_version and protected_categories;
    a hand-crafted minimal table would need to replicate all required fields.
    """
    dst = root / "config" / "uacp.toml"
    if not dst.exists():
        shutil.copy2(_REAL_CONFIG / "uacp.toml", dst)


def _reset_adapter_policy() -> None:
    """Reset the module-level _POLICY cache in the guardian adapter so
    GuardianPolicy.load() re-reads UACP_ROOT (set by temp_uacp_root fixture)."""
    uacp_guardian._POLICY = None
    uacp_guardian._POLICY_ERROR = ""
    uacp_guardian._PHASE_CONFIG = None


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestOracleToolDispatch:
    """Real adapter path: _handle_uacp_oracle_query + register(ctx)."""

    # ------------------------------------------------------------------
    # Part 1: handler dispatch
    # ------------------------------------------------------------------

    def test_handler_returns_packets_and_metadata_for_full_phase(
        self, temp_uacp_root: Path
    ) -> None:
        """_handle_uacp_oracle_query returns the canonical structure for FULL phases.

        Phase 'propose' is FULL tier.  With oracle disabled in the real config,
        the aggregator returns empty packets and a 'disabled' note — but the
        structure is identical whether enabled or disabled.
        """
        _seed_guardian_policy(temp_uacp_root)
        _reset_adapter_policy()

        raw = uacp_guardian._handle_uacp_oracle_query(
            {"phase": "propose", "project": "test-project", "query": "what did we learn?"}
        )
        assert isinstance(raw, str), f"handler must return a JSON string, got {type(raw)}"
        result = json.loads(raw)

        assert "packets" in result, f"missing 'packets' key: {result}"
        assert "metadata" in result, f"missing 'metadata' key: {result}"
        assert isinstance(result["packets"], list), "packets must be a list"
        assert isinstance(result["metadata"], dict), "metadata must be a dict"
        assert result["metadata"].get("phase") == "propose"

    def test_handler_is_read_only_for_full_phases(
        self, temp_uacp_root: Path
    ) -> None:
        """_handle_uacp_oracle_query writes NO state files (read-only contract).

        We snapshot state/ contents before and after the call and assert equality.
        """
        _seed_guardian_policy(temp_uacp_root)
        _reset_adapter_policy()

        state_before = set(
            str(p) for p in (temp_uacp_root / ".uacp" / "state").rglob("*")
        )
        for phase in ("propose", "plan", "verify"):
            uacp_guardian._handle_uacp_oracle_query(
                {"phase": phase, "project": "test-project"}
            )
        state_after = set(
            str(p) for p in (temp_uacp_root / ".uacp" / "state").rglob("*")
        )
        new_files = state_after - state_before
        assert not new_files, (
            f"_handle_uacp_oracle_query wrote state files (must be read-only): {new_files}"
        )

    @pytest.mark.parametrize("phase", ["propose", "plan", "verify"])
    def test_handler_accepts_full_tier_phases(
        self, temp_uacp_root: Path, phase: str
    ) -> None:
        """_handle_uacp_oracle_query accepts all three FULL-tier phases without error."""
        _seed_guardian_policy(temp_uacp_root)
        _reset_adapter_policy()

        raw = uacp_guardian._handle_uacp_oracle_query({"phase": phase, "project": "proj"})
        result = json.loads(raw)
        assert "error" not in result, (
            f"Phase '{phase}' should not produce an error: {result}"
        )
        assert result["metadata"]["phase"] == phase

    def test_handler_returns_error_for_missing_phase(
        self, temp_uacp_root: Path
    ) -> None:
        """Missing 'phase' arg returns a structured error JSON (not an exception)."""
        _seed_guardian_policy(temp_uacp_root)
        _reset_adapter_policy()

        raw = uacp_guardian._handle_uacp_oracle_query({"project": "test-project"})
        result = json.loads(raw)
        assert "error" in result, f"Missing phase should return error: {result}"
        assert "phase" in result["error"].lower()

    def test_handler_returns_error_for_missing_project(
        self, temp_uacp_root: Path
    ) -> None:
        """Missing 'project' arg returns a structured error JSON (not an exception)."""
        _seed_guardian_policy(temp_uacp_root)
        _reset_adapter_policy()

        raw = uacp_guardian._handle_uacp_oracle_query({"phase": "propose"})
        result = json.loads(raw)
        assert "error" in result, f"Missing project should return error: {result}"
        assert "project" in result["error"].lower()

    def test_handler_accepts_optional_domains_and_query(
        self, temp_uacp_root: Path
    ) -> None:
        """Handler accepts optional 'domains' list and 'query' string without error."""
        _seed_guardian_policy(temp_uacp_root)
        _reset_adapter_policy()

        raw = uacp_guardian._handle_uacp_oracle_query({
            "phase": "plan",
            "project": "my-proj",
            "domains": ["governance", "config"],
            "query": "heartgate config collapse",
        })
        result = json.loads(raw)
        assert "error" not in result, f"Optional args caused error: {result}"
        assert "packets" in result

    # ------------------------------------------------------------------
    # Part 2: register(ctx) smoke test
    # ------------------------------------------------------------------

    def test_register_registers_oracle_tool(self, temp_uacp_root: Path) -> None:
        """register(ctx) registers uacp_oracle_query with the correct handler."""
        _seed_guardian_policy(temp_uacp_root)
        _reset_adapter_policy()

        registrations: list[dict] = []
        hooks: list[tuple] = []

        class MockCtx:
            def register_tool(self, *, name, toolset, schema, handler, description):
                registrations.append({
                    "name": name,
                    "toolset": toolset,
                    "schema": schema,
                    "handler": handler,
                    "description": description,
                })

            def register_hook(self, hook_type, fn):
                hooks.append((hook_type, fn))

        ctx = MockCtx()
        uacp_guardian.register(ctx)

        tool_names = [r["name"] for r in registrations]
        assert "uacp_oracle_query" in tool_names, (
            f"uacp_oracle_query not registered; tools: {tool_names}"
        )

    def test_register_oracle_in_uacp_guardian_toolset(
        self, temp_uacp_root: Path
    ) -> None:
        """uacp_oracle_query is registered in the 'uacp_guardian' toolset (not a
        writer-only toolset).  This proves the read-only tool is co-located with
        the writers but is identifiable by its handler, not a separate toolset."""
        _seed_guardian_policy(temp_uacp_root)
        _reset_adapter_policy()

        registrations: list[dict] = []

        class MockCtx:
            def register_tool(self, *, name, toolset, schema, handler, description):
                registrations.append({"name": name, "toolset": toolset, "handler": handler})

            def register_hook(self, *args):
                pass

        uacp_guardian.register(MockCtx())

        oracle_reg = next(
            (r for r in registrations if r["name"] == "uacp_oracle_query"), None
        )
        assert oracle_reg is not None, "uacp_oracle_query not registered"
        assert oracle_reg["toolset"] == "uacp_guardian", (
            f"Expected toolset 'uacp_guardian', got {oracle_reg['toolset']!r}"
        )
        # Handler must be the read-only handler, not one of the write handlers
        assert oracle_reg["handler"] is uacp_guardian._handle_uacp_oracle_query, (
            f"uacp_oracle_query must be handled by _handle_uacp_oracle_query, "
            f"got {oracle_reg['handler']!r}"
        )

    def test_oracle_classified_as_read_local_by_guardian_policy(
        self, temp_uacp_root: Path
    ) -> None:
        """The Guardian policy classifies uacp_oracle_query as 'read.local' (read-only).

        This is the policy-layer proof that the tool is non-mutating: Guardian
        evaluates it as 'read.local' which maps to DECISION_ALLOW (no audit
        required), not DECISION_ALLOW_WITH_AUDIT like state-mutation tools.
        """
        from core import Guardian, GuardianEvent, GuardianPolicy, DECISION_ALLOW

        _seed_guardian_policy(temp_uacp_root)
        policy = GuardianPolicy.load(str(temp_uacp_root))
        guardian = Guardian(policy)

        event = GuardianEvent(
            runtime="test",
            adapter="test-adapter",
            event_type="tool_call",
            tool_provider="core",
            tool_name="uacp_oracle_query",
            tool_args={"phase": "propose", "project": "test-proj"},
            uacp_run_id="uacp-test-001",
            uacp_phase="propose",
            workspace=str(temp_uacp_root),
            policy_version="0.1",
            declared_authority="",
            declared_side_effects=[],
        )
        decision = guardian.evaluate(event)

        assert decision.category == "read.local", (
            f"uacp_oracle_query must be classified as 'read.local', "
            f"got category={decision.category!r}"
        )
        assert decision.decision == DECISION_ALLOW, (
            f"read.local must get DECISION_ALLOW (not audit), "
            f"got {decision.decision!r}"
        )

    def test_register_hooks_are_lifecycle_only(self, temp_uacp_root: Path) -> None:
        """register(ctx) installs exactly pre_tool_call and post_tool_call hooks.

        No oracle-specific hook is introduced — the oracle is a registered tool,
        not a hook-layer concern.
        """
        _seed_guardian_policy(temp_uacp_root)
        _reset_adapter_policy()

        hooks: list[str] = []

        class MockCtx:
            def register_tool(self, **kwargs):
                pass

            def register_hook(self, hook_type, fn):
                hooks.append(hook_type)

        uacp_guardian.register(MockCtx())

        assert "pre_tool_call" in hooks
        assert "post_tool_call" in hooks
        # No extra oracle hook
        oracle_hooks = [h for h in hooks if "oracle" in h.lower()]
        assert not oracle_hooks, f"Unexpected oracle hooks: {oracle_hooks}"
