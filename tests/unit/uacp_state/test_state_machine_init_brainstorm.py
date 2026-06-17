"""Test that handle_init accepts initial_phase='brainstorm' (T4)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import yaml


def _make_workspace(tmp: Path) -> Path:
    uacp_dir = tmp / ".uacp"
    uacp_dir.mkdir()
    return tmp


def test_handle_init_accepts_brainstorm_phase(tmp_path: Path) -> None:
    """handle_init with initial_phase='brainstorm' must create manifest at brainstorm."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]
                          / "skills" / "uacp-state" / "scripts"))
    from state_machine import handle_init

    ws = _make_workspace(tmp_path)
    result = json.loads(handle_init({
        "workspace": str(ws),
        "run_id": "bs-test-001",
        "source": "operator-request",
        "initial_phase": "brainstorm",
    }))
    assert result.get("ok"), f"unexpected error: {result}"

    manifest_path = ws / ".uacp" / "state" / "runs" / "bs-test-001.yaml"
    assert manifest_path.exists()
    manifest = yaml.safe_load(manifest_path.read_text())
    assert manifest["current_phase"] == "brainstorm"


def test_handle_init_default_phase_still_triage(tmp_path: Path) -> None:
    """When initial_phase is omitted, current_phase must still default to triage."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]
                          / "skills" / "uacp-state" / "scripts"))
    from state_machine import handle_init

    ws = _make_workspace(tmp_path)
    result = json.loads(handle_init({
        "workspace": str(ws),
        "run_id": "triage-test-001",
        "source": "operator-request",
    }))
    assert result.get("ok"), f"unexpected error: {result}"

    manifest_path = ws / ".uacp" / "state" / "runs" / "triage-test-001.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    assert manifest["current_phase"] == "triage"
