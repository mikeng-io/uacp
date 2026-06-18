"""Unit: host tool-name normalization for the PreToolUse hook (hook_kernel).

``normalize_tool_name`` rewrites a host runtime's native tool name into a KERNEL
tool name the Guardian classifier understands, so host tools resolve to a real
category instead of falling through to ``external.unknown_mutator``.

Two stages:
  1. MCP de-namespacing — Claude Code ``mcp__(plugin_<x>_)?<server>__<tool>`` and
     Hermes ``mcp_<server>_<tool>``. A recovered ``uacp_*`` tool that the kernel
     classification knows is returned bare; any other MCP tool is left namespaced
     (so it classifies as ``runtime.extension``).
  2. Host map — via ``[guardian.host_tool_classification.<profile>]``. Unmapped
     host names pass through unchanged.

The classification map here is the REAL repo config so the recovered-uacp gate
and the host map are exercised against production data.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_CORE_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "uacp-core" / "scripts"
if str(_CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_CORE_SCRIPTS))

from config import get_config  # noqa: E402
from hook_kernel import normalize_tool_name  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _classification_map() -> dict:
    return dict(get_config(_REPO_ROOT).model_dump().get("guardian", {}))


# ---------------------------------------------------------------------------
# Host-tool map (Claude Code profile)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Read", "read_file"),
        ("Grep", "read_file"),
        ("Glob", "read_file"),
        ("LS", "read_file"),
        ("NotebookRead", "read_file"),
        ("Bash", "terminal"),
        ("BashOutput", "terminal"),
        ("KillBash", "terminal"),
        ("Edit", "write_file"),
        ("Write", "write_file"),
        ("MultiEdit", "write_file"),
        ("NotebookEdit", "write_file"),
        ("WebFetch", "web_fetch"),
        ("WebSearch", "web_search"),
    ],
)
def test_host_map_claude(raw: str, expected: str) -> None:
    cmap = _classification_map()
    assert normalize_tool_name(raw, "claude_code", cmap) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Read", "read_file"),
        ("Bash", "terminal"),
        ("Edit", "write_file"),
        ("WebFetch", "web_fetch"),
    ],
)
def test_host_map_kimi(raw: str, expected: str) -> None:
    cmap = _classification_map()
    assert normalize_tool_name(raw, "kimi_code", cmap) == expected


# ---------------------------------------------------------------------------
# MCP de-namespacing
# ---------------------------------------------------------------------------


def test_mcp_cc_uacp_recovered_bare() -> None:
    cmap = _classification_map()
    assert (
        normalize_tool_name("mcp__uacp__uacp_state_write", "claude_code", cmap)
        == "uacp_state_write"
    )


def test_mcp_cc_uacp_with_plugin_prefix_recovered_bare() -> None:
    cmap = _classification_map()
    assert (
        normalize_tool_name(
            "mcp__plugin_uacp_uacp__uacp_state_write", "claude_code", cmap
        )
        == "uacp_state_write"
    )


def test_mcp_hermes_uacp_recovered_bare() -> None:
    cmap = _classification_map()
    assert (
        normalize_tool_name("mcp_uacp_uacp_state_write", "kimi_code", cmap)
        == "uacp_state_write"
    )


def test_mcp_cc_non_uacp_left_namespaced() -> None:
    cmap = _classification_map()
    raw = "mcp__uacp__other"
    # 'other' is not a known uacp_* kernel tool -> stays namespaced so it
    # classifies as runtime.extension.
    assert normalize_tool_name(raw, "claude_code", cmap) == raw


def test_mcp_cc_non_uacp_server_left_namespaced() -> None:
    cmap = _classification_map()
    raw = "mcp__github__create_issue"
    assert normalize_tool_name(raw, "claude_code", cmap) == raw


# ---------------------------------------------------------------------------
# Pass-through
# ---------------------------------------------------------------------------


def test_unknown_host_tool_passes_through() -> None:
    cmap = _classification_map()
    assert normalize_tool_name("SomeUnknownTool", "claude_code", cmap) == "SomeUnknownTool"


def test_empty_passes_through() -> None:
    cmap = _classification_map()
    assert normalize_tool_name("", "claude_code", cmap) == ""
