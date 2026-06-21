"""uacp-schema (Slice 1b, inc 3a): per-kind JSON-Schema validation — the pure-leaf node registry.

`validate(kind, doc)` returns a list of error strings (empty == valid); it never raises.
Properties under test (non-vacuous — each invalid case fails for a SPECIFIC reason, and the
valid cases pass so the schema isn't trivially rejecting everything):

* closed-world: an unknown / typo'd key is rejected (additionalProperties:false) — a dropped
  edge can't hide as a misspelled key;
* the KIND-SPECIFIC structural rule: a `work_unit` MUST carry a NON-EMPTY `derives_from`
  (this is what structurally forbids phantom tasks at the source);
* required identity: every node needs an `id`;
* an unknown `kind` is itself an error, never a silent pass.
"""

from __future__ import annotations

from engines.domain.uacp_schema import validate


# --- work_unit: the load-bearing kind (derives_from = the anti-phantom edge) ---------
def test_valid_work_unit_passes():
    errs = validate("work_unit", {"id": "wu-1", "title": "OAuth config", "derives_from": ["si-1"]})
    assert errs == [], errs


def test_work_unit_missing_derives_from_fails():
    errs = validate("work_unit", {"id": "wu-1", "title": "x"})
    assert errs, "a work_unit with no derives_from is an orphan — must fail"
    assert any("derives_from" in e for e in errs), errs


def test_work_unit_empty_derives_from_fails():
    errs = validate("work_unit", {"id": "wu-1", "title": "x", "derives_from": []})
    assert errs, "empty derives_from must fail (a work_unit must derive from >=1 scope_item)"
    assert any("derives_from" in e for e in errs), errs


def test_work_unit_unknown_key_fails():
    errs = validate(
        "work_unit",
        {"id": "wu-1", "title": "x", "derives_from": ["si-1"], "derivesfrom": ["si-2"]},
    )
    assert errs, "a typo'd/unknown key must fail (closed-world)"
    assert any("derivesfrom" in e or "additional" in e.lower() for e in errs), errs


# --- scope_item: proves the registry holds more than one kind ------------------------
def test_valid_scope_item_passes():
    assert validate("scope_item", {"id": "si-1", "statement": "Support Google OAuth"}) == []


def test_scope_item_missing_id_fails():
    errs = validate("scope_item", {"statement": "x"})
    assert errs and any("id" in e for e in errs), errs


# --- an unknown kind is an error, not a silent pass ---------------------------------
def test_unknown_kind_is_an_error():
    errs = validate("not_a_kind", {"id": "x"})
    assert errs, "validating against an unknown kind must report an error"
    assert any("not_a_kind" in e or "kind" in e for e in errs), errs


# --- evidence_obligation: must be FOR a work_unit (the obligation_for FK) ------------
def test_valid_evidence_obligation_passes():
    assert validate("evidence_obligation", {"id": "ev-1", "work_unit_id": "wu-1"}) == []


def test_evidence_obligation_missing_work_unit_id_fails():
    errs = validate("evidence_obligation", {"id": "ev-1"})
    assert errs and any("work_unit_id" in e for e in errs), errs


# --- checkpoint: id + work_unit_id + result(enum pass|fail) --------------------------
def test_valid_checkpoint_passes():
    assert validate("checkpoint", {"id": "cp-1", "work_unit_id": "wu-1", "result": "pass"}) == []


def test_checkpoint_bad_result_enum_fails():
    errs = validate("checkpoint", {"id": "cp-1", "work_unit_id": "wu-1", "result": "maybe"})
    assert errs and any("result" in e or "maybe" in e for e in errs), errs


def test_checkpoint_missing_work_unit_id_fails():
    errs = validate("checkpoint", {"id": "cp-1", "result": "pass"})
    assert errs and any("work_unit_id" in e for e in errs), errs


# --- assessment: obligation_id + evidence_refs(>=1) + result(enum) — no self-attesting
def test_valid_assessment_passes():
    a = {
        "id": "as-1",
        "obligation_id": "ev-1",
        "work_unit_id": "wu-1",
        "evidence_refs": ["cp-1"],
        "result": "pass",
    }
    assert validate("assessment", a) == []


def test_assessment_missing_evidence_refs_fails():
    # An assessment with no evidence is a self-attesting closure — must fail.
    errs = validate("assessment", {"obligation_id": "ev-1", "result": "pass"})
    assert errs and any("evidence_refs" in e for e in errs), errs


def test_assessment_empty_evidence_refs_fails():
    errs = validate("assessment", {"obligation_id": "ev-1", "evidence_refs": [], "result": "pass"})
    assert errs and any("evidence_refs" in e for e in errs), errs


def test_assessment_bad_result_enum_fails():
    a = {"obligation_id": "ev-1", "evidence_refs": ["cp-1"], "result": "inconclusive"}
    errs = validate("assessment", a)
    assert errs and any("result" in e or "inconclusive" in e for e in errs), errs
