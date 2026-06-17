"""Tests for oracle.tier_config PHASE_TIERS gating table."""
from __future__ import annotations


from engines.oracle.tier_config import OracleMode, PHASE_TIERS, mode_for_phase


def test_phase_tiers_has_all_lifecycle_phases():
    expected_phases = {"brainstorm", "triage", "propose", "plan", "execute", "verify", "resolve"}
    assert expected_phases.issubset(set(PHASE_TIERS.keys()))


def test_propose_and_plan_are_full():
    assert PHASE_TIERS["propose"] == OracleMode.FULL
    assert PHASE_TIERS["plan"] == OracleMode.FULL


def test_brainstorm_and_triage_are_advisory():
    assert PHASE_TIERS["brainstorm"] == OracleMode.ADVISORY
    assert PHASE_TIERS["triage"] == OracleMode.ADVISORY


def test_unknown_phase_returns_none():
    assert mode_for_phase("nonexistent_phase") == OracleMode.NONE


def test_oracle_mode_values_are_strings():
    for mode in OracleMode:
        assert isinstance(mode.value, str)


def test_execute_has_no_external_retrieval():
    """execute phase must map to NONE — no external retrieval during execution."""
    assert PHASE_TIERS["execute"] == OracleMode.NONE


def test_resolve_is_writeback():
    """resolve phase must map to WRITEBACK — the only phase that writes back."""
    assert PHASE_TIERS["resolve"] == OracleMode.WRITEBACK
