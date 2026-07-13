"""#135: the rework_completeness closure engine (codes prefixed ``RW_``).

A standard-track rework (#109) carries the parent's VERIFY findings forward on the
manifest's ``carried_findings`` map, but nothing yet forced the rework to actually
ADDRESS them — a rework could close having silently ignored a carried defect. This
engine makes closure fail-closed on that: for a run with carried findings, EVERY
carried key must be discharged by an explicit disposition (the existing LN
``handled_findings_chain`` grammar — ``handling_classification`` ∈
remediated|expanded|justified|deferred|accepted_warning|rejected_with_reason), and an
accepted-exception classification must carry a rationale/exception artifact. A carried
key with no disposition → RW_CARRIED_FINDING_UNADDRESSED (block). No-op for non-rework
runs (empty carried_findings, depth 0) so the common path is untouched.

These are UNIT tests over hand-seeded run manifests + artifacts on disk (the engine is
a pure read-only validator: (workspace, run_id) -> [Violation], never raises).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from engines.rework_completeness import validate_rework_completeness


def _codes(violations) -> set[str]:
    return {v.code for v in violations}


def _write_manifest(root: Path, run_id: str, **fields: Any) -> None:
    base = {
        "run_id": run_id,
        "status": "resolved",
        "current_phase": "resolved",
        "track": "standard",
        "authority": {"source": "operator-request", "status": "pass"},
    }
    base.update(fields)
    (root / ".uacp" / "state" / "runs" / f"{run_id}.yaml").write_text(
        yaml.safe_dump(base, sort_keys=False), encoding="utf-8"
    )


def _write_artifact(root: Path, rel: str, data: dict) -> None:
    p = root / ".uacp" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


# A rework run whose resolve-readiness artifact disposes each carried finding via the
# LN handled_findings_chain grammar. Two carried keys, two dispositions.
_CARRIED = {
    "verification_package": "verification/run-A-verify-selection.yaml",
    "assessment": "verification/run-A-piv-assessment.yaml",
}


def _seed_rework(root: Path, run_id: str, *, carried: dict, chain: list, rework_depth: int = 1):
    """Seed a resolved rework run whose resolve-readiness artifact carries ``chain``."""
    rr_rel = f"verification/{run_id}-resolve-readiness.yaml"
    _write_manifest(
        root,
        run_id,
        reworks="run-A",
        rework_depth=rework_depth,
        carried_findings=carried,
        artifacts={"resolve_readiness": rr_rel},
    )
    _write_artifact(
        root, rr_rel, {"kind": "uacp.verify_resolve_readiness", "handled_findings_chain": chain}
    )


# ------------------------------------------------------------------ passing path
def test_rework_with_full_dispositions_passes(temp_uacp_root: Path):
    chain = [
        {
            "original_finding_id": "verification_package",
            "handling_classification": "remediated",
            "handling_artifact_path": "executions/run-B-checkpoint-001.yaml",
        },
        {
            "original_finding_id": "assessment",
            "handling_classification": "justified",
            "accepted_exception_artifact": "verification/run-B-exception.yaml",
            "residual_risk": "accepted: parent finding not reproducible on the fix branch",
        },
    ]
    _seed_rework(temp_uacp_root, "run-B", carried=_CARRIED, chain=chain)
    v = validate_rework_completeness(temp_uacp_root, "run-B")
    assert v == [], _codes(v)


def test_disposition_correlates_by_artifact_path_too(temp_uacp_root: Path):
    """A disposition may reference the carried finding by its PARENT-RELATIVE path
    (original_artifact_path) instead of the manifest key."""
    chain = [
        {
            "original_artifact_path": "verification/run-A-verify-selection.yaml",
            "handling_classification": "remediated",
            "handling_artifact_path": "x.yaml",
        },
        {
            "original_artifact_path": "verification/run-A-piv-assessment.yaml",
            "handling_classification": "expanded",
            "handling_artifact_path": "y.yaml",
        },
    ]
    _seed_rework(temp_uacp_root, "run-B", carried=_CARRIED, chain=chain)
    assert validate_rework_completeness(temp_uacp_root, "run-B") == []


def test_disposition_in_governed_writer_readiness_artifact_is_scanned(temp_uacp_root: Path):
    """A child that authored its readiness via uacp_entity_write registers it under the
    GOVERNED-WRITER key 'verify_resolve_readiness' (kind.removeprefix('uacp.')), not the
    'resolve_readiness' alias — the engine must scan that artifact for dispositions too, or a
    real governed rework's dispositions are ignored (Codex #135)."""
    rr_rel = "verification/run-B-resolve-readiness.yaml"
    _write_manifest(
        temp_uacp_root,
        "run-B",
        reworks="run-A",
        rework_depth=1,
        carried_findings=_CARRIED,
        artifacts={"verify_resolve_readiness": rr_rel},  # governed-writer key
    )
    _write_artifact(
        temp_uacp_root,
        rr_rel,
        {
            "kind": "uacp.verify_resolve_readiness",
            "handled_findings_chain": [
                {
                    "original_finding_id": "verification_package",
                    "handling_classification": "remediated",
                    "handling_artifact_path": "x",
                },
                {
                    "original_finding_id": "assessment",
                    "handling_classification": "remediated",
                    "handling_artifact_path": "y",
                },
            ],
        },
    )
    assert validate_rework_completeness(temp_uacp_root, "run-B") == []


def test_disposition_in_governed_resolve_closure_artifact_is_scanned(temp_uacp_root: Path):
    """A rework authoring its dispositions during RESOLVE records them in the governed
    RESOLVE artifact, registered as 'resolve_closure' / 'resolve_package'
    (kind.removeprefix('uacp.')). The engine scans EVERY registered artifact for the chain,
    so a correctly-documented RESOLVE-authored disposition is not falsely blocked (Codex
    #135) — no curated key list to miss."""
    rc_rel = "resolutions/run-B-resolve-closure.yaml"
    _write_manifest(
        temp_uacp_root,
        "run-B",
        reworks="run-A",
        rework_depth=1,
        carried_findings=_CARRIED,
        artifacts={"resolve_closure": rc_rel},  # governed RESOLVE key, not lessons/verify
    )
    _write_artifact(
        temp_uacp_root,
        rc_rel,
        {
            "kind": "uacp.resolve_closure",
            "handled_findings_chain": [
                {
                    "original_finding_id": "verification_package",
                    "handling_classification": "remediated",
                    "handling_artifact_path": "x",
                },
                {
                    "original_finding_id": "assessment",
                    "handling_classification": "remediated",
                    "handling_artifact_path": "y",
                },
            ],
        },
    )
    assert validate_rework_completeness(temp_uacp_root, "run-B") == []


# ------------------------------------------------------------------ blocking paths
def test_carried_finding_without_disposition_blocks(temp_uacp_root: Path):
    # only the first carried key is disposed; 'assessment' is ignored
    chain = [
        {
            "original_finding_id": "verification_package",
            "handling_classification": "remediated",
            "handling_artifact_path": "x.yaml",
        }
    ]
    _seed_rework(temp_uacp_root, "run-B", carried=_CARRIED, chain=chain)
    v = validate_rework_completeness(temp_uacp_root, "run-B")
    assert "RW_CARRIED_FINDING_UNADDRESSED" in _codes(v), _codes(v)
    # names the ignored finding, and blocks (not warns)
    dropped = [x for x in v if x.code == "RW_CARRIED_FINDING_UNADDRESSED"]
    assert len(dropped) == 1 and dropped[0].severity == "block"
    assert "assessment" in dropped[0].message


def test_no_dispositions_at_all_blocks_every_carried_finding(temp_uacp_root: Path):
    """A rework that ignored ALL carried findings (no chain / no artifact) is the exact
    defect this engine exists to stop."""
    _write_manifest(
        temp_uacp_root,
        "run-B",
        reworks="run-A",
        rework_depth=1,
        carried_findings=_CARRIED,
        artifacts={},  # nothing registered → no dispositions anywhere
    )
    v = validate_rework_completeness(temp_uacp_root, "run-B")
    codes = [x.code for x in v]
    assert codes.count("RW_CARRIED_FINDING_UNADDRESSED") == 2, codes


def test_accepted_exception_without_rationale_blocks(temp_uacp_root: Path):
    """An accepted-exception classification (justified/deferred/…) must carry a rationale
    or an exception artifact — an empty 'justified' is not an explicit accepted-exception."""
    chain = [
        {
            "original_finding_id": "verification_package",
            "handling_classification": "remediated",
            "handling_artifact_path": "x.yaml",
        },
        {
            "original_finding_id": "assessment",
            "handling_classification": "deferred",
        },  # no rationale
    ]
    _seed_rework(temp_uacp_root, "run-B", carried=_CARRIED, chain=chain)
    v = validate_rework_completeness(temp_uacp_root, "run-B")
    assert "RW_CARRIED_FINDING_EXCEPTION_INCOMPLETE" in _codes(v), _codes(v)
    assert all(
        x.severity == "block" for x in v if x.code == "RW_CARRIED_FINDING_EXCEPTION_INCOMPLETE"
    )


def test_cross_talk_disposition_discharges_neither_finding(temp_uacp_root: Path):
    """Gaming vector (gemini #135 P1): ONE entry whose original_finding_id names finding A
    while its original_artifact_path names finding B must discharge NEITHER — correlation is
    conjunctive over the fields the entry declares, so a disposition that names two different
    findings matches none of them (a disjunctive match would let it discharge both)."""
    chain = [
        {
            "original_finding_id": "verification_package",  # names finding A (by key)
            "original_artifact_path": "verification/run-A-piv-assessment.yaml",  # names finding B (by path)
            "handling_classification": "remediated",
            "handling_artifact_path": "x.yaml",
        }
    ]
    _seed_rework(temp_uacp_root, "run-B", carried=_CARRIED, chain=chain)
    codes = [x.code for x in validate_rework_completeness(temp_uacp_root, "run-B")]
    # BOTH carried findings remain unaddressed — the mixed entry rescued neither
    assert codes.count("RW_CARRIED_FINDING_UNADDRESSED") == 2, codes


def test_multiple_incomplete_exception_classes_all_reported(temp_uacp_root: Path):
    """When several entries match one finding and all are incomplete accepted-exceptions, the
    violation names every failing class (not just the first)."""
    chain = [
        {
            "original_finding_id": "verification_package",
            "handling_classification": "remediated",
            "handling_artifact_path": "x.yaml",
        },
        {"original_finding_id": "assessment", "handling_classification": "justified"},
        {"original_finding_id": "assessment", "handling_classification": "deferred"},
    ]
    _seed_rework(temp_uacp_root, "run-B", carried=_CARRIED, chain=chain)
    v = [
        x
        for x in validate_rework_completeness(temp_uacp_root, "run-B")
        if x.code == "RW_CARRIED_FINDING_EXCEPTION_INCOMPLETE"
    ]
    assert len(v) == 1 and v[0].detail["handling_classifications"] == ["deferred", "justified"], v


def test_unknown_handling_classification_blocks(temp_uacp_root: Path):
    """A disposition with a classification outside the LN enum does not discharge the
    finding — it is not a recognized handling decision."""
    chain = [
        {
            "original_finding_id": "verification_package",
            "handling_classification": "remediated",
            "handling_artifact_path": "x.yaml",
        },
        {"original_finding_id": "assessment", "handling_classification": "looks-fine-to-me"},
    ]
    _seed_rework(temp_uacp_root, "run-B", carried=_CARRIED, chain=chain)
    assert "RW_CARRIED_FINDING_UNADDRESSED" in _codes(
        validate_rework_completeness(temp_uacp_root, "run-B")
    )


# ------------------------------------------------------------------ no-op safety
def test_non_rework_run_is_noop(temp_uacp_root: Path):
    """The common path: a run with no carried findings and depth 0 is never touched."""
    _write_manifest(temp_uacp_root, "run-plain", carried_findings={}, rework_depth=0, artifacts={})
    assert validate_rework_completeness(temp_uacp_root, "run-plain") == []


def test_missing_manifest_is_single_block_not_crash(temp_uacp_root: Path):
    v = validate_rework_completeness(temp_uacp_root, "does-not-exist")
    assert len(v) == 1 and v[0].severity == "block"


# ------------------------------------------------------------------ depth escalation (P4)
def test_rework_depth_escalation_warns_not_blocks(temp_uacp_root: Path):
    """A long rework chain (depth >= max_rework_depth) ESCALATES as a WARNING — visible,
    never a hard block (the #109 'visible bound', now thresholded)."""
    # low threshold via config override so depth=1 trips it
    (temp_uacp_root / ".uacp" / "config.toml").write_text(
        "[heartgate]\nmax_rework_depth = 1\n", encoding="utf-8"
    )
    chain = [
        {
            "original_finding_id": "verification_package",
            "handling_classification": "remediated",
            "handling_artifact_path": "x",
        },
        {
            "original_finding_id": "assessment",
            "handling_classification": "remediated",
            "handling_artifact_path": "y",
        },
    ]
    _seed_rework(temp_uacp_root, "run-B", carried=_CARRIED, chain=chain, rework_depth=1)
    v = validate_rework_completeness(temp_uacp_root, "run-B")
    esc = [x for x in v if x.code == "RW_REWORK_DEPTH_ESCALATION"]
    assert len(esc) == 1, _codes(v)
    assert esc[0].severity == "warn"  # escalates, does NOT block
    # and the well-disposed rework still has NO blocker
    assert not any(x.severity == "block" for x in v), _codes(v)


def test_depth_below_threshold_does_not_escalate(temp_uacp_root: Path):
    chain = [
        {
            "original_finding_id": "verification_package",
            "handling_classification": "remediated",
            "handling_artifact_path": "x",
        },
        {
            "original_finding_id": "assessment",
            "handling_classification": "remediated",
            "handling_artifact_path": "y",
        },
    ]
    _seed_rework(temp_uacp_root, "run-B", carried=_CARRIED, chain=chain, rework_depth=1)
    # default threshold (5) not reached at depth 1
    assert not any(
        x.code == "RW_REWORK_DEPTH_ESCALATION"
        for x in validate_rework_completeness(temp_uacp_root, "run-B")
    )


# ------------------------------------------------------------------ council hardening (D2/D3/D4)
def test_max_rework_depth_zero_escalates_every_rework(temp_uacp_root: Path):
    """max_rework_depth=0 is an explicit operator intent (escalate on every rework) and must
    be honored, not silently replaced by the code default (council #135 D2)."""
    (temp_uacp_root / ".uacp" / "config.toml").write_text(
        "[heartgate]\nmax_rework_depth = 0\n", encoding="utf-8"
    )
    chain = [
        {
            "original_finding_id": "verification_package",
            "handling_classification": "remediated",
            "handling_artifact_path": "x",
        },
        {
            "original_finding_id": "assessment",
            "handling_classification": "remediated",
            "handling_artifact_path": "y",
        },
    ]
    _seed_rework(temp_uacp_root, "run-B", carried=_CARRIED, chain=chain, rework_depth=1)
    v = validate_rework_completeness(temp_uacp_root, "run-B")
    assert any(x.code == "RW_REWORK_DEPTH_ESCALATION" for x in v), _codes(v)


def test_non_str_artifact_key_does_not_crash_engine(temp_uacp_root: Path):
    """A non-str manifest artifacts key must not break the never-raises contract (council
    #135 D3): the engine skips it and still enforces (the finding stays unaddressed)."""
    _write_manifest(
        temp_uacp_root,
        "run-B",
        reworks="run-A",
        rework_depth=1,
        carried_findings={"assessment": "verification/run-A-piv-assessment.yaml"},
        artifacts={123: "verification/junk.yaml"},  # non-str key
    )
    v = validate_rework_completeness(temp_uacp_root, "run-B")  # must not raise
    assert "RW_CARRIED_FINDING_UNADDRESSED" in _codes(v), _codes(v)


def test_discharge_enforced_when_finalized_at_set_even_if_status_not_resolved(temp_uacp_root: Path):
    """The discharge check keys off finalized_at OR status==resolved (council #135 D4): a
    finalized run cannot bypass enforcement by carrying a non-'resolved' status token."""
    _write_manifest(
        temp_uacp_root,
        "run-B",
        status="active",  # deliberately NOT the literal "resolved"
        finalized_at="2026-07-13T00:00:00Z",
        reworks="run-A",
        rework_depth=1,
        carried_findings={"assessment": "verification/run-A-piv-assessment.yaml"},
        artifacts={},  # no disposition
    )
    assert "RW_CARRIED_FINDING_UNADDRESSED" in _codes(
        validate_rework_completeness(temp_uacp_root, "run-B")
    )
