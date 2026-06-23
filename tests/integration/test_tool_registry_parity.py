"""Integration: prove MCP-exposed tools == Hermes-registered tools.

Both adapters consume the single-source-of-truth ``tool_specs()`` registry, so
the tool surface they expose must be identical. This guard fails loudly if a
future change makes one adapter diverge from the other (e.g. a tool registered
in Hermes but not surfaced over MCP, or a schema edited on one side only).

Construction:
  * HERMES SIDE — call ``register(MockCtx)`` on the real Hermes adapter and
    collect each registered tool's name, bare input schema (unwrapped from the
    Hermes ``{name, description, parameters}`` envelope), handler identity,
    description, toolset, and read_only flag (read_only/toolset come from the
    registry, since Hermes does not re-emit them per-registration).
  * MCP SIDE — read the same fields straight off ``tool_specs()``.

No ``mcp`` runtime is needed for this comparison — both sides derive from
``tool_specs()`` / the Hermes ``register`` path, which depend only on
pydantic + pyyaml. (The MCP *server* import is exercised separately in
test_mcp_server.py behind its own importorskip guard.)
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Import the Hermes adapter as a package (relative imports) — mirror the path
# setup in test_oracle_tool_dispatch.py.
_PLUGINS_DIR = _REPO_ROOT / "runtime-adapters" / "hermes" / "plugins"
if str(_PLUGINS_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGINS_DIR))

import uacp_guardian  # noqa: E402
from tool_specs import tool_specs  # noqa: E402

_REAL_CONFIG = _REPO_ROOT / "config"


def _seed_guardian_policy(root: Path) -> None:
    dst = root / "config" / "uacp.toml"
    if not dst.exists():
        shutil.copy2(_REAL_CONFIG / "uacp.toml", dst)


def _reset_adapter_policy() -> None:
    uacp_guardian._POLICY = None
    uacp_guardian._POLICY_ERROR = ""
    uacp_guardian._PHASE_CONFIG = None


def _hermes_registrations(temp_uacp_root: Path) -> dict[str, dict]:
    """Run register(MockCtx) and return {name: {schema, handler, description, toolset}}."""
    _seed_guardian_policy(temp_uacp_root)
    _reset_adapter_policy()

    registrations: dict[str, dict] = {}

    class MockCtx:
        def register_tool(self, *, name, toolset, schema, handler, description):
            registrations[name] = {
                "toolset": toolset,
                "schema": schema,
                "handler": handler,
                "description": description,
            }

        def register_hook(self, *_args):
            pass

    uacp_guardian.register(MockCtx())
    return registrations


class TestToolRegistryParity:
    def test_tool_name_sets_match(self, temp_uacp_root: Path) -> None:
        hermes = _hermes_registrations(temp_uacp_root)
        mcp_names = {s.name for s in tool_specs()}
        assert set(hermes) == mcp_names, (
            f"tool-name divergence between Hermes and MCP: {set(hermes) ^ mcp_names}"
        )
        assert len(mcp_names) == 12, f"expected 12 governed tools, got {len(mcp_names)}"

    def test_bare_input_schemas_match(self, temp_uacp_root: Path) -> None:
        """Each spec's bare input_schema equals the Hermes wrapped 'parameters'."""
        hermes = _hermes_registrations(temp_uacp_root)
        for spec in tool_specs():
            wrapped = hermes[spec.name]["schema"]
            assert wrapped["parameters"] == spec.input_schema, (
                f"input schema diverges for {spec.name}"
            )

    def test_handler_identity_matches(self, temp_uacp_root: Path) -> None:
        """The registered Hermes handler IS the registry handler object."""
        hermes = _hermes_registrations(temp_uacp_root)
        for spec in tool_specs():
            assert hermes[spec.name]["handler"] is spec.handler, (
                f"handler identity diverges for {spec.name}"
            )

    def test_descriptions_match(self, temp_uacp_root: Path) -> None:
        hermes = _hermes_registrations(temp_uacp_root)
        for spec in tool_specs():
            assert hermes[spec.name]["description"] == spec.description, (
                f"register description diverges for {spec.name}"
            )

    def test_toolset_and_read_only_consistent(self, temp_uacp_root: Path) -> None:
        """Toolset matches the registry; read_only is the registry's source of truth.

        Hermes registration does not re-emit read_only per tool, so the read_only
        flag is asserted on the registry side (it is what the MCP adapter and the
        Guardian classification consume). Toolset must match what Hermes registers.
        """
        hermes = _hermes_registrations(temp_uacp_root)
        read_only_names = {s.name for s in tool_specs() if s.read_only}
        # The known read-only tools per the registry contract.
        assert read_only_names == {
            "uacp_oracle_query",
            "uacp_heartgate_check",
            "uacp_sandbox_check",
        }, f"unexpected read-only set: {read_only_names}"
        for spec in tool_specs():
            assert hermes[spec.name]["toolset"] == spec.toolset, (
                f"toolset diverges for {spec.name}"
            )
