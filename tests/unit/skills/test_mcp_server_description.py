"""D-12: the MCP server exposes each tool's RICH ``schema_description`` (which
carries the tool's preconditions), falling back to the short ``description`` only
when a spec lacks one.

Before D-12 the server passed ``description=spec.description`` — the short
register_tool label — so an MCP client never saw the precondition-bearing text
that the Hermes wire form already carries. These tests drive the real
``list_tools()`` coroutine and assert the richer field is what ships, plus prove
the ``or`` fallback path for a spec with no schema_description.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / "runtime-adapters" / "mcp"))
sys.path.insert(0, str(_REPO_ROOT / "skills" / "uacp-core" / "scripts"))
sys.path.insert(0, str(_REPO_ROOT / "skills" / "uacp-state" / "scripts"))

import uacp_mcp_server as server  # noqa: E402
from tool_specs import tool_specs  # noqa: E402


def _exposed() -> dict[str, str]:
    tools = asyncio.run(server.list_tools())
    return {t.name: t.description for t in tools}


def test_server_ships_schema_description_not_short_label() -> None:
    exposed = _exposed()
    specs = {s.name: s for s in tool_specs()}
    for name, description in exposed.items():
        assert description == specs[name].schema_description, name


def test_rich_description_differs_from_short_label() -> None:
    # A concrete spec whose two descriptions differ — proves the RICH one ships.
    exposed = _exposed()
    spec = next(s for s in tool_specs() if s.name == "uacp_run_transition")
    assert spec.schema_description != spec.description
    assert exposed["uacp_run_transition"] == spec.schema_description
    assert "structural gates" in exposed["uacp_run_transition"]


def test_falls_back_to_short_description_when_schema_description_absent(monkeypatch) -> None:
    # A stand-in spec with an EMPTY schema_description exercises the `or` fallback.
    fake = SimpleNamespace(
        name="uacp_fake_tool",
        description="SHORT-LABEL",
        schema_description="",
        input_schema={"type": "object", "properties": {"x": {"type": "string"}}},
    )
    monkeypatch.setattr(server, "tool_specs", lambda: [fake])
    exposed = _exposed()
    assert exposed["uacp_fake_tool"] == "SHORT-LABEL"
