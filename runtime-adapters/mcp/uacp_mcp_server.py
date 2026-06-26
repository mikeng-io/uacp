"""Runtime-neutral MCP stdio server exposing UACP's governed tools.

This adapter is the Model Context Protocol binding for the runtime-neutral
governed-tool registry (`skills/uacp-core/scripts/tool_specs.py`). It exposes
the same governed tools the Hermes adapter registers, sourced from the
single-source-of-truth `tool_specs()`, over an MCP stdio transport. Each tool's
hand-written bare JSON `input_schema` is forwarded verbatim as the MCP
`inputSchema`, and each tool's handler (which returns a JSON string) is invoked
directly.

CONTAINMENT NOTE — Guardian is intentionally NOT re-run here. The governed-tool
handlers self-enforce their own filesystem containment (path-bounded writers,
read-only checks, attestation validation for contained shell). The Guardian
*policy* gate (pre-tool-call boundary enforcement) is delivered separately as an
MCP PreToolUse hook in the host runtime and is out of scope for this server: a
stdio MCP server has no privileged position to enforce policy on its own tool
calls beyond what each handler already guarantees. This server is a thin,
faithful exposure of `tool_specs()` over MCP — nothing more.

Run as a script: ``python runtime-adapters/mcp/uacp_mcp_server.py`` (blocks on
stdio). Requires ``mcp`` plus the kernel's core runtime deps (pydantic, pyyaml,
jsonschema). When launched as a Claude Code plugin, ``.claude-plugin/plugin.json``
self-provisions all of these via ``uv run --no-project --with ...`` (the one host
prerequisite is ``uv`` on PATH); for a manual/dev run use ``pip install -e ".[mcp]"``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import anyio

# ---------------------------------------------------------------------------
# sys.path setup — mirror the parents-relative inserts in the Hermes adapter
# (runtime-adapters/hermes/plugins/uacp_guardian/__init__.py). This file lives
# at runtime-adapters/mcp/, so the repo root is parents[2].
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
_CORE_SCRIPTS = _REPO_ROOT / "skills" / "uacp-core" / "scripts"
_STATE_SCRIPTS = _REPO_ROOT / "skills" / "uacp-state" / "scripts"
for _p in (_CORE_SCRIPTS, _STATE_SCRIPTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import mcp.types as types  # noqa: E402  (import follows sys.path setup)
from mcp.server.lowlevel import Server  # noqa: E402
from mcp.server.stdio import stdio_server  # noqa: E402

from tool_specs import ToolSpec, tool_specs  # noqa: E402


def _specs_by_name() -> dict[str, ToolSpec]:
    return {spec.name: spec for spec in tool_specs()}


server: Server = Server("uacp")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Expose every governed tool with its bare JSON input schema verbatim."""
    return [
        types.Tool(
            name=spec.name,
            description=spec.description,
            inputSchema=spec.input_schema,
        )
        for spec in tool_specs()
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    """Dispatch a governed-tool call to its registry handler.

    The handler returns a JSON string, which is surfaced as a single text
    content block. An unknown tool name raises ``ValueError``; the MCP SDK
    surfaces that as an ``isError`` result.
    """
    spec = _specs_by_name().get(name)
    if spec is None:
        raise ValueError(f"unknown tool: {name}")
    result = spec.handler(arguments or {})
    return [types.TextContent(type="text", text=result)]


async def main() -> None:
    """Run the server over stdio until the client disconnects."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    anyio.run(main)
