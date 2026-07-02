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


# --- uacp.proposal (D43): registered + carries KEYED scope.in_scope[{id,statement}] -----------
_PROPOSAL = {
    "kind": "uacp.proposal",
    "proposal_id": "p-1",
    "run_id": "r1",
    "phase": "propose",
    "triage_artifact": "proposals/r1-triage.yaml",
    "title": "x",
    "objective": "x",
    "scope": {
        "in_scope": [{"id": "si-1", "statement": "Support Google OAuth"}],
        "out_of_scope": [],
    },
    "declared_side_effects": "none",
    "authority": {"status": "pass"},
    "human_involvement": "none",
}


def test_valid_keyed_proposal_passes():
    assert has_schema(
        "uacp.proposal"
    )  # registered (D43) -> entity-write-routable + validate-on-write
    assert validate("uacp.proposal", _PROPOSAL) == []


def test_proposal_bare_string_in_scope_fails():
    # D43: in_scope items must be KEYED {id,statement} (the projection's scope_item nodes); a bare
    # string (the pre-D43 form) fails the typed scope block — so coverage can actually bind.
    bad = {**_PROPOSAL, "scope": {"in_scope": ["bare intent"], "out_of_scope": []}}
    errs = validate("uacp.proposal", bad)
    assert errs and any(("in_scope" in e) or ("scope" in e) or ("id" in e) for e in errs), errs


def test_proposal_empty_in_scope_fails():
    # A proposal must declare >=1 keyed scope_item (else coverage is vacuously satisfied).
    bad = {**_PROPOSAL, "scope": {"in_scope": [], "out_of_scope": []}}
    errs = validate("uacp.proposal", bad)
    assert errs and any("in_scope" in e or "scope" in e or "short" in e.lower() for e in errs), errs


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


# --- uacp.scope code_refs (#85 scope-witness claim): optional, CLOSED {file,name} item shape -----
def test_scope_valid_code_refs_validates():
    doc = {
        "kind": "uacp.scope",
        "run_id": "r1",
        "write_paths": ["src/"],
        "blast_radius": "low",
        "rollback_path": "none",
        "code_refs": [
            {"file": "src/a.py", "name": "Alpha"},
            {"file": "src/b.py", "name": "Beta.method"},
        ],
    }
    assert validate("uacp.scope", doc) == []


def test_scope_code_refs_missing_name_fails():
    doc = {
        "kind": "uacp.scope",
        "run_id": "r1",
        "write_paths": ["src/"],
        "blast_radius": "low",
        "rollback_path": "none",
        "code_refs": [{"file": "src/a.py"}],  # `name` required
    }
    errs = validate("uacp.scope", doc)
    assert errs and any("name" in e or "required" in e.lower() for e in errs), errs


def test_scope_code_refs_extra_key_fails():
    doc = {
        "kind": "uacp.scope",
        "run_id": "r1",
        "write_paths": ["src/"],
        "blast_radius": "low",
        "rollback_path": "none",
        "code_refs": [{"file": "src/a.py", "name": "Alpha", "line": 12}],  # extra key
    }
    errs = validate("uacp.scope", doc)
    assert errs and any("line" in e or "additional" in e.lower() for e in errs), errs


def test_scope_code_refs_empty_list_fails():
    # K8 / design node 02: code_refs requires minItems 1 — an empty list is a schema error
    # at write time, so "declared empty" cannot masquerade as a claim (absence is the ONLY
    # no-claim state, keeping the promotion-time absence-escalation unambiguous).
    doc = {
        "kind": "uacp.scope",
        "run_id": "r1",
        "write_paths": ["src/"],
        "blast_radius": "low",
        "rollback_path": "none",
        "code_refs": [],  # empty list rejected
    }
    errs = validate("uacp.scope", doc)
    assert errs and any(
        "code_refs" in e or "short" in e.lower() or "minitems" in e.lower() for e in errs
    ), errs


def test_scope_no_code_refs_key_is_valid():
    # Absence (the key omitted entirely) is the legitimate no-claim state — NOT rejected.
    doc = {
        "kind": "uacp.scope",
        "run_id": "r1",
        "write_paths": ["src/"],
        "blast_radius": "low",
        "rollback_path": "none",
    }
    assert validate("uacp.scope", doc) == []


def test_scope_code_refs_empty_name_fails():
    doc = {
        "kind": "uacp.scope",
        "run_id": "r1",
        "write_paths": ["src/"],
        "blast_radius": "low",
        "rollback_path": "none",
        "code_refs": [{"file": "src/a.py", "name": ""}],  # empty string rejected
    }
    errs = validate("uacp.scope", doc)
    assert errs and any(
        "name" in e or "short" in e.lower() or "minlength" in e.lower() for e in errs
    ), errs


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
        "work_units": [
            {"id": "wu-1", "intent": "x", "expected_outputs": ["o"], "derives_from": ["si-1"]}
        ],
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
    # D43/Codex PR#8 P1: a work_unit WITHOUT derives_from is rejected at write time (the schema), not
    # only by the offline validator -> coverage can't slip a self-gated plan-exit.
    nocov = _valid_piv()
    nocov["work_units"] = [{"id": "wu-1", "intent": "x", "expected_outputs": ["o"]}]
    assert validate("uacp.phase_intent_verification_contract", nocov), (
        "PIV w/o derives_from must fail"
    )
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
        # boundary / negative-judgment slot — the four kernel boundary invariants
        "invariants": {
            "authority_preserved": True,
            "write_boundary_preserved": True,
            "rollback_preserved": True,
            "privacy_boundary_preserved": True,
        },
        "next_phase_readiness": {"status": "ready"},
    }
    assert validate("uacp.execution_checkpoint", base) == []
    bad = dict(base)
    bad["checkpoint_type"] = "made_up"
    assert any(
        "checkpoint_type" in e or "made_up" in e for e in validate("uacp.execution_checkpoint", bad)
    )
    # the boundary slot is TYPED as an object: a non-object invariants fails. (The four boundary
    # keys are required by the OFFLINE validator, not at write time — so a minimal/in-flight
    # checkpoint with invariants={} is NOT false-rejected here.)
    assert validate("uacp.execution_checkpoint", {**base, "invariants": {}}) == []
    nonobj = dict(base)
    nonobj["invariants"] = "not-an-object"
    assert any("invariants" in e for e in validate("uacp.execution_checkpoint", nonobj))


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


# ============================================================================================
# Lifecycle doc kinds added 2026-06-24 (CMS skill-alignment follow-on): uacp.triage (TRIAGE
# serialize) + uacp.brainstorm_scope_package (BRAINSTORM serialize) — previously path-registered
# only (layout.py) and enforced at the Heartgate transition, NOT write-validated. OPEN-world,
# grounded on the real producers/validators (not invented). Non-vacuity = the required/enum/const
# assertions below.
# ============================================================================================


def test_triage_and_brainstorm_kinds_registered():
    assert has_schema("uacp.triage")
    assert has_schema("uacp.brainstorm_scope_package")


def _valid_triage() -> dict:
    return {
        "kind": "uacp.triage",
        "triage_id": "t-1",
        "request_summary": "do the thing",
        "authority": {"status": "pass", "source": "user"},
        "factor_scores": {"impact": 5},
        "routing_outcome": "standard",
        "track": "standard",
        "next_step": "propose",
        # canonical routing/scoring field the consumers read (reconciled 2026-06-24)
        "granularity_level": 6,
    }


def test_triage_valid_required_enums_const_open():
    assert validate("uacp.triage", _valid_triage()) == []
    # missing a required field (request_summary) -> fails
    bad = _valid_triage()
    del bad["request_summary"]
    assert any("request_summary" in e for e in validate("uacp.triage", bad))
    # missing the canonical granularity_level -> fails (producer<->consumer reconciliation)
    bad_g = _valid_triage()
    del bad_g["granularity_level"]
    assert any("granularity_level" in e for e in validate("uacp.triage", bad_g))
    # routing_outcome out of enum -> fails
    bad2 = {**_valid_triage(), "routing_outcome": "made_up"}
    assert any("routing_outcome" in e or "made_up" in e for e in validate("uacp.triage", bad2))
    # authority.status out of enum -> fails
    bad3 = {**_valid_triage(), "authority": {"status": "maybe"}}
    assert any("status" in e or "maybe" in e for e in validate("uacp.triage", bad3))
    # wrong kind const -> fails
    bad4 = {**_valid_triage(), "kind": "uacp.WRONG"}
    assert any(e.startswith("kind") or "const" in e.lower() for e in validate("uacp.triage", bad4))
    # OPEN-world: producer's optional fields (granularity etc.) pass — no false-reject
    extra = {**_valid_triage(), "composite_granularity": 6, "council": {"required": False}}
    assert validate("uacp.triage", extra) == []


def _valid_brainstorm() -> dict:
    # FLAT shape — matches the real gate-passing producer (the e2e entity-write + Heartgate
    # admission contract), NOT the phase-7 doc's selected_scope/estimated_governance wrappers.
    return {
        "kind": "uacp.brainstorm_scope_package",
        "title": "T",
        "description": "D",
        "in_scope": ["a"],
        "declared_side_effects": [],
        "authority": {"source": "user"},
        "routing_advisory": "standard",
    }


def test_brainstorm_scope_package_flat_required_open():
    # FLAT shape (reconciled 2026-06-24): the schema now enforces the flat admission contract — the
    # phase-7 doc, the e2e producer, and the schema all agree on flat root fields.
    assert validate("uacp.brainstorm_scope_package", _valid_brainstorm()) == []  # flat producer
    # the RETIRED nested shape now FAILS (the tightening bites — non-vacuous): no flat title/in_scope
    nested = {
        "kind": "uacp.brainstorm_scope_package",
        "selected_scope": {"title": "T", "description": "D", "in_scope": ["a"]},
        "estimated_governance": {"routing_advisory": "standard"},
        "declared_side_effects": [],
        "authority": {"source": "user"},
    }
    assert any(
        "title" in e or "in_scope" in e or "routing_advisory" in e
        for e in validate("uacp.brainstorm_scope_package", nested)
    ), "retired nested shape must fail on the missing flat root fields"
    # missing a required flat field (in_scope) -> fails
    bad = _valid_brainstorm()
    del bad["in_scope"]
    assert any("in_scope" in e for e in validate("uacp.brainstorm_scope_package", bad))
    # empty title -> fails (non-empty admission rule)
    assert any(
        "title" in e
        for e in validate("uacp.brainstorm_scope_package", {**_valid_brainstorm(), "title": ""})
    )
    # routing_advisory out of the 4-depth enum -> fails. "standard_uacp" (the retired suffixed name)
    # and "block_or_clarify" (impossible when admitting) both reject; "standard" is now the valid value.
    assert any(
        "routing_advisory" in e
        for e in validate(
            "uacp.brainstorm_scope_package",
            {**_valid_brainstorm(), "routing_advisory": "standard_uacp"},
        )
    ), "retired 'standard_uacp' value must now fail the enum"
    assert validate(
        "uacp.brainstorm_scope_package",
        {**_valid_brainstorm(), "routing_advisory": "block_or_clarify"},
    ), "block_or_clarify is not a valid brainstorm routing_advisory"
    # wrong kind const -> fails (mis-dispatch guard)
    bad4 = {**_valid_brainstorm(), "kind": "uacp.WRONG"}
    assert any(
        e.startswith("kind") or "const" in e.lower()
        for e in validate("uacp.brainstorm_scope_package", bad4)
    )
    # OPEN-world: advisory / provenance extras pass
    extra = {**_valid_brainstorm(), "approach_id": "A1", "signals": {}, "risks": []}
    assert validate("uacp.brainstorm_scope_package", extra) == []
    # authority.source must be documented (non-empty) — write-time schema now matches the
    # forced brainstorm-exit gate so the writer cannot accept a package the gate would block.
    assert any(
        "source" in e or "authority" in e
        for e in validate("uacp.brainstorm_scope_package", {**_valid_brainstorm(), "authority": {}})
    ), "authority without a source must fail at write time"
    assert any(
        "source" in e or "authority" in e
        for e in validate(
            "uacp.brainstorm_scope_package", {**_valid_brainstorm(), "authority": {"source": ""}}
        )
    ), "empty authority.source must fail at write time"
    # declared_side_effects must be a list (the contract) — a non-list fails write-time.
    assert any(
        "declared_side_effects" in e
        for e in validate(
            "uacp.brainstorm_scope_package",
            {**_valid_brainstorm(), "declared_side_effects": "nope"},
        )
    ), "non-list declared_side_effects must fail at write time"
    # whitespace-only title / authority.source must fail at write time too — the schema's \S
    # pattern matches the gate's str.strip() check (no write-clean-then-block drift).
    assert validate("uacp.brainstorm_scope_package", {**_valid_brainstorm(), "title": "   "}), (
        "whitespace-only title must fail at write time"
    )
    assert validate(
        "uacp.brainstorm_scope_package", {**_valid_brainstorm(), "authority": {"source": "   "}}
    ), "whitespace-only authority.source must fail at write time"
