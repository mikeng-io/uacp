"""Integration: the SessionStart cognition-injection hook.

`runtime-adapters/claude/inject_uacp_md.py` is the COGNITION-layer enforcement surface of CMS — it
emits the UACP.md preamble (minus its HTML-comment header) as SessionStart `additionalContext`, so a
host agent inherits the comprehend->measure->serialize discipline at session start. It must FAIL OPEN
(exit 0, no output) when UACP.md is absent — a cognition nudge, never a gate.

It also surfaces `active` uacp-handoff capsules (`.uacp/handoffs/_index.yaml`) from the WORKSPACE
root (the SessionStart payload's `cwd`, which may differ from the plugin root inside a worktree) —
also fail-open: an absent/malformed index must never crash or drop the UACP.md preamble.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SHIM = _REPO_ROOT / "runtime-adapters" / "claude" / "inject_uacp_md.py"


def _load_shim_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("_inject_uacp_md_under_test", _SHIM)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_stdlib_fallback_parses_column_zero_and_indented() -> None:
    """The PyYAML-free fallback (used when the hook's python lacks yaml) must ALSO handle the
    column-0 list items yaml.safe_dump emits and be key-order independent (council #100 P1) —
    it is the last line of defense when yaml is unavailable."""
    mod = _load_shim_module()
    # column-0 list, keys NOT workstream-first (the shape that broke the original)
    text = (
        "kind: handoff_index\nentries:\n"
        "- hook: c0 hook\n  status: active\n  workstream: c0-ws\n"
        "- status: resolved\n  workstream: gone\n"
    )
    entries = mod._parse_handoff_entries_stdlib(text)
    by_ws = {e.get("workstream"): e for e in entries}
    assert by_ws["c0-ws"]["status"] == "active" and by_ws["c0-ws"]["hook"] == "c0 hook"
    assert by_ws["gone"]["status"] == "resolved"  # not bled into the previous entry


def test_stdlib_fallback_bare_dash_and_inline_comment() -> None:
    """Fallback edge cases (gemini #100): a bare `-` opens an entry (keys on following lines),
    and an inline `# comment` after an unquoted value is stripped (so `status: active # note`
    still equals 'active'), while a `#` inside a quoted value survives."""
    mod = _load_shim_module()
    text = (
        "entries:\n"
        "  -\n"  # bare dash
        "    workstream: bare-ws\n"
        "    status: active   # still active\n"  # inline comment
        '    hook: "fix bug #1234"\n'  # '#' inside quotes must survive
    )
    entries = mod._parse_handoff_entries_stdlib(text)
    assert len(entries) == 1
    e = entries[0]
    assert e["workstream"] == "bare-ws"
    assert e["status"] == "active"  # comment stripped, not "active   # still active"
    assert e["hook"] == "fix bug #1234"  # quoted '#' preserved


def _run(plugin_root: Path, payload: dict | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(plugin_root)}
    # Always pass stdin explicitly (even "") so the hook's stdin read can never block on
    # an inherited terminal/pipe — the payload carries the SessionStart `cwd` when given.
    stdin_input = json.dumps(payload) if payload is not None else ""
    return subprocess.run(
        [sys.executable, str(_SHIM)],
        input=stdin_input,
        capture_output=True,
        text=True,
        env=env,
    )


def test_injects_uacp_md_as_sessionstart_context(tmp_path: Path) -> None:
    (tmp_path / "UACP.md").write_text(
        "<!--\n  meta comment, must be stripped\n-->\n\n# UACP\n\nSENTINEL_CMS_PREAMBLE\n",
        encoding="utf-8",
    )
    proc = _run(tmp_path)
    assert proc.returncode == 0
    hs = json.loads(proc.stdout)["hookSpecificOutput"]
    assert hs["hookEventName"] == "SessionStart"
    ctx = hs["additionalContext"]
    assert "SENTINEL_CMS_PREAMBLE" in ctx  # the file content IS injected
    assert "meta comment" not in ctx  # the HTML-comment header IS stripped
    assert not ctx.lstrip().startswith("<!--")


def test_fail_open_when_uacp_md_absent(tmp_path: Path) -> None:
    proc = _run(tmp_path)  # tmp_path has no UACP.md
    assert proc.returncode == 0  # never blocks a session
    assert proc.stdout.strip() == ""  # nothing injected, no malformed JSON


def test_fail_open_when_uacp_md_is_undecodable(tmp_path: Path) -> None:
    # Present but not valid UTF-8: must STILL fail open (UnicodeDecodeError is not an OSError).
    (tmp_path / "UACP.md").write_bytes(b"\xff\xfe not valid utf-8 \x80\x81")
    proc = _run(tmp_path)
    assert proc.returncode == 0  # corrupt encoding must not crash/block the session
    assert proc.stdout.strip() == ""  # nothing injected


def test_real_shipped_uacp_md_carries_the_principle() -> None:
    """Non-vacuity against the REAL UACP.md: the shipped preamble must carry the semantic principle."""
    proc = _run(_REPO_ROOT)
    assert proc.returncode == 0
    ctx = json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "comprehend" in ctx and "measure" in ctx and "serialize" in ctx
    assert "semantic" in ctx  # the determinism:machines :: CMS:agents bedrock is present


# --- active handoffs surfacing (#100 slice 2) ---------------------------------------
_UACP_MD = "<!--\n  meta\n-->\n\n# UACP\n\nSENTINEL_CMS_PREAMBLE\n"


def _write_index(handoffs_dir: Path, entries_yaml: str) -> None:
    handoffs_dir.mkdir(parents=True, exist_ok=True)
    (handoffs_dir / "_index.yaml").write_text(
        "kind: handoff_index\ntitle: index\nentries:\n" + entries_yaml, encoding="utf-8"
    )


def test_active_handoff_surfaced_from_workspace_root_distinct_from_plugin_root(
    tmp_path: Path,
) -> None:
    # The plugin root (UACP.md's home) and the workspace root (.uacp/'s home) are
    # DIFFERENT directories here — the realistic worktree shape: the plugin ships once,
    # the workspace is wherever the agent's cwd is.
    plugin_dir = tmp_path / "plugin"
    workspace_dir = tmp_path / "workspace"
    plugin_dir.mkdir()
    workspace_dir.mkdir()
    (plugin_dir / "UACP.md").write_text(_UACP_MD, encoding="utf-8")
    _write_index(
        workspace_dir / ".uacp" / "handoffs",
        "  - workstream: my-workstream\n"
        "    status: active\n"
        "    updated_at: '2026-07-14'\n"
        '    hook: "do the next thing"\n'
        "  - workstream: old-one\n"
        "    status: resolved\n"
        "    updated_at: '2026-07-01'\n"
        '    hook: "done, ignore"\n'
        "  - workstream: replaced-one\n"
        "    status: superseded\n"
        "    updated_at: '2026-06-01'\n"
        '    hook: "superseded, ignore"\n',
    )

    proc = _run(plugin_dir, payload={"cwd": str(workspace_dir)})

    assert proc.returncode == 0
    ctx = json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "SENTINEL_CMS_PREAMBLE" in ctx  # base preamble still present
    assert "my-workstream" in ctx and "do the next thing" in ctx  # active surfaced
    assert "old-one" not in ctx  # resolved excluded
    assert "replaced-one" not in ctx  # superseded excluded


def test_entries_with_status_first_key_do_not_bleed(tmp_path: Path) -> None:
    """Parser robustness (gemini/council #100 P1): a `- ` item that does NOT start with
    `workstream:` must still open a fresh entry — no key must bleed onto the previous one, and
    no active entry may be dropped or mis-statused."""
    plugin_dir = tmp_path / "plugin"
    workspace_dir = tmp_path / "workspace"
    plugin_dir.mkdir()
    workspace_dir.mkdir()
    (plugin_dir / "UACP.md").write_text(_UACP_MD, encoding="utf-8")
    _write_index(
        workspace_dir / ".uacp" / "handoffs",
        # entry 1: status-first (would be DROPPED by a workstream-anchored parser)
        "  - status: active\n"
        "    workstream: apollo-checklist\n"
        '    hook: "finalize pre-flight"\n'
        # entry 2: workstream-first, active
        "  - workstream: gemini-e2e\n"
        "    status: active\n"
        '    hook: "run the suite"\n'
        # entry 3: status-first, superseded (must NOT bleed 'active' from entry 2)
        "  - status: superseded\n"
        "    workstream: old-hermes\n",
    )
    proc = _run(plugin_dir, payload={"cwd": str(workspace_dir)})
    assert proc.returncode == 0
    ctx = json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "apollo-checklist" in ctx and "finalize pre-flight" in ctx  # status-first NOT dropped
    assert "gemini-e2e" in ctx and "run the suite" in ctx
    assert "old-hermes" not in ctx  # superseded excluded — no 'active' bleed from entry 2


def _write_raw_index(handoffs_dir: Path, content: str) -> None:
    handoffs_dir.mkdir(parents=True, exist_ok=True)
    (handoffs_dir / "_index.yaml").write_text(content, encoding="utf-8")


def test_safe_dump_shape_surfaces_active(tmp_path: Path) -> None:
    """The DEFAULT yaml emitter (yaml.safe_dump) writes list items at COLUMN 0 and sorts keys
    alphabetically — the shape that killed the original hand-rolled parser (council #100 P1).
    Real YAML parsing (or the hardened fallback) must surface the active entry."""
    import yaml

    plugin_dir, workspace_dir = tmp_path / "plugin", tmp_path / "workspace"
    plugin_dir.mkdir()
    workspace_dir.mkdir()
    (plugin_dir / "UACP.md").write_text(_UACP_MD, encoding="utf-8")
    index = {
        "kind": "handoff_index",
        "entries": [
            {"hook": "resume the migration", "status": "active", "workstream": "db-migration"},
            {"hook": "done", "status": "resolved", "workstream": "old-thing"},
        ],
    }
    _write_raw_index(workspace_dir / ".uacp" / "handoffs", yaml.safe_dump(index, sort_keys=True))
    proc = _run(plugin_dir, payload={"cwd": str(workspace_dir)})
    assert proc.returncode == 0
    ctx = json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "db-migration" in ctx and "resume the migration" in ctx  # NOT dead on safe_dump output
    assert "old-thing" not in ctx


def test_mapping_keyed_entries_surface(tmp_path: Path) -> None:
    """An `entries:` MAPPING keyed by workstream (a plausible alternate shape) is handled."""
    plugin_dir, workspace_dir = tmp_path / "plugin", tmp_path / "workspace"
    plugin_dir.mkdir()
    workspace_dir.mkdir()
    (plugin_dir / "UACP.md").write_text(_UACP_MD, encoding="utf-8")
    _write_raw_index(
        workspace_dir / ".uacp" / "handoffs",
        'kind: handoff_index\nentries:\n  alpha:\n    status: active\n    hook: "alpha next"\n'
        "  beta:\n    status: resolved\n",
    )
    proc = _run(plugin_dir, payload={"cwd": str(workspace_dir)})
    ctx = json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "alpha" in ctx and "alpha next" in ctx
    assert "beta" not in ctx


def test_oversized_hook_is_clamped(tmp_path: Path) -> None:
    """A committed capsule's untrusted `hook` is length-clamped before injection (council P3)."""
    plugin_dir, workspace_dir = tmp_path / "plugin", tmp_path / "workspace"
    plugin_dir.mkdir()
    workspace_dir.mkdir()
    (plugin_dir / "UACP.md").write_text(_UACP_MD, encoding="utf-8")
    huge = "X" * 5000
    _write_index(
        workspace_dir / ".uacp" / "handoffs",
        f"  - workstream: big\n    status: active\n    hook: {huge}\n",
    )
    proc = _run(plugin_dir, payload={"cwd": str(workspace_dir)})
    ctx = json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "big" in ctx
    assert "X" * 5000 not in ctx  # not injected verbatim
    assert "…" in ctx  # clamped with an ellipsis


def test_fail_open_when_handoffs_index_absent(tmp_path: Path) -> None:
    (tmp_path / "UACP.md").write_text(_UACP_MD, encoding="utf-8")
    proc = _run(tmp_path, payload={"cwd": str(tmp_path)})  # no .uacp/handoffs/ at all
    assert proc.returncode == 0
    ctx = json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "SENTINEL_CMS_PREAMBLE" in ctx  # UACP.md content still present
    assert "Active Handoffs" not in ctx


def test_fail_open_when_handoffs_index_malformed(tmp_path: Path) -> None:
    (tmp_path / "UACP.md").write_text(_UACP_MD, encoding="utf-8")
    handoffs_dir = tmp_path / ".uacp" / "handoffs"
    handoffs_dir.mkdir(parents=True)
    (handoffs_dir / "_index.yaml").write_bytes(b"\xff\xfe not valid utf-8 \x80\x81")

    proc = _run(tmp_path, payload={"cwd": str(tmp_path)})

    assert proc.returncode == 0  # never crashes
    ctx = json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "SENTINEL_CMS_PREAMBLE" in ctx  # UACP.md content still present
    assert "Active Handoffs" not in ctx


def test_no_active_entries_omits_the_section(tmp_path: Path) -> None:
    (tmp_path / "UACP.md").write_text(_UACP_MD, encoding="utf-8")
    _write_index(
        tmp_path / ".uacp" / "handoffs",
        "  - workstream: old-one\n    status: resolved\n    updated_at: '2026-07-01'\n"
        '    hook: "done"\n',
    )

    proc = _run(tmp_path, payload={"cwd": str(tmp_path)})

    assert proc.returncode == 0
    ctx = json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "Active Handoffs" not in ctx
    assert "old-one" not in ctx
