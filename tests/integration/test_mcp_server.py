"""Integration: drive the runtime-neutral MCP stdio server in-memory.

These tests exercise the real MCP binding at
``runtime-adapters/mcp/uacp_mcp_server.py`` through the official ``mcp`` Python
SDK's in-memory transport (``create_connected_server_and_client_session``), so
no subprocess is spawned. The same governed-tool handlers a coding agent would
hit over stdio are driven directly.

The whole module is guarded by ``pytest.importorskip("mcp")`` so it skips
cleanly when the optional ``mcp`` dependency is absent — keeping the core suite
installable on pydantic + pyyaml alone.

Assertions:
  (a) ``tools/list`` exposes exactly ``{s.name for s in tool_specs()}`` and each
      returned ``inputSchema`` equals the spec's bare schema verbatim.
  (b) ``tools/call`` of the read-only ``uacp_oracle_query`` returns a JSON text
      payload and writes NO state files under the temp UACP root.
  (c) a writer (``uacp_gate_ledger_append``) called with valid args actually
      appends a record under the temp UACP root.
  (d) an unknown tool name yields ``result.isError is True``.

UACP-root staging mirrors test_oracle_tool_dispatch.py: the real
``config/uacp.toml`` is copied into the temp root so GuardianPolicy.load()
(invoked inside the writer handler) resolves policy correctly, and the adapter
policy singleton is reset before each call.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

# Skip the entire module (at collection time) when mcp is not installed.
pytest.importorskip("mcp")

import anyio  # noqa: E402
import mcp.types as types  # noqa: E402
from mcp.shared.memory import (  # noqa: E402
    create_connected_server_and_client_session as connect,
)

# Make the MCP adapter importable so we can reuse its `server` object directly.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_MCP_ADAPTER = _REPO_ROOT / "runtime-adapters" / "mcp"
if str(_MCP_ADAPTER) not in sys.path:
    sys.path.insert(0, str(_MCP_ADAPTER))

import uacp_mcp_server  # noqa: E402
from tool_specs import tool_specs  # noqa: E402

_REAL_CONFIG = _REPO_ROOT / "config"


@pytest.fixture
def anyio_backend() -> str:
    """Drive anyio-based async tests on the asyncio backend only."""
    return "asyncio"


def _seed_guardian_policy(root: Path) -> None:
    """Copy the real config/uacp.toml into the temp root so GuardianPolicy.load()
    (invoked by the governed writer handlers) succeeds."""
    dst = root / "config" / "uacp.toml"
    if not dst.exists():
        shutil.copy2(_REAL_CONFIG / "uacp.toml", dst)


def _reset_adapter_policy() -> None:
    """Reset the Hermes adapter policy singleton so handlers re-read UACP_ROOT.

    The governed handlers live in the neutral layer but the policy cache is on
    the Hermes adapter module; resetting it keeps cross-test isolation aligned
    with test_oracle_tool_dispatch.py.
    """
    try:
        import uacp_guardian

        uacp_guardian._POLICY = None
        uacp_guardian._POLICY_ERROR = ""
        uacp_guardian._PHASE_CONFIG = None
    except Exception:
        pass


@pytest.mark.anyio
async def test_list_tools_matches_registry(temp_uacp_root: Path) -> None:
    """(a) tools/list names == registry names; each inputSchema is verbatim."""
    _seed_guardian_policy(temp_uacp_root)
    _reset_adapter_policy()

    specs = {s.name: s for s in tool_specs()}
    async with connect(uacp_mcp_server.server) as client:
        listed = await client.list_tools()

    listed_names = {t.name for t in listed.tools}
    assert listed_names == set(specs), (
        f"MCP-exposed tool set mismatch: {listed_names ^ set(specs)}"
    )
    for tool in listed.tools:
        spec = specs[tool.name]
        assert tool.inputSchema == spec.input_schema, (
            f"inputSchema for {tool.name} not forwarded verbatim"
        )
        assert tool.description == spec.description


@pytest.mark.anyio
async def test_call_oracle_read_only_returns_json_and_writes_nothing(
    temp_uacp_root: Path,
) -> None:
    """(b) read-only uacp_oracle_query returns JSON text and writes no state."""
    _seed_guardian_policy(temp_uacp_root)
    _reset_adapter_policy()

    state_root = temp_uacp_root / ".uacp" / "state"
    before = {str(p) for p in state_root.rglob("*")}

    async with connect(uacp_mcp_server.server) as client:
        result = await client.call_tool(
            "uacp_oracle_query",
            {"phase": "propose", "project": "test-project", "query": "what did we learn?"},
        )

    assert result.isError is False, f"oracle call errored: {result.content}"
    assert result.content and isinstance(result.content[0], types.TextContent)
    payload = json.loads(result.content[0].text)
    assert "packets" in payload and "metadata" in payload
    assert payload["metadata"].get("phase") == "propose"

    after = {str(p) for p in state_root.rglob("*")}
    assert after == before, f"read-only oracle wrote state files: {after - before}"


@pytest.mark.anyio
async def test_call_writer_appends_to_gate_ledger(
    temp_uacp_root: Path, valid_run_id: str
) -> None:
    """(c) a writer call with valid args appends under the temp UACP root."""
    _seed_guardian_policy(temp_uacp_root)
    _reset_adapter_policy()

    ledger_path = (
        temp_uacp_root / ".uacp" / "state" / "gate-ledger" / f"{valid_run_id}.jsonl"
    )
    assert not ledger_path.exists()

    async with connect(uacp_mcp_server.server) as client:
        result = await client.call_tool(
            "uacp_gate_ledger_append",
            {
                "uacp_run_id": valid_run_id,
                "uacp_phase": "execute",
                # declared_side_effects is schema-typed as a string, so we pass a
                # string here (the handler only checks key presence). The Hermes
                # handler test passes [] because it bypasses JSON-schema validation;
                # the MCP SDK validates against inputSchema, so a string is required.
                "declared_side_effects": "append gate ledger record",
                "policy_version": "0.1",
                "workspace": str(temp_uacp_root),
                "gate": "EXECUTE->VERIFY",
                "record": {"result": "pass", "check": "ppv_1"},
                "authority_artifact": "plans/test-plan.yaml",
            },
        )

    assert result.isError is False, f"writer call errored: {result.content}"
    payload = json.loads(result.content[0].text)
    assert payload.get("ok") is True, f"writer did not succeed: {payload}"
    assert payload["gate"] == "EXECUTE->VERIFY"

    assert ledger_path.exists(), "gate ledger file was not created under temp root"
    lines = ledger_path.read_text().strip().split("\n")
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["gate"] == "EXECUTE->VERIFY"
    assert record["result"] == "pass"


@pytest.mark.anyio
async def test_unknown_tool_name_is_error(temp_uacp_root: Path) -> None:
    """(d) an unknown tool name surfaces as result.isError is True."""
    _seed_guardian_policy(temp_uacp_root)
    _reset_adapter_policy()

    async with connect(uacp_mcp_server.server) as client:
        result = await client.call_tool("uacp_definitely_not_a_tool", {})

    assert result.isError is True
    assert result.content and "unknown tool" in result.content[0].text.lower()


def test_module_anyio_run_smoke() -> None:
    """Sanity: the adapter exposes an awaitable main() and an anyio import.

    Does not run the stdio loop (that blocks); just asserts the wiring is present
    so a regression in the entrypoint is caught without spawning a process.
    """
    assert callable(uacp_mcp_server.main)
    assert hasattr(uacp_mcp_server, "anyio")
    assert anyio is not None
