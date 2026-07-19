"""Entry-gate helper contracts (script imported directly; not part of the package surface)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import entry_gate


def test_run_missing_executable_fails_closed_with_evidence():
    """Docker absent must yield a FAILED requirement (exit 127 + stderr evidence), never a
    traceback that dies before write_record (Codex P2 on PR #158)."""
    code, out, err = entry_gate._run(["/nonexistent-docker-binary", "build"], timeout=5)
    assert code == 127
    assert "spawn failed" in err
