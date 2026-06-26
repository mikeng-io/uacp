"""Manifest-integrity: the Claude Code PreToolUse hook manifest is well-formed
and points at the real Guardian shim.

Pure JSON + path checks (no Claude Code runtime needed). Parses
``hooks/hooks.json`` and ``.claude-plugin/plugin.json`` at the repo root and
asserts:
  * hooks.json declares a PreToolUse hook with a ``*`` matcher and a command
    entry that invokes the shim via the ``${CLAUDE_PLUGIN_ROOT}`` token with a
    sane timeout;
  * the referenced shim path resolves to
    ``runtime-adapters/shared/guardian_pretooluse.py`` and exists;
  * plugin.json references ``./hooks/hooks.json`` so Claude Code discovers it.
"""

from __future__ import annotations

import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SHIM_REL = "runtime-adapters/shared/guardian_pretooluse.py"


def test_shim_file_exists() -> None:
    assert (_REPO_ROOT / _SHIM_REL).is_file(), f"hook shim missing at {_SHIM_REL}"


def test_hooks_json_well_formed_and_points_at_shim() -> None:
    manifest = json.loads((_REPO_ROOT / "hooks" / "hooks.json").read_text())
    pre = manifest["hooks"]["PreToolUse"]
    assert isinstance(pre, list) and pre, "PreToolUse must be a non-empty list"
    entry = pre[0]
    assert entry["matcher"] == "*", f"expected '*' matcher, got {entry.get('matcher')!r}"
    hooks = entry["hooks"]
    assert isinstance(hooks, list) and hooks
    hook = hooks[0]
    assert hook["type"] == "command"
    assert isinstance(hook.get("timeout"), int) and hook["timeout"] > 0

    command = hook["command"]
    assert "${CLAUDE_PLUGIN_ROOT}/" in command, (
        f"hook command must use the CLAUDE_PLUGIN_ROOT token, got {command!r}"
    )
    assert _SHIM_REL in command, f"hook command must invoke {_SHIM_REL}, got {command!r}"
    assert "--profile claude" in command, "CC hook must pass --profile claude"

    # Resolve the path embedded in the command and assert it exists.
    token = "${CLAUDE_PLUGIN_ROOT}/"
    start = command.index(token) + len(token)
    rest = command[start:]
    # The path ends at the next quote (the command quotes the path).
    rel = rest.split('"', 1)[0].split(" ", 1)[0]
    assert (_REPO_ROOT / rel).is_file(), f"hook command path does not resolve: {rel}"


def test_plugin_json_references_hooks() -> None:
    plugin = json.loads((_REPO_ROOT / ".claude-plugin" / "plugin.json").read_text())
    assert plugin.get("hooks") == "./hooks/hooks.json", (
        f"plugin.json must reference ./hooks/hooks.json, got {plugin.get('hooks')!r}"
    )
