"""Manifest-integrity: the MCP server manifests point at the real server file.

Pure JSON + path checks — no ``mcp`` runtime is needed. Parses ``.mcp.json``
(Claude Code) and ``kimi.plugin.json`` (Kimi Code) at the repo root and asserts:
  * each manifest declares a ``uacp`` MCP server;
  * the referenced server file resolves to
    ``runtime-adapters/mcp/uacp_mcp_server.py`` under the repo root and exists;
  * the host-specific path prefixes are correct (Claude Code uses the
    ``${CLAUDE_PLUGIN_ROOT}`` token; Kimi uses a ``./``-relative path with a
    ``./``-relative ``cwd``, per the Kimi plugin manifest contract).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SERVER_REL = "runtime-adapters/mcp/uacp_mcp_server.py"
# .mcp.json is the Claude project MCP config; it is gitignored operator-local
# (af93cbe) so it is ABSENT in clean checkouts / CI. Verify its wiring only when
# present — the committed server file (test_server_file_exists) and the committed
# Kimi manifest (test_kimi_*) are checked unconditionally.
_MCP_JSON = _REPO_ROOT / ".mcp.json"


def test_server_file_exists() -> None:
    assert (_REPO_ROOT / _SERVER_REL).is_file(), (
        f"MCP server file missing at {_SERVER_REL}"
    )


@pytest.mark.skipif(not _MCP_JSON.is_file(), reason=".mcp.json absent (gitignored operator-local, af93cbe)")
def test_claude_mcp_json_points_at_server() -> None:
    manifest = json.loads(_MCP_JSON.read_text())
    servers = manifest["mcpServers"]
    assert "uacp" in servers, "Claude .mcp.json missing 'uacp' server"
    entry = servers["uacp"]
    assert entry["command"] == "python3"
    args = entry["args"]
    assert len(args) == 1, f"expected a single server-path arg, got {args}"
    arg = args[0]
    assert arg.startswith("${CLAUDE_PLUGIN_ROOT}/"), (
        f"Claude server arg must use the CLAUDE_PLUGIN_ROOT token, got {arg!r}"
    )
    resolved_rel = arg.removeprefix("${CLAUDE_PLUGIN_ROOT}/")
    assert resolved_rel == _SERVER_REL, (
        f"Claude manifest points at {resolved_rel!r}, expected {_SERVER_REL!r}"
    )
    assert (_REPO_ROOT / resolved_rel).is_file()


def test_kimi_plugin_json_points_at_server() -> None:
    manifest = json.loads((_REPO_ROOT / "kimi.plugin.json").read_text())
    assert manifest["name"] == "uacp"
    servers = manifest["mcpServers"]
    assert "uacp" in servers, "kimi.plugin.json missing 'uacp' server"
    entry = servers["uacp"]
    assert entry["command"] == "python3"
    # Kimi requires cwd to be a ./-relative path within the plugin root.
    assert entry["cwd"] == "./", f"Kimi cwd must be './', got {entry['cwd']!r}"
    args = entry["args"]
    assert len(args) == 1, f"expected a single server-path arg, got {args}"
    arg = args[0]
    assert arg.startswith("./"), (
        f"Kimi server arg must be a ./-relative path, got {arg!r}"
    )
    resolved_rel = arg.removeprefix("./")
    assert resolved_rel == _SERVER_REL, (
        f"Kimi manifest points at {resolved_rel!r}, expected {_SERVER_REL!r}"
    )
    assert (_REPO_ROOT / resolved_rel).is_file()


def test_kimi_declares_skills_dir() -> None:
    manifest = json.loads((_REPO_ROOT / "kimi.plugin.json").read_text())
    assert manifest.get("skills") == "./skills/", (
        f"Kimi manifest skills path unexpected: {manifest.get('skills')!r}"
    )
    assert (_REPO_ROOT / "skills").is_dir()
