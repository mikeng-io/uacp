#!/usr/bin/env python3
"""SessionStart hook — inject the UACP coherence-invariant preamble (UACP.md) at the top of the
agent's context for every session.

This is the COGNITION-layer enforcement surface of CMS (comprehend -> measure -> serialize). The
only lever on an LLM's own reasoning is the instruction it reads, so injecting the preamble *is* the
enforcement mechanism there -- not decoration. See
design/comprehend-measure-serialize/25-enforcement-surfaces.md.

Contract: emit {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": <text>}}.
Fail OPEN -- this is a cognition nudge, not a gate; a missing/unreadable UACP.md must never block a
session (the architecture surface, not this hook, is the fail-closed one).
"""
from __future__ import annotations

import json
import os
import re
import sys


def _plugin_root() -> str:
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        return env
    # fallback: <root>/runtime-adapters/hooks/inject_uacp_md.py -> <root>
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    path = os.path.join(_plugin_root(), "UACP.md")
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError):
        # Fail open on BOTH a missing/unreadable file (OSError) AND a present-but-undecodable
        # one (UnicodeDecodeError subclasses ValueError, not OSError) — a corrupt-encoding
        # UACP.md is "unreadable" too and must never crash/block a session.
        return 0  # nothing to inject

    # Drop the leading HTML comment (file-role metadata; not meant for the agent).
    text = re.sub(r"^\s*<!--.*?-->\s*", "", text, count=1, flags=re.DOTALL).strip()
    if not text:
        return 0

    payload = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": text,
        }
    }
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
