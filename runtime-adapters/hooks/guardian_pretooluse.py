#!/usr/bin/env python3
"""UACP Guardian PreToolUse hook — Claude Code / Kimi Code companion.

Defense-in-depth shim. Reads a host PreToolUse payload as JSON on stdin and, for
ONE narrow case, renders a host-shaped deny; otherwise it allows. It is NOT the
authoritative containment: the MCP server's governed handlers remain the
authority (they own the actual writers). This hook adds a single pre-call guard
to runtimes that drive UACP through the bare host tools.

Threat model (the ONLY thing this hook serves): *accidental corruption of
governed state* — a raw host file write that lands inside a governed ``.uacp/``
namespace. It is NOT a sandbox against hostile commands; container-grade
isolation is out of scope. The MCP governed writers stay authoritative.

The predicate (host-tool path) is TARGET-RELATIVE and worktree-robust:
  DENY iff the tool is a raw host mutating file tool (Write / Edit / MultiEdit /
  NotebookEdit) AND any ANCESTOR directory of the resolved target path is named
  ``.uacp`` (casefolded). A relative target is resolved against the payload
  ``cwd`` (the tree the agent is in — the worktree when working inside one), not
  the hook process cwd. Otherwise ALLOW (exit 0, no stdout). Specifically:
    * The membership is by ``.uacp`` ancestor dir, so it guards ``<main>/.uacp/``,
      ``<repo>/.worktrees/X/.uacp/`` (a worktree's OWN governed state), and ANY
      ``.uacp/`` uniformly — no single-project-root resolution.
    * Bash is ENTIRELY ungated. Command-string inspection is insufficient to know
      what a shell command writes (see docs/runtime/runtime-enforcement.md), so
      ANY shell-driven write bypasses this hook — a redirect (``> .uacp/x``), but
      equally ``cp``/``mv``/``tee``, ``sed -i``, an interpreter ``open()``,
      ``git checkout``, etc. This is the honest residual; it is acceptable under
      the accidental-corruption threat model — the MCP governed writers and the
      worktree are the real containment.
    * A file at the repo ROOT (e.g. ``.mcp.json``) has no ``.uacp`` ancestor -> allow.
      A file literally named ``.uacp`` (or ``*.uacp``) as the leaf is allowed too —
      only writing INTO a ``.uacp/`` directory is blocked.
    * Ordinary project edits (work-product the agent writes during EXECUTE) are
      NOT raw-blocked — they are contained by the worktree (Invariant #2) and
      captured as evidence by checkpoint/diff coverage (see ADR-0019, which
      clarifies AGENTS.md Key Invariant #3).
    * The behavior is identical whether or not a run is active.
    * The governed MCP writers (``mcp__uacp__uacp_*`` -> ``uacp_*``) are NOT host
      file tools, so they are naturally allowed (the sanctioned write path).

Design decisions:
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

# The governed namespace directory name (the namespace convention). A target is
# governed iff one of its ANCESTOR dirs is named this (casefolded).
_GOVERNED_DIR_NAME = ".uacp"


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


def _resolve_target_path(value: str, payload_cwd: str) -> Path | None:
    """Resolve a tool path arg to an absolute path.

    Absolute values are used as-is; a RELATIVE value is resolved against the
    payload ``cwd`` (the tree the agent is actually in — this is the worktree
    when working inside one), NOT the hook process cwd. ``.resolve()`` collapses
    ``..`` so a traversal is normalized before the membership test.
    """
    try:
        p = Path(value).expanduser()
        if not p.is_absolute() and payload_cwd:
            p = Path(payload_cwd).expanduser() / p
        return p.resolve()
    except Exception:
        return None


def _target_under_governed(tool_args: Mapping[str, Any], payload_cwd: str) -> str | None:
    """Return the path under the governed namespace if a path arg writes INTO a
    ``.uacp/`` directory, else None.

    Membership is TARGET-RELATIVE and worktree-robust: DENY iff any ANCESTOR
    directory of the resolved target is named ``.uacp`` (compared casefolded, so
    a case-insensitive FS — macOS/NTFS — cannot dodge via ``.UACP``). This guards
    ``<main>/.uacp/``, ``<repo>/.worktrees/X/.uacp/``, and ANY ``.uacp/`` uniformly,
    with no single-project-root resolution.

    Only ANCESTOR DIR components are checked — never the leaf name — so a file
    literally named ``.uacp`` (or ``*.uacp``) is allowed; only writing *into* a
    ``.uacp/`` directory is blocked.
    """
    for key in _PATH_ARG_KEYS:
        value = tool_args.get(key)
        if not isinstance(value, str) or not value:
            continue
        target = _resolve_target_path(value, payload_cwd)
        if target is None:
            continue
        for ancestor in target.parents:
            if ancestor.name.casefold() == _GOVERNED_DIR_NAME:
                try:
                    return str(target.relative_to(ancestor))
                except ValueError:
                    return target.name
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
        cwd = payload.get("cwd")
        payload_cwd = cwd if isinstance(cwd, str) else ""

        rel = _target_under_governed(tool_args, payload_cwd)
        if rel is None:
            # Target does not write into any .uacp/ dir (project work-product, or
            # no path) -> allow.
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
