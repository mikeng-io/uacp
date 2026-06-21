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

import pathlib

import yaml

from engines.domain.schema import validate

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_OAUTH_FIXTURES = _REPO_ROOT / "design" / "graph-engine" / "spike" / "fixtures" / "oauth-login"
_LESSONS_FIXTURE = _REPO_ROOT / "tests" / "e2e" / "fixtures" / "lessons.yaml"


def _load_yaml(path: pathlib.Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


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


# ====================================================================================
# DOCUMENT kinds (inc 3b) — whole control-plane artifacts that COMPOSE the node-items
# via JSON-Schema $ref/$defs. Properties under test (non-vacuous): the kind is pinned
# (const); the document is closed-world (a typo'd top-level key — e.g. a misspelled
# `work_units` that would silently drop every task — is rejected); and a malformed
# node-item INSIDE a document is rejected by the SAME node-item rule (a work_unit with
# no derives_from fails inside the plan exactly as it does standalone — proving the
# $ref reuse, not a re-inlined copy). The real canonical-form fixtures are validated
# end-to-end so the schemas can't drift from the on-disk shape.
# ====================================================================================


# --- the strongest non-vacuous check: every real canonical-form fixture validates ---
def test_oauth_login_fixtures_validate_against_their_own_kind():
    files = sorted(_OAUTH_FIXTURES.glob("*.yaml"))
    # Guard: an empty glob would make the loop vacuously pass.
    assert files, f"no oauth-login fixtures found under {_OAUTH_FIXTURES}"
    for path in files:
        doc = _load_yaml(path)
        kind = doc.get("kind")
        errs = validate(kind, doc)
        assert errs == [], f"{path.name} (kind={kind!r}) should validate but: {errs}"


# --- uacp.proposal: composes scope_item under scope.in_scope ------------------------
def test_valid_proposal_passes():
    doc = {
        "kind": "uacp.proposal",
        "run_id": "r1",
        "scope": {"in_scope": [{"id": "si-1", "statement": "Support Google OAuth"}]},
    }
    assert validate("uacp.proposal", doc) == []


def test_proposal_wrong_kind_const_fails():
    doc = {"kind": "uacp.plan", "run_id": "r1", "scope": {"in_scope": [{"id": "si-1"}]}}
    errs = validate("uacp.proposal", doc)
    # The error must be on the `kind` field (path "kind: ..."), NOT the registry's
    # "unknown kind" message — i.e. the const is enforced, the kind IS registered.
    assert errs and any(e.startswith("kind") for e in errs), errs


def test_proposal_scope_item_missing_id_fails():
    # Composition: a scope_item inside in_scope must satisfy the scope_item node rule.
    doc = {"kind": "uacp.proposal", "run_id": "r1", "scope": {"in_scope": [{"statement": "x"}]}}
    errs = validate("uacp.proposal", doc)
    assert errs and any("id" in e for e in errs), errs


def test_proposal_empty_in_scope_fails():
    # A proposal with no declared intent is not a proposal (mirrors the kernel's
    # non-empty in_scope admission rule).
    doc = {"kind": "uacp.proposal", "run_id": "r1", "scope": {"in_scope": []}}
    errs = validate("uacp.proposal", doc)
    assert errs and any("in_scope" in e for e in errs), errs


def test_proposal_unknown_top_level_key_fails():
    doc = {
        "kind": "uacp.proposal",
        "run_id": "r1",
        "scope": {"in_scope": [{"id": "si-1"}]},
        "scopes": {},  # typo'd duplicate — closed-world must reject
    }
    errs = validate("uacp.proposal", doc)
    assert errs and any("scopes" in e or "additional" in e.lower() for e in errs), errs


def test_proposal_missing_run_id_fails():
    doc = {"kind": "uacp.proposal", "scope": {"in_scope": [{"id": "si-1"}]}}
    errs = validate("uacp.proposal", doc)
    assert errs and any("run_id" in e for e in errs), errs


# --- uacp.plan: composes work_unit + evidence_obligation ----------------------------
def test_valid_plan_passes():
    doc = {
        "kind": "uacp.plan",
        "run_id": "r1",
        "work_units": [{"id": "wu-1", "title": "x", "derives_from": ["si-1"]}],
        "evidence_obligations": [{"id": "ev-1", "work_unit_id": "wu-1"}],
    }
    assert validate("uacp.plan", doc) == []


def test_plan_work_unit_missing_derives_from_fails():
    # THE composition test: the anti-phantom work_unit rule is enforced INSIDE the plan.
    doc = {"kind": "uacp.plan", "run_id": "r1", "work_units": [{"id": "wu-1", "title": "x"}]}
    errs = validate("uacp.plan", doc)
    assert errs and any("derives_from" in e for e in errs), errs


def test_plan_work_unit_empty_derives_from_fails():
    doc = {
        "kind": "uacp.plan",
        "run_id": "r1",
        "work_units": [{"id": "wu-1", "title": "x", "derives_from": []}],
    }
    errs = validate("uacp.plan", doc)
    assert errs and any("derives_from" in e for e in errs), errs


def test_plan_bad_evidence_obligation_fails():
    # Composition: an obligation inside the plan must still carry work_unit_id.
    doc = {
        "kind": "uacp.plan",
        "run_id": "r1",
        "work_units": [{"id": "wu-1", "title": "x", "derives_from": ["si-1"]}],
        "evidence_obligations": [{"id": "ev-1"}],
    }
    errs = validate("uacp.plan", doc)
    assert errs and any("work_unit_id" in e for e in errs), errs


def test_plan_missing_work_units_fails():
    errs = validate("uacp.plan", {"kind": "uacp.plan", "run_id": "r1"})
    assert errs and any("work_units" in e for e in errs), errs


# --- uacp.execution: composes checkpoint --------------------------------------------
def test_valid_execution_passes():
    doc = {
        "kind": "uacp.execution",
        "run_id": "r1",
        "checkpoints": [{"id": "cp-1", "work_unit_id": "wu-1", "result": "pass"}],
    }
    assert validate("uacp.execution", doc) == []


def test_execution_bad_checkpoint_result_fails():
    doc = {
        "kind": "uacp.execution",
        "run_id": "r1",
        "checkpoints": [{"id": "cp-1", "work_unit_id": "wu-1", "result": "maybe"}],
    }
    errs = validate("uacp.execution", doc)
    assert errs and any("result" in e or "maybe" in e for e in errs), errs


# --- uacp.piv_assessment (the VERIFY document): composes assessment -----------------
def test_valid_piv_assessment_passes():
    doc = {
        "kind": "uacp.piv_assessment",
        "run_id": "r1",
        "assessments": [
            {
                "id": "as-1",
                "obligation_id": "ev-1",
                "work_unit_id": "wu-1",
                "evidence_refs": ["cp-1"],
                "result": "pass",
            }
        ],
    }
    assert validate("uacp.piv_assessment", doc) == []


def test_piv_assessment_self_attesting_fails():
    # Composition: an assessment with no evidence_refs is a self-attesting closure.
    doc = {
        "kind": "uacp.piv_assessment",
        "run_id": "r1",
        "assessments": [{"obligation_id": "ev-1", "result": "pass"}],
    }
    errs = validate("uacp.piv_assessment", doc)
    assert errs and any("evidence_refs" in e for e in errs), errs


# --- uacp.lessons (the RESOLVE document): items stay loose until the lesson node (3d)
def test_valid_lessons_passes():
    doc = {"kind": "uacp.lessons", "run_id": "r1", "lessons": [{"id": "L1", "finding": "x"}]}
    assert validate("uacp.lessons", doc) == []


def test_lessons_golden_fixture_validates():
    doc = _load_yaml(_LESSONS_FIXTURE)
    errs = validate(doc["kind"], doc)
    assert errs == [], errs


def test_lessons_missing_lessons_fails():
    errs = validate("uacp.lessons", {"kind": "uacp.lessons", "run_id": "r1"})
    # Must be the missing-`lessons` schema error, NOT the registry's "unknown kind"
    # message (whose text happens to contain "lessons" via the kind name itself).
    assert errs and any("lessons" in e for e in errs) and not any("unknown" in e for e in errs), (
        errs
    )
