"""P7 — the MCP delivery face (server module + bundled ``.mcp.json``).

The ``mcp`` package is optional (absent in the dev venv): the module's substance
(:func:`run_query`, the read-only query) is dep-free and tested directly; the live MCP boot
(:func:`build_server`) is gated behind ``importorskip("mcp")``.
"""

import json
import os

import pytest

from codeflair import Edge, Store, Symbol, mcp_server
from codeflair.store import default_store_path

_MCP_JSON = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".mcp.json")


def _seed_index(repo: str) -> None:
    db = default_store_path(repo, create=True)
    with Store(db) as s:
        s.add_symbol(Symbol(symbol="A", file="a.py", name="A", kind="func"))
        s.add_symbol(Symbol(symbol="B", file="b.py", name="B", kind="func"))
        s.add_edge(Edge("B", "A", "calls", "scip"))
        s.set_watermark("feed", "feed")
        s.commit()


def test_module_declares_the_query_tool():
    """STRUCTURE: the module names a read-only ``query`` tool with a description, regardless of
    whether the ``mcp`` runtime is installed."""
    assert mcp_server.SERVER_NAME == "codeflair"
    assert mcp_server.TOOL_NAME == "query"
    assert "read-only" in mcp_server.TOOL_DESCRIPTION.lower()
    assert callable(mcp_server.run_query)


def test_run_query_returns_the_json_contract(tmp_path):
    """The tool substance is the real read-only query: it returns the ``{nodes,gaps,trace}``
    contract with the seed's blast radius — exercised WITHOUT the mcp runtime (non-vacuous)."""
    repo = str(tmp_path)
    _seed_index(repo)
    doc = json.loads(mcp_server.run_query("A", repo=repo))
    assert set(doc) == {"nodes", "gaps", "trace"}
    assert "B" in [n["symbol"] for n in doc["nodes"]]


def test_build_server_without_mcp_raises():
    """When ``mcp`` is absent, ``build_server`` fails closed with an actionable message rather
    than importing a missing package."""
    if mcp_server._HAVE_MCP:
        pytest.skip("mcp is installed; the absent-dep branch is not exercisable here")
    with pytest.raises(RuntimeError, match="mcp"):
        mcp_server.build_server()


def test_bundled_mcp_json_is_wellformed_and_points_at_the_server():
    """The bundled ``.mcp.json`` registers codeflair's own MCP (via the CLI ``mcp`` subcommand)
    and Serena (the LSP layer, per 12-delivery)."""
    with open(_MCP_JSON, encoding="utf-8") as fh:
        cfg = json.load(fh)
    servers = cfg["mcpServers"]
    assert servers["codeflair"]["command"] == "codeflair"
    assert servers["codeflair"]["args"] == ["mcp"]
    assert servers["codeflair"]["type"] == "stdio"
    # Serena is bundled too (one install brings the lot) — the live LSP overlay layer.
    assert "serena" in servers
    assert servers["serena"]["command"] == "uvx"


def test_live_server_registers_the_query_tool():
    """GATED live boot: only when ``mcp`` is installed, the built server actually carries the
    ``query`` tool. Skipped in the dev venv (mcp absent), mirroring the tree-sitter pattern."""
    pytest.importorskip("mcp")
    server = mcp_server.build_server()
    # FastMCP exposes its registered tools via list_tools (async) or the tool manager; assert
    # the tool name is present without depending on a specific private attribute shape.
    names: set[str] = set()
    manager = getattr(server, "_tool_manager", None)
    if manager is not None and hasattr(manager, "list_tools"):
        names = {t.name for t in manager.list_tools()}
    assert mcp_server.TOOL_NAME in names
