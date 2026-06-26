#!/usr/bin/env python3
"""UACP Guardian PreToolUse hook — Claude Code / Kimi Code companion.

Defense-in-depth shim. Reads a host PreToolUse payload as JSON on stdin and, for
ONE narrow case, renders a host-shaped deny; otherwise it allows. It is NOT the
authoritative containment: the MCP server's governed handlers remain the
authority (they own the actual writers). This hook adds a single pre-call guard
to runtimes that drive UACP through the bare host tools.

Threat model (the ONLY thing this hook serves): *accidental corruption of
governed state* — a raw host file write that lands inside the governed
``.uacp/`` namespace. It is NOT a sandbox against hostile commands; container-
grade isolation is out of scope. The MCP governed writers stay authoritative.

The narrow predicate (host-tool path):
  DENY iff the tool is a raw host mutating file tool (Write / Edit / MultiEdit /
  NotebookEdit) AND its resolved target path is inside ``<root>/.uacp/``.
  Otherwise ALLOW (exit 0, no stdout). Specifically:
    * Bash is NOT gated (command-string inspection is insufficient — see
      docs/runtime/runtime-enforcement.md; a redirect bypass is the honest
      residual, acceptable under the accidental-corruption threat model).
    * A file at the repo ROOT (e.g. ``.mcp.json``) is NOT under ``.uacp/`` -> allow.
    * Ordinary project edits (work-product the agent writes during EXECUTE) are
      NOT raw-blocked — they are contained by the worktree (Invariant #2) and
      captured as evidence by checkpoint/diff coverage (see ADR-0019, which
      clarifies AGENTS.md Key Invariant #3).
    * The behavior is identical whether or not a run is active.
    * The governed MCP writers (``mcp__uacp__uacp_*`` -> ``uacp_*``) are NOT host
      file tools, so they are naturally allowed (the sanctioned write path).

Design decisions:
  A  Root resolution: resolve the PROJECT being worked in, where ``.uacp/`` lives.
     Order: ``UACP_ROOT`` env -> ``CLAUDE_PROJECT_DIR`` env (Claude Code sets it)
     -> the payload's ``cwd`` -> this hook's own repo root (last resort). The hook
     never falls back to ``~/.hermes/uacp`` (a different install).
  D1 Fail-OPEN: malformed/unparseable stdin or an unexpected internal exception
     -> exit 0, NO stdout (allow), warn on stderr. The MCP governed handlers stay
     authoritative, so fail-open here never opens the writers.
  D5: a deny holds even under permission_mode == "bypassPermissions" (the shim
     never short-circuits to allow on permission_mode).
  D6: documented as defense-in-depth atop the authoritative MCP handlers.

Output contract:
  block  -> exit 0 + stdout PreToolUse deny JSON (+ stderr reason). If the stdout
            write fails, exit 2 + stderr.
  allow  -> exit 0, NO stdout.
  malformed/crash -> exit 0, NO stdout, stderr warning (D1).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

# --- sys.path: make the runtime-neutral kernel importable -------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
_CORE_SCRIPTS = _REPO_ROOT / "skills" / "uacp-core" / "scripts"
if str(_CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_CORE_SCRIPTS))

# Host tools that perform a raw file mutation (Claude Code / Kimi Code names).
_RAW_WRITE_TOOLS = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit"})

# Tool-arg keys that may carry the target path of a file mutation.
_PATH_ARG_KEYS = ("file_path", "path", "target_path", "notebook_path")


def _warn(msg: str) -> None:
    sys.stderr.write(f"[uacp-guardian-hook] {msg}\n")


def _read_stdin_json() -> Mapping[str, Any] | None:
    try:
        raw = sys.stdin.read()
    except Exception:
        return None
    if not raw or not raw.strip():
        return None
    try:
        payload = json.loads(raw)
    except Exception:
        return None
    return payload if isinstance(payload, Mapping) else None


def _extract_tool_name(payload: Mapping[str, Any]) -> str:
    return str(payload.get("tool_name") or payload.get("toolName") or "")


def _extract_tool_args(payload: Mapping[str, Any]) -> dict[str, Any]:
    args = payload.get("tool_input")
    if not isinstance(args, Mapping):
        args = payload.get("toolInput")
    if not isinstance(args, Mapping):
        args = payload.get("input")
    return dict(args) if isinstance(args, Mapping) else {}


def _resolve_project_root(payload: Mapping[str, Any]) -> Path:
    """DEFECT A: resolve the project being worked in, where ``.uacp/`` lives.

    Order: ``UACP_ROOT`` env -> ``CLAUDE_PROJECT_DIR`` env -> payload ``cwd`` ->
    this hook's own repo root. Never ``~/.hermes/uacp`` (do NOT call the kernel's
    ``resolve_uacp_root``, which would fall back to a different install when
    ``UACP_ROOT``/``HERMES_HOME`` are unset — the normal Claude Code case).
    """
    for env_key in ("UACP_ROOT", "CLAUDE_PROJECT_DIR"):
        value = os.getenv(env_key, "").strip()
        if value:
            try:
                return Path(value).expanduser().resolve()
            except Exception:
                pass
    cwd = payload.get("cwd")
    if isinstance(cwd, str) and cwd.strip():
        try:
            return Path(cwd).expanduser().resolve()
        except Exception:
            pass
    return _REPO_ROOT


def _governed_base(root: Path) -> Path | None:
    """The governed namespace root ``<root>/.uacp`` (config-controlled).

    Prefers ``config.base_dir`` (honors a ``[paths] base`` override). Falls back
    to ``<root>/.uacp`` if the config cannot be read, so a config blip never
    silently disables the guard. Returns None only if even the fallback fails.
    """
    try:
        from config import base_dir

        return base_dir(root).resolve()
    except Exception:
        try:
            return (root / ".uacp").resolve()
        except Exception:
            return None


def _target_under_governed(tool_args: Mapping[str, Any], base: Path) -> str | None:
    """If any path arg resolves inside ``base``, return its path relative to
    ``base`` (traversal-safe). Else None.

    Resolution collapses ``..`` before the containment test, so a traversal that
    climbs out is correctly seen as outside; a path that lands on/under ``base``
    is inside.
    """
    for key in _PATH_ARG_KEYS:
        value = tool_args.get(key)
        if not isinstance(value, str) or not value:
            continue
        try:
            target = Path(value).expanduser().resolve()
        except Exception:
            continue
        try:
            rel = target.relative_to(base)
        except ValueError:
            continue
        return str(rel)
    return None


def _emit_deny(reason: str) -> int:
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    _warn(f"deny: {reason}")
    try:
        sys.stdout.write(json.dumps(payload))
        sys.stdout.flush()
    except Exception as exc:  # stdout write failed -> exit 2 + stderr (per spec).
        _warn(f"failed to write deny decision to stdout: {exc}")
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    # --profile is accepted for invocation compatibility (hooks.json passes it)
    # but no longer changes the narrow predicate — host names are identical
    # across Claude Code and Kimi Code for the tools this hook guards.
    parser.add_argument("--profile", choices=["claude", "kimi"], default=None)
    parser.parse_args(argv if argv is not None else sys.argv[1:])

    payload = _read_stdin_json()
    if payload is None:
        # D1: malformed/unparseable stdin -> fail open (allow, no stdout).
        _warn("unparseable or empty stdin payload — failing open (allow)")
        return 0

    try:
        tool_name = _extract_tool_name(payload)
        # Only raw host file mutators can accidentally corrupt governed state.
        if tool_name not in _RAW_WRITE_TOOLS:
            return 0

        tool_args = _extract_tool_args(payload)
        root = _resolve_project_root(payload)
        base = _governed_base(root)
        if base is None:
            # Could not determine the governed namespace -> fail open (D1).
            _warn("could not resolve the governed base — failing open (allow)")
            return 0

        rel = _target_under_governed(tool_args, base)
        if rel is None:
            # Target is outside .uacp/ (project work-product, or no path) -> allow.
            return 0

        reason = (
            f"Blocked raw {tool_name} into the governed namespace (.uacp/{rel}). "
            "Use the uacp_* governed writer (e.g. uacp_state_write / "
            "uacp_entity_write) instead, or open a run via TRIAGE. "
            "(Defense-in-depth; the MCP governed writers are authoritative.)"
        )
        return _emit_deny(reason)
    except Exception as exc:  # D1: any unexpected internal error -> fail open.
        _warn(f"internal error — failing open (allow): {type(exc).__name__}: {exc}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
