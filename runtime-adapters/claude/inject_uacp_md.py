#!/usr/bin/env python3
"""SessionStart hook — inject the UACP coherence-invariant preamble (UACP.md) at the top of the
agent's context for every session, plus a compact summary of any `active` uacp-handoff capsules and
the project's PRINCIPLE.md.

This is the COGNITION-layer enforcement surface of CMS (comprehend -> measure -> serialize). The
only lever on an LLM's own reasoning is the instruction it reads, so injecting the preamble *is* the
enforcement mechanism there -- not decoration. See
design/comprehend-measure-serialize/25-enforcement-surfaces.md.

WHAT LIVES HERE vs IN SHARED: the context TEXT is built by the runtime-neutral
``runtime-adapters/shared/session_context.py`` (same preamble + handoffs + principle for every
runtime). This file keeps only Claude Code's edges: read the SessionStart payload from stdin, locate
UACP.md under the plugin root, and emit the ``hookSpecificOutput`` envelope on stdout. Hermes calls
the same neutral builder from its own hook -- see runtime-adapters/hermes/plugins/uacp_guardian/.

Contract: emit {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": <text>}}.
Fail OPEN -- this is a cognition nudge, not a gate; a missing/unreadable UACP.md, or a missing/
malformed handoffs index, must never block a session (the architecture surface, not this hook, is
the fail-closed one). Kernel-free (imports nothing from the UACP kernel).
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "shared"))

from session_context import (  # noqa: E402  (sys.path set above)
    build_session_context,
    principle_path,
    workspace_root,
)


def _plugin_root() -> str:
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        return env
    # fallback: <root>/runtime-adapters/claude/inject_uacp_md.py -> <root>
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _read_stdin_json() -> dict[str, Any] | None:
    """Best-effort read of the SessionStart hook payload from stdin. None on any failure
    (empty stdin, unparseable JSON, non-object payload) -- never raises. A TTY stdin (the
    hook run interactively, not by Claude Code's piped SessionStart) would make ``.read()``
    BLOCK until EOF and hang session startup, so it is treated as no-payload first."""
    try:
        if sys.stdin is None or sys.stdin.isatty():
            return None
        raw = sys.stdin.read()
    except Exception:
        return None
    if not raw or not raw.strip():
        return None
    try:
        payload = json.loads(raw)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _cwd_from(payload: dict[str, Any] | None) -> str | None:
    """The session's working directory as Claude Code reports it, or None."""
    if payload is None:
        return None
    c = payload.get("cwd")
    return c if isinstance(c, str) and c else None


def main() -> int:
    payload = _read_stdin_json()
    cwd = _cwd_from(payload)
    plugin_root = _plugin_root()
    ws_root = workspace_root(cwd, plugin_root)
    text = build_session_context(plugin_root, ws_root, principle_path(cwd, ws_root))
    if not text:
        return 0  # nothing to inject
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": text,
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
