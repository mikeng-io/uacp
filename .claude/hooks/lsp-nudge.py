#!/usr/bin/env python3
"""PreToolUse nudge (DEV-ONLY, repo-local) — LSP-first for symbols.

When a `Grep` tool call (or a Bash `grep`/`rg`) searches for a bare IDENTIFIER (a
symbol-shaped pattern), inject a soft reminder to use the `LSP` tool instead. It is
SOFT: it never blocks a tool call — it only adds context. See CLAUDE.md "Code
intelligence — unified lookup/edit flow".

Scope: this is Claude Code project config for working IN the uacp repo (wired in
`.claude/settings.json`). It is NOT part of UACP-the-framework — it ships nothing,
appears in no skill, and enforces nothing at UACP runtime. Other runtimes ignore it.
"""

from __future__ import annotations

import json
import re
import sys

# A bare symbol name: alpha/underscore start, word chars only, len >= 3, no regex
# metacharacters and no whitespace (so "validate", "graph_projection", "_extract_paths",
# "GraphProjection" match; "def validate", "import os", "a.b", ".*foo" do not).
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{2,}$")

# In a Bash command: the search term right after grep/rg/egrep (skipping simple flags).
_BASH_GREP = re.compile(
    r"\b(?:grep|egrep|rg)\b(?:\s+-{1,2}[A-Za-z-]+)*\s+['\"]?([A-Za-z_][A-Za-z0-9_]{2,})['\"]?"
)


def _pattern(data: dict) -> str | None:
    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}
    if tool == "Grep":
        p = ti.get("pattern")
        return p if isinstance(p, str) else None
    if tool == "Bash":
        m = _BASH_GREP.search(ti.get("command", "") or "")
        return m.group(1) if m else None
    return None


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return  # malformed input -> allow silently
    pat = _pattern(data)
    if not pat:
        return
    pat = pat.strip().strip("'\"")
    if not _IDENT.match(pat):
        return
    msg = (
        f"LSP+grep hybrid reminder: '{pat}' is symbol-shaped. LEAD WITH the LSP tool "
        f"(findReferences / documentSymbol / workspaceSymbol) — precise, import-resolved — "
        f"then combine with grep, which catches what LSP misses (strings, comments, dynamic "
        f"/ cross-language refs, stale-index gaps). Don't rely on grep ALONE for a symbol; "
        f"reconcile both, the suite decides. (Genuinely literal text / config? grep alone is fine.)"
    )
    print(
        json.dumps(
            {"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": msg}}
        )
    )


if __name__ == "__main__":
    main()
