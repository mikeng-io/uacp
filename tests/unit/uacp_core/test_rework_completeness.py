"""#135 / #149: the rework_completeness closure engine (codes prefixed ``RW_``).

A standard-track rework (#109) carries the parent's VERIFY findings forward on the
manifest's ``carried_findings`` map, but nothing yet forced the rework to actually
ADDRESS them — a rework could close having silently ignored a carried defect. This
engine makes closure fail-closed on that: for a run with carried findings, EVERY
carried key must be discharged by an explicit disposition (the existing LN
``handled_findings_chain`` grammar — ``handling_classification`` ∈
remediated|expanded|justified|deferred|accepted_warning|rejected_with_reason), an
accepted-exception classification must carry a rationale/exception artifact, AND (#149)
the disposition must be a well-formed canonical ``handled_findings_chain`` item (all 8
base fields present, valid enums) — a class-evidence-only disposition that is otherwise
structurally invalid must NOT discharge (fail-CLOSED). A carried key with no disposition
→ RW_CARRIED_FINDING_UNADDRESSED (block). No-op for non-rework runs (empty
carried_findings, depth 0) so the common path is untouched.

These are UNIT tests over hand-seeded run manifests + artifacts on disk (the engine is
a pure read-only validator: (workspace, run_id) -> [Violation], never raises).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml
from engines.rework_completeness import (
    _CANONICAL_DISPOSITION_REQUIRED_FIELDS,
    _VALID_CLASSES,
    _VALID_FINDING_CLASSIFICATIONS,
    _VALID_HEARTGATE_VALIDATIONS,
    validate_rework_completeness,
)


def _codes(violations) -> set[str]:
    return {v.code for v in violations}


def _canonical(original_finding_id: str, **over: Any) -> dict[str, Any]:
    """A FULL, canonically well-formed handled_findings_chain item (all 8 base fields,
    valid enums) — what a real rework author writes per the #135/#149 execute-skill
    briefing. Override any field via kwargs (e.g. to drop one for a fail-closed test)."""
    item: dict[str, Any] = {
        "original_finding_id": original_finding_id,
        "finding_classification": "concern",
        "handling_classification": "remediated",
        "handling_artifact_path": "executions/run-B-checkpoint-001.yaml",
        "followup_required": False,
        "owner": "rework-author",
        "residual_risk": "no material residual risk on the fix branch",
        "heartgate_validation": "pass",
    }
    item.update(over)
    return item


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
        _canonical("verification_package", handling_classification="remediated"),
        _canonical(
            "assessment",
            handling_classification="justified",
            accepted_exception_artifact="verification/run-B-exception.yaml",
            residual_risk="accepted: parent finding not reproducible on the fix branch",
        ),
    ]
    _seed_rework(temp_uacp_root, "run-B", carried=_CARRIED, chain=chain)
    v = validate_rework_completeness(temp_uacp_root, "run-B")
    assert v == [], _codes(v)


def test_disposition_correlates_by_artifact_path_too(temp_uacp_root: Path):
    """A disposition may reference the carried finding by its PARENT-RELATIVE path
    (original_artifact_path) in addition to the manifest key. The canonical item grammar
    still requires original_finding_id, so both are present and correlate to the SAME
    finding (conjunctive match)."""
    chain = [
        _canonical(
            "verification_package",
            original_artifact_path="verification/run-A-verify-selection.yaml",
            handling_artifact_path="x.yaml",
        ),
        _canonical(
            "assessment",
            original_artifact_path="verification/run-A-piv-assessment.yaml",
            handling_classification="expanded",
            handling_artifact_path="y.yaml",
        ),
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
                _canonical("verification_package", handling_artifact_path="x"),
                _canonical("assessment", handling_artifact_path="y"),
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
                _canonical("verification_package", handling_artifact_path="x"),
                _canonical("assessment", handling_artifact_path="y"),
            ],
        },
    )
    assert validate_rework_completeness(temp_uacp_root, "run-B") == []


# ------------------------------------------------------------------ blocking paths
def test_carried_finding_without_disposition_blocks(temp_uacp_root: Path):
    # only the first carried key is disposed; 'assessment' is ignored
    chain = [_canonical("verification_package", handling_artifact_path="x.yaml")]
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


def test_bare_remediated_without_fix_evidence_blocks(temp_uacp_root: Path):
    """A remediation must LINK its fix via handling_artifact_path — a bare
    {original_finding_id, handling_classification: remediated} with no fix pointer has no
    class-evidence at all, so it is UNEVIDENCED (not a well-formedness MALFORMED)."""
    chain = [
        _canonical("verification_package", handling_artifact_path="executions/run-B-cp-001.yaml"),
        # class-evidence MISSING: remediated with no handling_artifact_path
        {"original_finding_id": "assessment", "handling_classification": "remediated"},
    ]
    _seed_rework(temp_uacp_root, "run-B", carried=_CARRIED, chain=chain)
    v = validate_rework_completeness(temp_uacp_root, "run-B")
    rem = [x for x in v if x.code == "RW_CARRIED_FINDING_REMEDIATION_UNEVIDENCED"]
    assert len(rem) == 1 and rem[0].severity == "block", _codes(v)
    assert rem[0].detail["carried_finding"] == "assessment"
    # the properly-evidenced, well-formed verification_package remediation is NOT flagged
    assert not any(x.detail.get("carried_finding") == "verification_package" for x in v)


def test_accepted_exception_without_rationale_blocks(temp_uacp_root: Path):
    """An accepted-exception classification (justified/deferred/…) must carry a rationale
    or an exception artifact — a 'deferred' with no class-evidence is UNEVIDENCED at the
    class-evidence layer (EXCEPTION_INCOMPLETE), before the well-formedness floor."""
    chain = [
        _canonical("verification_package", handling_artifact_path="x.yaml"),
        # class-evidence MISSING: deferred with neither residual_risk nor exception artifact
        {"original_finding_id": "assessment", "handling_classification": "deferred"},
    ]
    _seed_rework(temp_uacp_root, "run-B", carried=_CARRIED, chain=chain)
    v = validate_rework_completeness(temp_uacp_root, "run-B")
    assert "RW_CARRIED_FINDING_EXCEPTION_INCOMPLETE" in _codes(v), _codes(v)
    assert all(
        x.severity == "block" for x in v if x.code == "RW_CARRIED_FINDING_EXCEPTION_INCOMPLETE"
    )


# ------------------------------------------------- #149: well-formedness floor (fail-CLOSED)
def test_class_evidence_complete_but_missing_base_fields_is_malformed(temp_uacp_root: Path):
    """#149 fail-CLOSED: a disposition that carries its class-evidence (handling_artifact_path)
    but OMITS canonical base fields is NOT a valid discharge — it blocks as MALFORMED and the
    message names every missing field."""
    # verification_package: full canonical (discharges). assessment: class-evidence-complete
    # (has handling_artifact_path) but missing finding_classification/followup_required/owner/
    # residual_risk/heartgate_validation.
    chain = [
        _canonical("verification_package", handling_artifact_path="x.yaml"),
        {
            "original_finding_id": "assessment",
            "handling_classification": "remediated",
            "handling_artifact_path": "executions/run-B-cp-002.yaml",
        },
    ]
    _seed_rework(temp_uacp_root, "run-B", carried=_CARRIED, chain=chain)
    v = validate_rework_completeness(temp_uacp_root, "run-B")
    mal = [x for x in v if x.code == "RW_CARRIED_FINDING_DISPOSITION_MALFORMED"]
    assert len(mal) == 1 and mal[0].severity == "block", _codes(v)
    assert mal[0].detail["carried_finding"] == "assessment"
    for field in (
        "finding_classification",
        "followup_required",
        "owner",
        "residual_risk",
        "heartgate_validation",
    ):
        assert field in mal[0].message, (field, mal[0].message)
        assert f"missing {field}" in mal[0].detail["defects"], (field, mal[0].detail["defects"])
    # the well-formed verification_package disposition is NOT flagged
    assert not any(x.detail.get("carried_finding") == "verification_package" for x in v)


def test_single_missing_base_field_is_malformed(temp_uacp_root: Path):
    """Dropping ONE required base field (owner) from an otherwise-complete canonical item
    still fails closed as MALFORMED naming exactly that field."""
    chain = [
        _canonical("verification_package", handling_artifact_path="x.yaml"),
        _canonical("assessment", owner=""),  # empty owner — one defect
    ]
    _seed_rework(temp_uacp_root, "run-B", carried=_CARRIED, chain=chain)
    v = validate_rework_completeness(temp_uacp_root, "run-B")
    mal = [x for x in v if x.code == "RW_CARRIED_FINDING_DISPOSITION_MALFORMED"]
    assert len(mal) == 1, _codes(v)
    assert mal[0].detail["defects"] == ["missing owner"], mal[0].detail["defects"]


def test_invalid_enum_value_is_malformed(temp_uacp_root: Path):
    """An invalid enum value (heartgate_validation='maybe') on an otherwise-complete item is
    MALFORMED — the well-formedness floor mirrors the validator's enum check."""
    chain = [
        _canonical("verification_package", handling_artifact_path="x.yaml"),
        _canonical("assessment", heartgate_validation="maybe"),
    ]
    _seed_rework(temp_uacp_root, "run-B", carried=_CARRIED, chain=chain)
    v = validate_rework_completeness(temp_uacp_root, "run-B")
    mal = [x for x in v if x.code == "RW_CARRIED_FINDING_DISPOSITION_MALFORMED"]
    assert len(mal) == 1 and mal[0].severity == "block", _codes(v)
    assert any("invalid heartgate_validation" in d for d in mal[0].detail["defects"]), mal[0].detail


def test_invalid_finding_classification_is_malformed(temp_uacp_root: Path):
    """An invalid finding_classification enum also trips the floor."""
    chain = [
        _canonical("verification_package", handling_artifact_path="x.yaml"),
        _canonical("assessment", finding_classification="catastrophe"),
    ]
    _seed_rework(temp_uacp_root, "run-B", carried=_CARRIED, chain=chain)
    v = validate_rework_completeness(temp_uacp_root, "run-B")
    mal = [x for x in v if x.code == "RW_CARRIED_FINDING_DISPOSITION_MALFORMED"]
    assert len(mal) == 1, _codes(v)
    assert any("invalid finding_classification" in d for d in mal[0].detail["defects"]), mal[0].detail


def test_full_canonical_item_discharges(temp_uacp_root: Path):
    """A FULL canonical item (all 8 base fields, valid enums) discharges — no violation."""
    chain = [
        _canonical("verification_package"),
        _canonical("assessment", handling_artifact_path="executions/run-B-cp-002.yaml"),
    ]
    _seed_rework(temp_uacp_root, "run-B", carried=_CARRIED, chain=chain)
    assert validate_rework_completeness(temp_uacp_root, "run-B") == []


def test_malformed_and_incomplete_prefer_the_class_evidence_layer(temp_uacp_root: Path):
    """Reporting precedence: if NO match is class-evidence-complete, the class-evidence code
    (UNEVIDENCED / EXCEPTION_INCOMPLETE) fires — MALFORMED is only reported when a match DID
    carry its class-evidence but is base-malformed. Here assessment has ONLY malformed-and-
    incomplete matches (remediated, no fix pointer) → UNEVIDENCED, not MALFORMED."""
    chain = [
        _canonical("verification_package"),
        # remediated, missing handling_artifact_path (no class-evidence) AND missing base fields
        {"original_finding_id": "assessment", "handling_classification": "remediated"},
    ]
    _seed_rework(temp_uacp_root, "run-B", carried=_CARRIED, chain=chain)
    codes = _codes(validate_rework_completeness(temp_uacp_root, "run-B"))
    assert "RW_CARRIED_FINDING_REMEDIATION_UNEVIDENCED" in codes, codes
    assert "RW_CARRIED_FINDING_DISPOSITION_MALFORMED" not in codes, codes


def test_cross_talk_disposition_discharges_neither_finding(temp_uacp_root: Path):
    """Gaming vector (gemini #135 P1): ONE entry whose original_finding_id names finding A
    while its original_artifact_path names finding B must discharge NEITHER — correlation is
    conjunctive over the fields the entry declares, so a disposition that names two different
    findings matches none of them (a disjunctive match would let it discharge both)."""
    chain = [
        _canonical(
            "verification_package",  # names finding A (by key)
            original_artifact_path="verification/run-A-piv-assessment.yaml",  # names B (by path)
            handling_artifact_path="x.yaml",
        )
    ]
    _seed_rework(temp_uacp_root, "run-B", carried=_CARRIED, chain=chain)
    codes = [x.code for x in validate_rework_completeness(temp_uacp_root, "run-B")]
    # BOTH carried findings remain unaddressed — the mixed entry rescued neither
    assert codes.count("RW_CARRIED_FINDING_UNADDRESSED") == 2, codes


def test_multiple_incomplete_exception_classes_all_reported(temp_uacp_root: Path):
    """When several entries match one finding and all are incomplete accepted-exceptions (no
    class-evidence), the violation names every failing class (not just the first)."""
    chain = [
        _canonical("verification_package"),
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
        _canonical("verification_package"),
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
    chain = [_canonical("verification_package"), _canonical("assessment")]
    _seed_rework(temp_uacp_root, "run-B", carried=_CARRIED, chain=chain, rework_depth=1)
    v = validate_rework_completeness(temp_uacp_root, "run-B")
    esc = [x for x in v if x.code == "RW_REWORK_DEPTH_ESCALATION"]
    assert len(esc) == 1, _codes(v)
    assert esc[0].severity == "warn"  # escalates, does NOT block
    # and the well-disposed rework still has NO blocker
    assert not any(x.severity == "block" for x in v), _codes(v)


def test_depth_below_threshold_does_not_escalate(temp_uacp_root: Path):
    chain = [_canonical("verification_package"), _canonical("assessment")]
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
    chain = [_canonical("verification_package"), _canonical("assessment")]
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


# ------------------------------------------ #149 behavioral parity with the canonical validator
def test_engine_required_fields_match_the_canonical_validator():
    """Tie the engine's canonical required set to the validator's grammar WITHOUT importing the
    validator's private local list: an entry populated with EXACTLY the engine's
    _CANONICAL_DISPOSITION_REQUIRED_FIELDS (valid enums) yields NO 'missing' BLOCK from
    validate_handled_findings_chain; dropping any one engine-required field yields a
    'missing <field>' BLOCK. If the two required sets ever diverge, this test fails."""
    repo_scripts = Path(__file__).resolve().parents[3] / "scripts"
    if str(repo_scripts) not in sys.path:
        sys.path.insert(0, str(repo_scripts))
    import validate_uacp_artifacts as vua

    def _missing_blocks(entry: dict) -> list[str]:
        issues: list[str] = []
        vua.validate_handled_findings_chain(
            Path("synthetic.yaml"),
            {"source_negative_findings_present": True, "handled_findings_chain": [entry]},
            issues,
        )
        return [i for i in issues if " missing " in i]

    # valid enums for the enum-typed required fields
    complete = {
        f: "concern"
        if f == "finding_classification"
        else "remediated"
        if f == "handling_classification"
        else "pass"
        if f == "heartgate_validation"
        else False
        if f == "followup_required"
        else "value"
        for f in _CANONICAL_DISPOSITION_REQUIRED_FIELDS
    }
    # (a) a full engine-required entry yields NO 'missing' block
    assert _missing_blocks(dict(complete)) == [], _missing_blocks(dict(complete))
    # (b) dropping any one engine-required field yields a 'missing <field>' block
    for field in _CANONICAL_DISPOSITION_REQUIRED_FIELDS:
        partial = dict(complete)
        del partial[field]
        blocks = _missing_blocks(partial)
        assert any(f"missing {field}" in b for b in blocks), (field, blocks)
    # (c) the engine's MIRRORED enum sets must match the validator's canonical enums, so a
    # future enum change to the grammar cannot silently diverge the engine (gemini #149 P3).
    assert _VALID_FINDING_CLASSIFICATIONS == frozenset(vua.VALID_FINDING_CLASSIFICATIONS)
    assert _VALID_CLASSES == frozenset(vua.VALID_HANDLING_CLASSIFICATIONS)
    assert _VALID_HEARTGATE_VALIDATIONS == frozenset(vua.VALID_HEARTGATE_VALIDATIONS)
