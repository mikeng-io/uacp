"""Codeflair MCP server — the agent-facing delivery face (P7, 12-delivery face #3).

Exposes codeflair's **read-only** query (blast radius / heatmap / gaps) as a single MCP tool
returning the canonical ``{nodes, gaps, trace}`` JSON. Any agent runtime (Claude Code, kimi,
opencode) calls it through the bundled ``.mcp.json``.

The ``mcp`` package is an **optional** dependency (absent in the dev venv), so its import is
guarded — importing this module never fails. The substance, :func:`run_query`, is dep-free
and tested directly; the live MCP wrapper :func:`build_server` is gated behind ``mcp`` being
installed (the live-boot test ``importorskip``\\s it, mirroring the tree-sitter/serena pattern).
"""

from __future__ import annotations

from typing import Any

from codeflair.cli import query_to_json

try:
    # Optional dep (codeflair[mcp]); absent in the dev venv. The gated import stays unresolved
    # there, exactly like the tree-sitter floor — see the root pyright config note.
    from mcp.server.fastmcp import FastMCP  # pyright: ignore[reportMissingImports]

    _HAVE_MCP = True
except ImportError:  # pragma: no cover - dep-presence branch
    FastMCP = None
    _HAVE_MCP = False

SERVER_NAME = "codeflair"
TOOL_NAME = "query"
TOOL_DESCRIPTION = (
    "Codeflair read-only code-intelligence query. Given a seed symbol (id or human "
    "substring), return the ranked blast-radius heatmap, first-class test gaps, and a "
    "replayable watermarked trace as canonical JSON ({nodes, gaps, trace}). Read-only: it "
    "never mutates the index or any governed state."
)


def run_query(
    seed: str,
    repo: str = ".",
    k: int = 20,
    max_hops: int = 3,
    direction: str = "callers",
) -> str:
    """The MCP tool's substance: a **read-only** codeflair query -> canonical JSON. Dep-free
    (no ``mcp`` import), so it is exercised directly by the suite without the MCP runtime."""
    return query_to_json(repo, seed, k=k, max_hops=max_hops, direction=direction)


def build_server() -> Any:  # pragma: no cover - exercised only when mcp is installed
    """Construct the FastMCP server with the ``query`` tool registered. Raises if the optional
    ``mcp`` package is not installed (the CLI's ``mcp`` subcommand surfaces the message)."""
    if not _HAVE_MCP or FastMCP is None:
        raise RuntimeError(
            "the 'mcp' package is not installed; install it with `pip install codeflair[mcp]` "
            "to run the codeflair MCP server"
        )
    server = FastMCP(SERVER_NAME)
    server.tool(name=TOOL_NAME, description=TOOL_DESCRIPTION)(run_query)
    return server
