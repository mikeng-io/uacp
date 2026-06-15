"""Unit tests for expanded CurrentPointer, LedgerEntry, and new EscalationRecord models.

Slice 4a Task 3 — codify run-state schemas from config/state.yaml.

Covers:
- CurrentPointer expanded optional fields + CURRENT_POINTER_REQUIRED_FIELDS constant
- LedgerEntry expanded optional fields with Literal types
- EscalationRecord new model (engines/domain/escalation.py)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from typing import get_args

from engines.domain import (
    CurrentPointer,
    CURRENT_POINTER_REQUIRED_FIELDS,
    LedgerEntry,
    EscalationRecord,
)


# ---------------------------------------------------------------------------
# CURRENT_POINTER_REQUIRED_FIELDS constant
# ---------------------------------------------------------------------------

EXPECTED_REQUIRED_FIELDS = (
    "active_run_id",
    "active_run_manifest",
    "mutation_policy",
    "current_transition_artifact",
    "kanban_binding_artifact",
    "kanban_board_slug",
    "bootstrap_closed",
    "governed_mutation_active",
)


def test_current_pointer_required_fields_is_tuple():
    assert isinstance(CURRENT_POINTER_REQUIRED_FIELDS, tuple)


def test_current_pointer_required_fields_has_eight_entries():
    assert len(CURRENT_POINTER_REQUIRED_FIELDS) == 8


def test_current_pointer_required_fields_matches_yaml():
    assert set(CURRENT_POINTER_REQUIRED_FIELDS) == set(EXPECTED_REQUIRED_FIELDS)


# ---------------------------------------------------------------------------
# CurrentPointer — base fields still optional (extra=allow preserved)
# ---------------------------------------------------------------------------

def test_current_pointer_accepts_minimal():
    cp = CurrentPointer()
    assert cp.active_run_id is None
    assert cp.active_run_manifest is None


def test_current_pointer_accepts_full_required_fields():
    cp = CurrentPointer(
        active_run_id="uacp-run-001",
        active_run_manifest="state/runs/uacp-run-001.yaml",
        mutation_policy="uacp_state_required",
        current_transition_artifact="state/runs/uacp-run-001-transition.yaml",
        kanban_binding_artifact="state/kanban.yaml",
        kanban_board_slug="uacp-board",
        bootstrap_closed=True,
        governed_mutation_active=True,
    )
    assert cp.active_run_id == "uacp-run-001"
    assert cp.mutation_policy == "uacp_state_required"
    assert cp.bootstrap_closed is True


def test_current_pointer_accepts_all_uacp_mode_values():
    for mode in ("manual", "semi_auto", "supervised_auto", "full_auto"):
        cp = CurrentPointer.model_validate({"active_run_id": "r1", "uacp_mode": mode})
        assert cp.uacp_mode == mode  # type: ignore[attr-defined]


def test_current_pointer_rejects_invalid_uacp_mode():
    with pytest.raises(ValidationError):
        CurrentPointer.model_validate({"active_run_id": "r1", "uacp_mode": "godmode"})


def test_current_pointer_allows_extra_fields():
    cp = CurrentPointer.model_validate({"active_run_id": "r1", "notes": ["some note"]})
    assert cp.notes == ["some note"]  # type: ignore[attr-defined]


def test_current_pointer_optional_fields_default_none():
    cp = CurrentPointer()
    for field in (
        "mutation_policy", "current_transition_artifact",
        "kanban_binding_artifact", "kanban_board_slug",
        "bootstrap_closed", "governed_mutation_active", "uacp_mode",
    ):
        assert getattr(cp, field) is None


# ---------------------------------------------------------------------------
# LedgerEntry — expanded optional fields
# ---------------------------------------------------------------------------

def test_ledger_entry_accepts_minimal():
    entry = LedgerEntry(gate="EXECUTE->VERIFY", run_id="run-001", ts=1000)
    assert entry.gate == "EXECUTE->VERIFY"


def test_ledger_entry_accepts_phase():
    entry = LedgerEntry(gate="G", run_id="r", ts=1, phase="execute")
    assert entry.phase == "execute"


def test_ledger_entry_rejects_invalid_result():
    with pytest.raises(ValidationError):
        LedgerEntry(gate="G", run_id="r", ts=1, result="explode")


def test_ledger_entry_accepts_valid_result_values():
    for val in ("pass", "warn", "block"):
        e = LedgerEntry(gate="G", run_id="r", ts=1, result=val)
        assert e.result == val


def test_ledger_entry_rejects_invalid_reviewer():
    with pytest.raises(ValidationError):
        LedgerEntry(gate="G", run_id="r", ts=1, reviewer="robot")


def test_ledger_entry_accepts_valid_reviewer_values():
    for val in ("model", "codex", "council", "operator"):
        e = LedgerEntry(gate="G", run_id="r", ts=1, reviewer=val)
        assert e.reviewer == val


def test_ledger_entry_optional_fields_default_none():
    e = LedgerEntry()
    assert e.phase is None
    assert e.result is None
    assert e.reviewer is None


# ---------------------------------------------------------------------------
# EscalationRecord — new model from escalations.record_schema
# ---------------------------------------------------------------------------

VALID_ESCALATION: dict = {
    "run_id": "uacp-run-001",
    "phase": "execute",
    "mode": "supervised_auto",
    "trigger": "trigger_blast_radius_high",
    "severity": "warn",
    "reason": "blast radius exceeds threshold",
    "authority_artifact": "verification/phase4-verify.yaml",
    "ts": 1717234567,
}


def test_escalation_record_accepts_valid():
    rec = EscalationRecord.model_validate(VALID_ESCALATION)
    assert rec.run_id == "uacp-run-001"
    assert rec.mode == "supervised_auto"
    assert rec.severity == "warn"


def test_escalation_record_rejects_invalid_mode():
    bad = {**VALID_ESCALATION, "mode": "godmode"}
    with pytest.raises(ValidationError):
        EscalationRecord.model_validate(bad)


def test_escalation_record_rejects_invalid_severity():
    bad = {**VALID_ESCALATION, "severity": "doom"}
    with pytest.raises(ValidationError):
        EscalationRecord.model_validate(bad)


def test_escalation_record_accepts_all_modes():
    for mode in ("manual", "semi_auto", "supervised_auto", "full_auto"):
        rec = EscalationRecord.model_validate({**VALID_ESCALATION, "mode": mode})
        assert rec.mode == mode


def test_escalation_record_accepts_all_severities():
    for sev in ("info", "warn", "block"):
        rec = EscalationRecord.model_validate({**VALID_ESCALATION, "severity": sev})
        assert rec.severity == sev


def test_escalation_record_accepts_optional_details():
    data = {**VALID_ESCALATION, "details": {"foo": "bar"}}
    rec = EscalationRecord.model_validate(data)
    assert rec.details == {"foo": "bar"}


def test_escalation_record_details_defaults_none():
    rec = EscalationRecord.model_validate(VALID_ESCALATION)
    assert rec.details is None


@pytest.mark.parametrize("field", [
    "run_id", "phase", "mode", "trigger", "severity", "reason", "authority_artifact", "ts",
])
def test_escalation_record_rejects_missing_required_field(field: str):
    data = {k: v for k, v in VALID_ESCALATION.items() if k != field}
    with pytest.raises(ValidationError):
        EscalationRecord.model_validate(data)


def test_escalation_mode_enum_values():
    """EscalationRecord.mode Literal covers exactly the 4 UACP modes."""
    import typing
    hints = typing.get_type_hints(EscalationRecord)
    mode_type = hints["mode"]
    values = set(get_args(mode_type))
    assert values == {"manual", "semi_auto", "supervised_auto", "full_auto"}


def test_escalation_severity_enum_values():
    """EscalationRecord.severity Literal covers exactly info|warn|block."""
    import typing
    hints = typing.get_type_hints(EscalationRecord)
    sev_type = hints["severity"]
    values = set(get_args(sev_type))
    assert values == {"info", "warn", "block"}
