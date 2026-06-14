"""E2E deferral-completeness tests: prove validate_deferral_completeness returns
ZERO violations on a run whose deferred items are FULLY specified and carried to
closure, and that each kind of under-specified / dropped deferral is CAUGHT.

NON-VACUITY: ``seed_coherent_run`` produces a resolved run with NO deferred items
anywhere, so the engine would pass it trivially. To make the positive test
MEANINGFUL we inject a fully-specified deferred item into BOTH the run manifest's
``deferred_items`` and the registered closure/lessons artifact's ``deferred_items``
(matched by ``id``), then assert the engine actually inspected >=1 item (so 0
violations is "a real deferral was fully specified", not "no deferrals").

Grounding (where deferrals live + required fields) is documented in the engine
module; tests mirror it: required per-item fields are ``owner`` / ``residual_risk``
/ ``next_phase_obligation`` (per config/artifact-schemas.yaml deferred.requires +
config/evidence-clusters.yaml), read from the manifest ``deferred_items`` list and
the closure artifact registered under ``manifest.artifacts['lessons']``.
"""

from __future__ import annotations

import copy
from pathlib import Path

import yaml
from engines.base import Violation
from engines.deferral_completeness import validate_deferral_completeness

from tests.e2e.test_coherence import (
    _load_manifest_raw,
    _write_manifest_raw,
    seed_coherent_run,
)

# A fully-specified deferred item: owner + residual_risk + next_phase_obligation,
# with an id so the cross-phase carry-forward check can correlate it.
_COMPLETE_ITEM = {
    "id": "D1",
    "owner": "platform-team",
    "residual_risk": "Runtime selector remains unvalidated under load.",
    "next_phase_obligation": "Re-run load profile once selector lands.",
    "reason": "Out of scope for this run.",
}

_LESSONS_REL_TMPL = ".outputs/{run_id}-lessons.yaml"


def _codes(violations) -> set[str]:
    return {v.code for v in violations}


def _read_lessons(root: Path, run_id: str) -> dict:
    return yaml.safe_load((root / _LESSONS_REL_TMPL.format(run_id=run_id)).read_text())


def _write_lessons(root: Path, run_id: str, data: dict) -> None:
    (root / _LESSONS_REL_TMPL.format(run_id=run_id)).write_text(
        yaml.safe_dump(data, sort_keys=False)
    )


def seed_run_with_deferral(root: Path, run_id: str, item: dict) -> None:
    """Seed a coherent resolved run, then record ``item`` as a deferred item in
    BOTH the manifest and the closure/lessons artifact (carried forward)."""
    seed_coherent_run(root, run_id)

    manifest = _load_manifest_raw(root, run_id)
    manifest["deferred_items"] = [copy.deepcopy(item)]
    _write_manifest_raw(root, run_id, manifest)

    lessons = _read_lessons(root, run_id)
    lessons["deferred_items"] = [copy.deepcopy(item)]
    _write_lessons(root, run_id, lessons)


# ---------------------------------------------------------------- positive test
def test_complete_deferral_has_zero_violations(temp_uacp_root: Path, valid_run_id: str):
    seed_run_with_deferral(temp_uacp_root, valid_run_id, _COMPLETE_ITEM)
    violations = validate_deferral_completeness(temp_uacp_root, valid_run_id)
    assert violations == [], (
        f"expected zero violations, got: {[(v.code, v.message) for v in violations]}"
    )
    assert all(isinstance(v, Violation) for v in violations)


def test_positive_is_non_vacuous(temp_uacp_root: Path, valid_run_id: str):
    """Guard against a vacuous pass: the run the engine reads MUST actually carry
    >=1 deferred item in BOTH the manifest and the closure artifact, otherwise 0
    violations proves nothing about field-completeness."""
    seed_run_with_deferral(temp_uacp_root, valid_run_id, _COMPLETE_ITEM)

    manifest = _load_manifest_raw(temp_uacp_root, valid_run_id)
    assert isinstance(manifest.get("deferred_items"), list)
    assert len(manifest["deferred_items"]) >= 1

    lessons = _read_lessons(temp_uacp_root, valid_run_id)
    assert isinstance(lessons.get("deferred_items"), list)
    assert len(lessons["deferred_items"]) >= 1

    # And the inspected item carries every required field (so the positive is a
    # real "fully-specified" assertion, not "field happened to be absent").
    item = manifest["deferred_items"][0]
    for field in ("owner", "residual_risk", "next_phase_obligation"):
        assert item.get(field), field


# ------------------------------------------------- teeth: missing owner
def test_missing_owner_fires(temp_uacp_root: Path, valid_run_id: str):
    seed_run_with_deferral(temp_uacp_root, valid_run_id, _COMPLETE_ITEM)
    assert "DF_DEFERRAL_MISSING_OWNER" not in _codes(
        validate_deferral_completeness(temp_uacp_root, valid_run_id)
    )

    manifest = _load_manifest_raw(temp_uacp_root, valid_run_id)
    del manifest["deferred_items"][0]["owner"]
    _write_manifest_raw(temp_uacp_root, valid_run_id, manifest)

    codes = _codes(validate_deferral_completeness(temp_uacp_root, valid_run_id))
    assert "DF_DEFERRAL_MISSING_OWNER" in codes, codes


# ------------------------------------------------- teeth: missing residual_risk
def test_missing_residual_risk_fires(temp_uacp_root: Path, valid_run_id: str):
    seed_run_with_deferral(temp_uacp_root, valid_run_id, _COMPLETE_ITEM)
    assert "DF_DEFERRAL_MISSING_RESIDUAL_RISK" not in _codes(
        validate_deferral_completeness(temp_uacp_root, valid_run_id)
    )

    manifest = _load_manifest_raw(temp_uacp_root, valid_run_id)
    del manifest["deferred_items"][0]["residual_risk"]
    _write_manifest_raw(temp_uacp_root, valid_run_id, manifest)

    codes = _codes(validate_deferral_completeness(temp_uacp_root, valid_run_id))
    assert "DF_DEFERRAL_MISSING_RESIDUAL_RISK" in codes, codes


# ------------------------------------------------- teeth: missing obligation
def test_missing_obligation_fires(temp_uacp_root: Path, valid_run_id: str):
    seed_run_with_deferral(temp_uacp_root, valid_run_id, _COMPLETE_ITEM)
    assert "DF_DEFERRAL_MISSING_OBLIGATION" not in _codes(
        validate_deferral_completeness(temp_uacp_root, valid_run_id)
    )

    # An EMPTY value (not just an absent key) must still be treated as missing.
    manifest = _load_manifest_raw(temp_uacp_root, valid_run_id)
    manifest["deferred_items"][0]["next_phase_obligation"] = "   "
    _write_manifest_raw(temp_uacp_root, valid_run_id, manifest)

    codes = _codes(validate_deferral_completeness(temp_uacp_root, valid_run_id))
    assert "DF_DEFERRAL_MISSING_OBLIGATION" in codes, codes


# ------------------------------------------- teeth: deferred-then-dropped at resolve
def test_dropped_at_resolve_fires(temp_uacp_root: Path, valid_run_id: str):
    seed_run_with_deferral(temp_uacp_root, valid_run_id, _COMPLETE_ITEM)
    assert "DF_DEFERRAL_DROPPED_AT_RESOLVE" not in _codes(
        validate_deferral_completeness(temp_uacp_root, valid_run_id)
    )

    # Drop the deferred item from the closure artifact while it remains declared
    # in the manifest: a resolved run that silently lost a carried risk.
    lessons = _read_lessons(temp_uacp_root, valid_run_id)
    lessons["deferred_items"] = []
    _write_lessons(temp_uacp_root, valid_run_id, lessons)

    codes = _codes(validate_deferral_completeness(temp_uacp_root, valid_run_id))
    assert "DF_DEFERRAL_DROPPED_AT_RESOLVE" in codes, codes


# ----------------------------------------- no-op: a run with no deferrals is clean
def test_no_deferrals_is_clean(temp_uacp_root: Path, valid_run_id: str):
    """Honest limitation: a run that records NO deferred items anywhere yields zero
    violations — absence of deferral data is not a finding."""
    seed_coherent_run(temp_uacp_root, valid_run_id)  # no deferred_items injected
    violations = validate_deferral_completeness(temp_uacp_root, valid_run_id)
    assert violations == [], [(v.code, v.message) for v in violations]


# --------------------------------------------------------- defensive: never raises
def test_never_raises_on_missing_run(temp_uacp_root: Path):
    out = validate_deferral_completeness(temp_uacp_root, "no-such-run")
    assert isinstance(out, list) and out
    assert out[0].code == "DF0_MANIFEST_MISSING"


def test_never_raises_on_garbled_manifest(temp_uacp_root: Path, valid_run_id: str):
    mpath = temp_uacp_root / "state" / "runs" / f"{valid_run_id}.yaml"
    mpath.parent.mkdir(parents=True, exist_ok=True)
    mpath.write_text("this: : : not valid yaml: [")
    out = validate_deferral_completeness(temp_uacp_root, valid_run_id)
    assert isinstance(out, list) and out
