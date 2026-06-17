"""State-machine transition tests for the brainstorm phase (T9)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_STATE_DIR = Path(__file__).resolve().parents[3] / "skills" / "uacp-state" / "scripts"
if str(_STATE_DIR) not in sys.path:
    sys.path.insert(0, str(_STATE_DIR))

from state_machine import VALID_TRANSITIONS, handle_init, handle_transition


@pytest.fixture()
def bs_workspace(tmp_path: Path) -> Path:
    """Workspace with a run initialized at brainstorm."""
    ws = tmp_path
    (ws / ".uacp").mkdir()
    result = json.loads(handle_init({
        "workspace": str(ws),
        "run_id": "bs-trans-001",
        "source": "operator-request",
        "initial_phase": "brainstorm",
    }))
    assert result.get("ok"), result
    return ws


@pytest.fixture()
def triage_workspace(tmp_path: Path) -> Path:
    """Workspace with a run initialized directly at triage (existing behavior)."""
    ws = tmp_path
    (ws / ".uacp").mkdir()
    result = json.loads(handle_init({
        "workspace": str(ws),
        "run_id": "triage-direct-001",
        "source": "operator-request",
    }))
    assert result.get("ok"), result
    return ws


# --- VALID_TRANSITIONS graph assertions ---

def test_valid_transitions_includes_brainstorm_to_triage() -> None:
    assert "brainstorm" in VALID_TRANSITIONS
    assert "triage" in VALID_TRANSITIONS["brainstorm"]


def test_valid_transitions_triage_still_accepts_propose() -> None:
    """triage->propose must still work (existing edge unbroken)."""
    assert "propose" in VALID_TRANSITIONS.get("triage", set())


# --- handle_transition tests ---

def test_brainstorm_to_triage_allowed(bs_workspace: Path) -> None:
    result = json.loads(handle_transition({
        "workspace": str(bs_workspace),
        "run_id": "bs-trans-001",
        "from_phase": "brainstorm",
        "to_phase": "triage",
    }))
    assert result.get("ok"), f"expected ok, got: {result}"
    assert result["from_phase"] == "brainstorm"
    assert result["to_phase"] == "triage"


def test_triage_still_accepts_none_entry(triage_workspace: Path) -> None:
    """Direct triage entry (without brainstorm) must still be possible."""
    # A run started at triage should be able to advance to propose.
    result = json.loads(handle_transition({
        "workspace": str(triage_workspace),
        "run_id": "triage-direct-001",
        "from_phase": "triage",
        "to_phase": "propose",
    }))
    assert result.get("ok"), f"expected ok, got: {result}"


# NOTE: test_brainstorm_to_terminal is intentionally omitted from this slice.
# state_machine_projection() drops every ->terminal edge, so brainstorm->terminal
# is not in VALID_TRANSITIONS and handle_transition will refuse it. The explore-and-bail
# path (brainstorm->abort) is a tracked follow-up needing the aborted-status path designed.
# Add a test here when that slice ships.


def test_brainstorm_to_plan_blocked(bs_workspace: Path) -> None:
    """brainstorm->plan must be refused (phase-skipping)."""
    result = json.loads(handle_transition({
        "workspace": str(bs_workspace),
        "run_id": "bs-trans-001",
        "from_phase": "brainstorm",
        "to_phase": "plan",
    }))
    assert not result.get("ok")
    assert "not allowed" in result.get("error", "")


def test_brainstorm_to_propose_blocked(bs_workspace: Path) -> None:
    """brainstorm->propose must be refused (must flow through triage first)."""
    result = json.loads(handle_transition({
        "workspace": str(bs_workspace),
        "run_id": "bs-trans-001",
        "from_phase": "brainstorm",
        "to_phase": "propose",
    }))
    assert not result.get("ok")
    assert "not allowed" in result.get("error", "")
