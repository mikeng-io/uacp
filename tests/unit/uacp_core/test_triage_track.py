"""Unit tests for the `track` field in triage artifacts (goal-driven track, Task 1).

Asserts:
- track: "standard"     -> no track-related BLOCK
- track: "goal-driven"  -> no track-related BLOCK
- track: "bogus"        -> a BLOCK mentioning track
- no track key at all   -> no track-related BLOCK (absent == standard, back-compat)
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_validator():
    """Load the offline validator module fresh (mirrors Heartgate's in-process exec)."""
    validator_path = REPO_ROOT / "scripts" / "validate_uacp_artifacts.py"
    spec = importlib.util.spec_from_file_location("uacp_validate_track_pin", validator_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _minimal_triage(extra: dict) -> dict:
    """Return a triage object with all required fields satisfied, plus any extras."""
    base = {
        "kind": "triage",
        "triage_id": "t-001",
        "request_summary": "test summary",
        "authority": {"status": "pass"},
        "factor_scores": {},
        "granularity_level": 1,
        "routing_outcome": "standard",
        "next_step": "propose",
    }
    base.update(extra)
    return base


def _track_blocks(issues: list[str]) -> list[str]:
    """Filter issues list to those that mention 'track'."""
    return [i for i in issues if "track" in i.lower()]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_track_standard_no_block():
    """track: 'standard' is valid — no track-related BLOCK."""
    module = _load_validator()
    issues: list[str] = []
    module.validate_triage(Path("triage/t-001.yaml"), _minimal_triage({"track": "standard"}), issues)
    assert not _track_blocks(issues), f"unexpected track issues: {issues}"


def test_track_goal_driven_no_block():
    """track: 'goal-driven' is valid — no track-related BLOCK."""
    module = _load_validator()
    issues: list[str] = []
    module.validate_triage(Path("triage/t-001.yaml"), _minimal_triage({"track": "goal-driven"}), issues)
    assert not _track_blocks(issues), f"unexpected track issues: {issues}"


def test_track_invalid_value_emits_block():
    """track: 'bogus' must produce a BLOCK mentioning track."""
    module = _load_validator()
    issues: list[str] = []
    module.validate_triage(Path("triage/t-001.yaml"), _minimal_triage({"track": "bogus"}), issues)
    blocks = _track_blocks(issues)
    assert blocks, f"expected a track BLOCK but got none; all issues: {issues}"
    assert any("BLOCK" in i for i in blocks), f"expected BLOCK severity in track issues: {blocks}"


def test_track_absent_no_block():
    """Absent track key must not produce any track-related BLOCK (back-compat: defaults to standard)."""
    module = _load_validator()
    issues: list[str] = []
    module.validate_triage(Path("triage/t-001.yaml"), _minimal_triage({}), issues)
    assert not _track_blocks(issues), f"unexpected track issues when key absent: {issues}"
