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

_FIXTURES = pathlib.Path(__file__).resolve().parents[3] / "tests" / "e2e" / "fixtures"


def _load(name: str) -> dict:
    with open(_FIXTURES / name) as fh:
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
# DOCUMENT kinds — the fixture-backed YAML artifacts (artifact_schema.py fold-in, D41).
# These are REAL kernel kinds with golden full-shape fixtures under tests/e2e/fixtures/;
# the schemas are authored from those fixtures + the artifact_schema.py field vocab, so
# they match reality (not the spike). Each kind is closed-world (D9), pins its `kind`
# (const), and its golden fixture is validated end-to-end (the non-vacuity anchor).
# ====================================================================================


# --- uacp.scope (PLAN->EXECUTE write-boundary; ScopeSchema) --------------------------
def test_golden_scope_fixture_validates():
    assert validate("uacp.scope", _load("scope.yaml")) == []


def test_scope_bad_blast_radius_fails():
    doc = {
        "kind": "uacp.scope",
        "run_id": "r1",
        "write_paths": ["docs/"],
        "blast_radius": "huge",  # not in {low,medium,high,critical}
        "rollback_path": "none",
    }
    errs = validate("uacp.scope", doc)
    assert errs and any("blast_radius" in e or "huge" in e for e in errs), errs


def test_scope_missing_write_paths_fails():
    doc = {"kind": "uacp.scope", "run_id": "r1", "blast_radius": "low", "rollback_path": "none"}
    errs = validate("uacp.scope", doc)
    assert errs and any("write_paths" in e for e in errs), errs


def test_scope_optional_fields_ok():
    doc = {
        "kind": "uacp.scope",
        "run_id": "r1",
        "write_paths": ["src/"],
        "blast_radius": "medium",
        "rollback_path": "git revert",
        "read_paths": ["docs/"],
        "forbidden_paths": [".uacp/"],
    }
    assert validate("uacp.scope", doc) == []


def test_scope_unknown_key_fails():
    doc = {
        "kind": "uacp.scope",
        "run_id": "r1",
        "write_paths": ["docs/"],
        "blast_radius": "low",
        "rollback_path": "none",
        "write_path": ["typo"],  # closed-world must reject
    }
    errs = validate("uacp.scope", doc)
    assert errs and any("write_path" in e or "additional" in e.lower() for e in errs), errs


def test_scope_wrong_kind_const_fails():
    doc = {
        "kind": "uacp.plan",
        "run_id": "r1",
        "write_paths": ["docs/"],
        "blast_radius": "low",
        "rollback_path": "none",
    }
    errs = validate("uacp.scope", doc)
    assert errs and any(e.startswith("kind") for e in errs), errs


def test_scope_no_writes_intended_and_self_patch_authority_ok():
    # AS-BUILT: Heartgate._validate_scope_artifact accepts the no_writes_intended
    # sentinel (for empty write_paths) and a self_patch_write_authority block. The
    # closed-world schema must not reject a scope the runtime gate accepts. (Pre-fix
    # this failed: additionalProperties=false rejected both keys — Codex P2 #1.)
    doc = {
        "kind": "uacp.scope",
        "run_id": "r1",
        "write_paths": [],
        "no_writes_intended": True,
        "blast_radius": "low",
        "rollback_path": "none--write-only-artifact",
        "self_patch_write_authority": {
            "enabled": True,
            "reason": "uacp self-repair",
            "authority_artifact": "proposals/r1-intent.md",
            "owner": "core",
            "rollback_path": "git revert",
            "verification_obligations": ["suite green"],
            "allowed_prefixes": ["scripts/"],
        },
    }
    assert validate("uacp.scope", doc) == []


# --- uacp.run_registry (state/run-registry.yaml) ------------------------------------
def test_golden_run_registry_fixture_validates():
    assert validate("uacp.run_registry", _load("run_registry.yaml")) == []


def test_run_registry_missing_active_runs_fails():
    errs = validate("uacp.run_registry", {"kind": "uacp.run_registry"})
    assert errs and any("active_runs" in e for e in errs), errs


def test_run_registry_active_run_item_ok():
    doc = {
        "kind": "uacp.run_registry",
        "active_runs": [
            {
                "run_id": "r1",
                "phase": "execute",
                "write_paths": ["src/"],
                "scope_artifact_path": "plans/r1-scope.yaml",
                "started_at": 1700000000,
            }
        ],
    }
    assert validate("uacp.run_registry", doc) == []


def test_run_registry_active_run_missing_run_id_fails():
    doc = {"kind": "uacp.run_registry", "active_runs": [{"phase": "execute"}]}
    errs = validate("uacp.run_registry", doc)
    assert errs and any("run_id" in e for e in errs), errs


def test_run_registry_writer_shape_no_kind_validates():
    # AS-BUILT: the uacp_run_registry_update writer emits {schema_version, active_runs}
    # with NO top-level `kind`. The schema must accept the writer's own output. (Pre-fix
    # this failed: `kind` was in required — Codex P2 #2.) This is the writer-shaped doc,
    # not a schema-shaped fixture — the distinction that hid the mismatch.
    doc = {
        "schema_version": "0.1",
        "active_runs": [
            {
                "run_id": "r1",
                "phase": "execute",
                "write_paths": ["src/"],
                "scope_artifact_path": "plans/r1-scope.yaml",
                "started_at": 1700000000,
            }
        ],
    }
    assert validate("uacp.run_registry", doc) == []


# --- uacp.lessons (VERIFY->RESOLVE lessons artifact; LessonsSchema) ------------------
def test_golden_lessons_fixture_validates():
    assert validate("uacp.lessons", _load("lessons.yaml")) == []


def test_lessons_missing_lessons_fails():
    errs = validate("uacp.lessons", {"kind": "uacp.lessons", "run_id": "r1"})
    # Must be the missing-`lessons` schema error, not the registry's "unknown kind".
    assert errs and any("lessons" in e for e in errs) and not any("unknown" in e for e in errs), (
        errs
    )
