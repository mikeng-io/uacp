"""uacp-schema (node 33 reconciliation): per-kind JSON-Schema validation — the pure-leaf registry.

`validate(kind, doc)` returns a list of error strings (empty == valid); it never raises. Shapes are
DERIVED FROM the dominant runtime authority (scripts/validate_uacp_artifacts.py), not authored to
fixtures. Non-vacuous: each invalid case fails for a SPECIFIC reason; each valid case passes so the
schema isn't trivially rejecting everything.

Two layers (node 33):
* node-items (scope_item/work_unit/evidence_obligation/checkpoint/assessment) — closed-world, shape
  only; the real outcome enum is {pass,warn,block,deferred}; coverage (derives_from) is a projection
  invariant, NOT a shape rule (so it's OPTIONAL here).
* document kinds — small ones closed-world; the 9 rich package docs OPEN-world (the runtime validator
  allows extra fields), validating required + kind/phase consts + key enums.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

from engines.domain.schema import has_schema, validate

_FIXTURES = pathlib.Path(__file__).resolve().parents[3] / "tests" / "e2e" / "fixtures"


def _load(name: str) -> dict:
    with open(_FIXTURES / name) as fh:
        return yaml.safe_load(fh)


# --- work_unit: real PIV shape (id+intent+expected_outputs); derives_from OPTIONAL ----------
def test_valid_work_unit_passes():
    assert (
        validate("work_unit", {"id": "wu-1", "intent": "config OAuth", "expected_outputs": ["x"]})
        == []
    )


def test_work_unit_missing_intent_fails():
    errs = validate("work_unit", {"id": "wu-1", "expected_outputs": ["x"]})
    assert errs and any("intent" in e for e in errs), errs


def test_work_unit_derives_from_is_optional():
    # Coverage (derives_from) is a PROJECTION invariant, not a shape rule — the real PIV validator
    # does not require it, so a shape-valid work_unit may omit it (node 33 shape-vs-referential split).
    assert validate("work_unit", {"id": "wu-1", "intent": "x", "expected_outputs": ["o"]}) == []
    assert (
        validate(
            "work_unit",
            {"id": "wu-1", "intent": "x", "expected_outputs": ["o"], "derives_from": ["si-1"]},
        )
        == []
    )


def test_work_unit_unknown_key_fails():
    errs = validate(
        "work_unit", {"id": "wu-1", "intent": "x", "expected_outputs": ["o"], "ntent": "typo"}
    )
    assert errs and any("ntent" in e or "additional" in e.lower() for e in errs), errs


# --- scope_item -----------------------------------------------------------------------------
def test_valid_scope_item_passes():
    assert validate("scope_item", {"id": "si-1", "statement": "Support Google OAuth"}) == []


def test_scope_item_missing_id_fails():
    errs = validate("scope_item", {"statement": "x"})
    assert errs and any("id" in e for e in errs), errs


def test_unknown_kind_is_an_error():
    errs = validate("not_a_kind", {"id": "x"})
    assert errs and any("not_a_kind" in e or "kind" in e for e in errs), errs


# --- evidence_obligation: id+evidence_type+required+sufficiency; work_unit_id OPTIONAL -------
def test_valid_evidence_obligation_passes():
    doc = {"id": "ev-1", "evidence_type": "test", "required": True, "sufficiency": "suite green"}
    assert validate("evidence_obligation", doc) == []


def test_evidence_obligation_missing_evidence_type_fails():
    errs = validate("evidence_obligation", {"id": "ev-1", "required": True, "sufficiency": "x"})
    assert errs and any("evidence_type" in e for e in errs), errs


def test_evidence_obligation_work_unit_id_optional():
    doc = {"id": "ev-1", "evidence_type": "t", "required": False, "sufficiency": "s"}
    assert validate("evidence_obligation", doc) == []  # no work_unit_id -> still valid


# --- checkpoint: result enum {pass,warn,block,deferred} (NOT pass/fail); work_unit_id optional
def test_valid_checkpoint_passes():
    assert validate("checkpoint", {"result": "pass"}) == []


def test_checkpoint_deferred_and_block_are_valid():
    assert validate("checkpoint", {"result": "deferred"}) == []
    assert validate("checkpoint", {"result": "block"}) == []


def test_checkpoint_old_fail_enum_now_rejected():
    # The spike vocab was {pass,fail}; the REAL evidence result is {pass,warn,block,deferred}.
    errs = validate("checkpoint", {"result": "fail"})
    assert errs and any("result" in e or "fail" in e for e in errs), errs


# --- assessment: obligation_id + state(enum) + evidence_refs(>=1) — note STATE not result ---
def test_valid_assessment_passes():
    a = {"obligation_id": "ev-1", "state": "pass", "evidence_refs": ["cp-1"]}
    assert validate("assessment", a) == []


def test_assessment_missing_evidence_refs_fails():
    errs = validate("assessment", {"obligation_id": "ev-1", "state": "pass"})
    assert errs and any("evidence_refs" in e for e in errs), errs


def test_assessment_empty_evidence_refs_fails():
    errs = validate("assessment", {"obligation_id": "ev-1", "state": "pass", "evidence_refs": []})
    assert errs and any("evidence_refs" in e for e in errs), errs


def test_assessment_bad_state_enum_fails():
    errs = validate(
        "assessment", {"obligation_id": "ev-1", "state": "fail", "evidence_refs": ["cp-1"]}
    )
    assert errs and any("state" in e or "fail" in e for e in errs), errs


# ============================================================================================
# DOCUMENT kinds — small/stable closed-world (scope/run_registry/lessons), golden-fixture backed.
# ============================================================================================
def test_golden_scope_fixture_validates():
    assert validate("uacp.scope", _load("scope.yaml")) == []


def test_scope_bad_blast_radius_fails():
    doc = {
        "kind": "uacp.scope",
        "run_id": "r1",
        "write_paths": ["docs/"],
        "blast_radius": "huge",
        "rollback_path": "none",
    }
    errs = validate("uacp.scope", doc)
    assert errs and any("blast_radius" in e or "huge" in e for e in errs), errs


def test_scope_unknown_key_fails():
    doc = {
        "kind": "uacp.scope",
        "run_id": "r1",
        "write_paths": ["docs/"],
        "blast_radius": "low",
        "rollback_path": "none",
        "write_path": ["typo"],
    }
    errs = validate("uacp.scope", doc)
    assert errs and any("write_path" in e or "additional" in e.lower() for e in errs), errs


def test_scope_no_writes_intended_and_self_patch_authority_ok():
    doc = {
        "kind": "uacp.scope",
        "run_id": "r1",
        "write_paths": [],
        "no_writes_intended": True,
        "blast_radius": "low",
        "rollback_path": "none--write-only-artifact",
        "self_patch_write_authority": {"enabled": True, "reason": "x", "owner": "core"},
    }
    assert validate("uacp.scope", doc) == []


def test_golden_run_registry_fixture_validates():
    assert validate("uacp.run_registry", _load("run_registry.yaml")) == []


def test_run_registry_writer_shape_no_kind_validates():
    doc = {
        "schema_version": "0.1",
        "active_runs": [{"run_id": "r1", "phase": "execute", "goal_id": "g1"}],
    }
    assert validate("uacp.run_registry", doc) == []


def test_golden_lessons_fixture_validates():
    assert validate("uacp.lessons", _load("lessons.yaml")) == []


def test_lessons_missing_lessons_fails():
    errs = validate("uacp.lessons", {"kind": "uacp.lessons", "run_id": "r1"})
    assert errs and any("lessons" in e for e in errs) and not any("unknown" in e for e in errs), (
        errs
    )


def test_scope_and_lessons_kind_is_optional_const():
    # GN1-review F1: the wired authority (artifact_schema ScopeSchema/LessonsSchema) does NOT
    # require `kind`, so schema.py must accept a kind-less doc it accepts — kind is optional-const
    # (matching run_registry). But a WRONG kind, when present, still fails the const.
    scope = {"run_id": "r1", "write_paths": ["src/"], "blast_radius": "low", "rollback_path": "n/a"}
    assert validate("uacp.scope", scope) == []
    assert any(
        "const" in e.lower() or e.startswith("kind")
        for e in validate("uacp.scope", {**scope, "kind": "uacp.plan"})
    )
    lessons = {"run_id": "r1", "lessons": []}
    assert validate("uacp.lessons", lessons) == []
    assert any(
        "const" in e.lower() or e.startswith("kind")
        for e in validate("uacp.lessons", {**lessons, "kind": "x"})
    )


# ============================================================================================
# PACKAGE-MODEL document kinds (node 33) — the 9 rich docs, OPEN-world (required + kind/phase
# consts + key enums), derived from validate_uacp_artifacts.py. No golden fixtures yet, so these
# use constructed producer-shaped docs (the non-vacuity anchor is the specific required-field +
# const + enum assertions).
# ============================================================================================
_PACKAGE_KINDS = [
    "uacp.proposal_package_selection",
    "uacp.plan_package_selection",
    "uacp.phase_intent_verification_contract",
    "uacp.execution_checkpoint",
    "uacp.piv_assessment",
    "uacp.verification_package",
    "uacp.verify_resolve_readiness",
    "uacp.resolve_package",
    "uacp.resolve_closure",
]


def test_all_nine_package_kinds_registered():
    assert all(has_schema(k) for k in _PACKAGE_KINDS), [
        k for k in _PACKAGE_KINDS if not has_schema(k)
    ]


@pytest.mark.parametrize("kind", _PACKAGE_KINDS)
def test_package_kind_pins_kind_const(kind):
    # A doc whose `kind` doesn't match the schema's const must fail on `kind` (mis-dispatch guard).
    errs = validate(kind, {"kind": "uacp.WRONG", "phase": "plan", "run_id": "r1"})
    assert errs and any(e.startswith("kind") or "const" in e.lower() for e in errs), (kind, errs)


def _valid_piv() -> dict:
    return {
        "kind": "uacp.phase_intent_verification_contract",
        "phase": "plan",
        "run_id": "r1",
        "applies_to_phase": "execute",
        "phase_intent": {"summary": "x"},
        "work_units": [{"id": "wu-1", "intent": "x", "expected_outputs": ["o"]}],
        "evidence_obligations": [
            {"id": "ev-1", "evidence_type": "t", "required": True, "sufficiency": "s"}
        ],
        "checkpoint_policy": {"required_checkpoints": ["after_each_work_unit"]},
        "intent_drift_conditions": [],
        "next_phase_handoff": {"required_artifacts": [], "pass_condition": "x"},
    }


def test_piv_contract_valid_and_required_and_phase_and_open():
    assert validate("uacp.phase_intent_verification_contract", _valid_piv()) == []
    # missing a required field (work_units) -> fails
    bad = _valid_piv()
    del bad["work_units"]
    assert any("work_units" in e for e in validate("uacp.phase_intent_verification_contract", bad))
    # wrong phase const -> fails
    badp = _valid_piv()
    badp["phase"] = "execute"
    assert any("phase" in e for e in validate("uacp.phase_intent_verification_contract", badp))
    # OPEN-world: an extra field the runtime validator tolerates must NOT be rejected
    extra = _valid_piv()
    extra["author_note"] = "free text"
    assert validate("uacp.phase_intent_verification_contract", extra) == []


def test_execution_checkpoint_required_and_checkpoint_type_enum():
    base = {
        "kind": "uacp.execution_checkpoint",
        "phase": "execute",
        "run_id": "r1",
        "checkpoint_id": "cp-1",
        "piv_contract": "plans/r1-piv.yaml",
        "checkpoint_type": "after_work_unit",
        "work_unit_id": "wu-1",
        "work_performed": {"summary": "x", "produced_outputs": []},
        "decisions": [],
        "evidence": [{"result": "pass"}],
        "intent_drift": {"detected": False},
        "invariants": {},
        "next_phase_readiness": {"status": "ready"},
    }
    assert validate("uacp.execution_checkpoint", base) == []
    bad = dict(base)
    bad["checkpoint_type"] = "made_up"
    assert any(
        "checkpoint_type" in e or "made_up" in e for e in validate("uacp.execution_checkpoint", bad)
    )


def test_piv_assessment_required_assessments():
    base = {
        "kind": "uacp.piv_assessment",
        "phase": "verify",
        "run_id": "r1",
        "piv_contract": "plans/r1-piv.yaml",
        "assessments": [{"obligation_id": "ev-1", "state": "pass", "evidence_refs": ["cp-1"]}],
        "overall_status": "pass",
    }
    assert validate("uacp.piv_assessment", base) == []
    bad = dict(base)
    del bad["assessments"]
    assert any("assessments" in e for e in validate("uacp.piv_assessment", bad))
