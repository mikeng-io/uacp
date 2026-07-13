#!/usr/bin/env python3
"""SessionStart hook — inject the UACP coherence-invariant preamble (UACP.md) at the top of the
agent's context for every session, plus a compact summary of any `active` uacp-handoff capsules.

This is the COGNITION-layer enforcement surface of CMS (comprehend -> measure -> serialize). The
only lever on an LLM's own reasoning is the instruction it reads, so injecting the preamble *is* the
enforcement mechanism there -- not decoration. See
design/comprehend-measure-serialize/25-enforcement-surfaces.md.

It also surfaces `.uacp/handoffs/_index.yaml` (the uacp-handoff skill's session-boundary capsules,
design/handoff/): entries with `status: active` get a one-line "workstream — hook" summary appended
after the UACP.md preamble, so RESUME is no longer purely a manual skill verb. `.uacp/` lives in the
WORKSPACE, which may differ from the plugin root (e.g. inside a worktree) -- the workspace root is
read from the SessionStart payload's `cwd` (stdin JSON), mirroring
runtime-adapters/shared/guardian_pretooluse.py; it falls back to the plugin root when no payload /
no `cwd` is available.

Contract: emit {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": <text>}}.
Fail OPEN -- this is a cognition nudge, not a gate; a missing/unreadable UACP.md, or a missing/
malformed handoffs index, must never block a session (the architecture surface, not this hook, is
the fail-closed one). Kernel-free (imports nothing from the UACP kernel). The handoffs index is
read with real YAML when the hook's python has PyYAML (robust for any shape a writer produces,
including the default ``yaml.safe_dump`` column-0 list and a workstream-keyed mapping); when
PyYAML is absent it falls back to a tolerant stdlib line parser, so the hook never HARD-depends
on yaml. Untrusted field values (committed capsules) are length-clamped before injection.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

# Cap on how many active handoffs get surfaced (keep the injected context compact).
_MAX_ACTIVE_HANDOFFS = 10
# Per-field length clamp: a committed capsule's `hook`/`workstream` is untrusted text injected
# verbatim into session context, so bound each to keep a hostile/oversized value from flooding
# the preamble (council #100 P3).
_MAX_FIELD_LEN = 200

_HANDOFF_KEYS = ("workstream", "status", "updated_at", "hook")

# stdlib-fallback line matchers: a list item opens on `- key:` at ANY indent (incl. column 0,
# which is what yaml.safe_dump emits); a continuation key is any indented `key:`.
_HANDOFF_ITEM_RE = re.compile(r"^\s*-\s+([A-Za-z_]\w*):\s*(.*)$")
_HANDOFF_KEY_RE = re.compile(r"^\s+([A-Za-z_]\w*):\s*(.*)$")


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


def _workspace_root(payload: dict[str, Any] | None) -> str:
    """Where `.uacp/` lives for THIS session -- the payload `cwd` (the tree the agent is
    actually in; the worktree, when working inside one), mirroring
    runtime-adapters/shared/guardian_pretooluse.py's `_target_under_governed`. Falls back
    to the plugin root when the payload/cwd is absent (no-stdin invocation, or a workspace
    that IS the plugin root)."""
    if payload is not None:
        cwd = payload.get("cwd")
        if isinstance(cwd, str) and cwd:
            return cwd
    return _plugin_root()


def _unquote(value: str) -> str:
    """Strip surrounding quotes; for an UNquoted scalar, also drop a trailing YAML comment
    (`... # note`). A bare `#` without a leading space is a literal (e.g. `bug#12`), and a `#`
    inside a quoted value is preserved (gemini #100). Only used by the stdlib fallback — the
    real YAML parser handles all of this natively."""
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if " #" in v:
        v = v.split(" #", 1)[0].rstrip()
    return v


def _coerce_entry(raw: dict[str, Any]) -> dict[str, str]:
    """Keep only the recognized keys, as trimmed strings."""
    out: dict[str, str] = {}
    for k in _HANDOFF_KEYS:
        v = raw.get(k)
        if v is not None:
            out[k] = str(v).strip()
    return out


def _entries_from_obj(data: Any) -> list[dict[str, str]]:
    """Normalize a parsed index object to a list of entry dicts. ``entries`` is a LIST of
    mappings — the shape the uacp-handoff skill writes (see its SKILL.md template). Only the
    list form is supported, and BOTH the yaml and stdlib-fallback paths handle it identically,
    so behavior does not silently change with PyYAML's presence (Codex #100). A non-list
    ``entries`` (e.g. a workstream-keyed mapping) is not a shape the skill produces -> []."""
    if not isinstance(data, dict):
        return []
    entries = data.get("entries")
    if isinstance(entries, list):
        return [_coerce_entry(e) for e in entries if isinstance(e, dict)]
    return []


def _parse_handoff_entries(text: str) -> list[dict[str, str]]:
    """Parse the `entries` from a handoff `_index.yaml`. Uses real YAML when PyYAML is present
    (robust for ANY writer's shape); falls back to a tolerant stdlib line parser when it is not
    (the hook must not hard-depend on yaml -- it may run under a bare ``python3``). Returns a
    list of ``{recognized_key: str}`` entry dicts; anything unparseable -> ``[]``. Never raises."""
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        return _parse_handoff_entries_stdlib(text)
    try:
        return _entries_from_obj(yaml.safe_load(text))
    except Exception:
        return []  # yaml present but the content is malformed -> fail open


def _parse_handoff_entries_stdlib(text: str) -> list[dict[str, str]]:
    """PyYAML-free fallback: read the `entries` block line by line. A list item opens on a
    `- key:` marker at ANY indent (column-0 items, as ``yaml.safe_dump`` emits, included) and
    is order-independent; a top-level non-list line ends the block. Recognized keys only."""
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_entries = False
    for line in text.splitlines():
        if not in_entries:
            if re.match(r"^entries:\s*$", line):
                in_entries = True
            continue
        stripped = line.strip()
        if not stripped:
            continue
        # a non-indented line that is NOT a list item = the next top-level key -> block over
        # (a column-0 `- ...` list item, which safe_dump emits, stays inside the block).
        if not line[0].isspace() and not stripped.startswith("-"):
            break
        item = _HANDOFF_ITEM_RE.match(line)
        if stripped == "-" or item:
            # a `- key: value` OR a bare `-` (keys on the following indented lines) opens a
            # fresh entry — both are valid YAML block-sequence items (gemini #100).
            if current is not None:
                entries.append(current)
            current = {}
            if item:
                key, val = item.group(1), item.group(2)
                if key in _HANDOFF_KEYS:
                    current[key] = _unquote(val)
            continue
        m = _HANDOFF_KEY_RE.match(line)
        if m and current is not None:
            key, val = m.group(1), m.group(2)
            if key in _HANDOFF_KEYS:
                current[key] = _unquote(val)
    if current is not None:
        entries.append(current)
    return entries


def _active_handoffs_section(ws_root: str) -> str:
    """A compact 'active workstreams' summary from `.uacp/handoffs/_index.yaml` under
    `ws_root`, or '' if the file/dir is absent, unreadable, or carries no active entries
    (fail open -- this is a cognition nudge, never a gate)."""
    path = os.path.join(ws_root, ".uacp", "handoffs", "_index.yaml")
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError):
        return ""
    try:
        entries = _parse_handoff_entries(text)
    except Exception:
        return ""
    active = [e for e in entries if e.get("status") == "active" and e.get("workstream")]
    if not active:
        return ""
    lines = ["## Active Handoffs (uacp-handoff)", ""]
    for e in active[:_MAX_ACTIVE_HANDOFFS]:
        ws = _clamp(e["workstream"])
        hook = _clamp(e.get("hook", "").strip())
        lines.append(f"- **{ws}** — {hook}" if hook else f"- **{ws}**")
    return "\n".join(lines)


def _clamp(value: str) -> str:
    """Bound an untrusted committed-capsule field before it is injected into session context
    (council #100 P3). Also collapse newlines so a multi-line value can't break the markdown."""
    v = " ".join(value.split())
    return v if len(v) <= _MAX_FIELD_LEN else v[: _MAX_FIELD_LEN - 1] + "…"


def main() -> int:
    ws_root = _workspace_root(_read_stdin_json())

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

    handoffs = _active_handoffs_section(ws_root)
    if handoffs:
        text = f"{text}\n\n{handoffs}"

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
