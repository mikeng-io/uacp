"""Integration: the SessionStart cognition-injection hook.

`runtime-adapters/claude/inject_uacp_md.py` is the COGNITION-layer enforcement surface of CMS — it
emits the UACP.md preamble (minus its HTML-comment header) as SessionStart `additionalContext`, so a
host agent inherits the comprehend->measure->serialize discipline at session start. It must FAIL OPEN
(exit 0, no output) when UACP.md is absent — a cognition nudge, never a gate.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SHIM = _REPO_ROOT / "runtime-adapters" / "claude" / "inject_uacp_md.py"


def _run(plugin_root: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(plugin_root)}
    return subprocess.run(
        [sys.executable, str(_SHIM)], capture_output=True, text=True, env=env
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
