"""Unit tests for the PROPOSE grounding gate (design/grounded-governance/06).

The PROPOSE instance of the same grounding-screening machine the TRIAGE gate is.
``validate_propose_screening`` + ``validate_propose_findings`` make the proposal's PREMISE
(its declared intent + constraints) non-skippable and grounded against a screening that COVERS the
kernel-produced premise substrate (a sha256 over the canonical JSON of the premise-bearing fields).
Any change to the declared premise (re-premising) moves the hash — the fixpoint.

This is the SAME machine as the TRIAGE screening; the ONLY difference is the substrate producer
(the proposal's premise vs the declared scope targets), and PROPOSE has NO deterministic
"targets resolve" floor (a premise is prose, not a resolvable path). So these tests mirror
``test_triage_grounding.py`` minus the unresolved-target floor. Fixtures use a minimal projectable
``.uacp`` workspace with a serialized proposal.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from engines.graph_projection import (
    validate_propose_findings,
    validate_propose_screening,
)
from state_machine import _run_forced_propose_grounding_gate

# The premise-bearing fields the producer reads (mirrors projection._PROPOSE_PREMISE_FIELDS).
_PREMISE_FIELDS = (
    "title",
    "objective",
    "purpose",
    "scope",
    "declared_side_effects",
    "authority",
    "human_involvement",
)


# --------------------------------------------------------------------------- workspace fixture
def _ws(tmp_path: Path, run: str = "r") -> Path:
    """A minimal .uacp workspace with a registered run manifest (no proposal/screening artifact)."""
    base = tmp_path / ".uacp"
    (base / "state" / "runs").mkdir(parents=True)
    (base / "proposals" / run).mkdir(parents=True)
    (base / "state" / "runs" / f"{run}.yaml").write_text(
        yaml.safe_dump({"kind": "uacp.run_state", "run_id": run, "artifacts": {}})
    )
    return tmp_path


def _declare_premise(tmp_path: Path, run: str, **overrides) -> dict:
    """Write a uacp.proposal artifact declaring a premise (intent + constraints), under
    proposals/{run}-proposal.yaml — where the gate reads the run's serialized premise. Returns the
    written doc so a test can hash exactly what it declared."""
    doc = {
        "kind": "uacp.proposal",
        "run_id": run,
        "title": "Ground the PROPOSE screening",
        "objective": "make the declared premise non-skippable and grounded",
        "authority": {"requested_by": "operator", "authorization_source": "go"},
    }
    doc.update(overrides)
    p = tmp_path / ".uacp" / "proposals" / f"{run}-proposal.yaml"
    p.write_text(yaml.safe_dump(doc))
    return doc


def _write_screening(
    tmp_path: Path,
    run: str,
    substrate_hash: str,
    *,
    verdict: str = "clean",
    findings: list[dict] | None = None,
    premise: str | None = None,
    name: str = "propose-screening-0",
) -> None:
    """Place a propose-screening artifact under proposals/{run}/ (the subdir the gate scans + the
    governed writer's home). Loaded leniently by the gate (keys on kind + substrate_hash)."""
    p = tmp_path / ".uacp" / "proposals" / run / f"{name}.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        yaml.safe_dump(
            {
                "kind": "uacp.propose_screening",
                "run_id": run,
                "substrate_hash": substrate_hash,
                "reviewed_premise": premise or "reproduced the declared intent + constraints",
                "verdict": verdict,
                "findings": findings or [],
                "screener": {"model": "test-model", "independence_evidence": None},
            }
        )
    )


def _write_fix_artifact(tmp_path: Path, run: str, name: str = "fix") -> str:
    """A run-bound fix artifact under the PROPOSE evidence dir propose/{run}/ that EXISTS + LOADS
    (so the phase-appropriate _artifact_resolves accepts it — a propose discharge lands in propose/,
    not the late-phase verification/executions dirs). Returns its base-relative path."""
    rel = f"propose/{run}/{name}.yaml"
    dest = tmp_path / ".uacp" / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(yaml.safe_dump({"kind": "uacp.fix", "run_id": run}))
    return rel


def _expected_hash(doc: dict) -> str:
    """Independent oracle for the premise-substrate identity (mirrors _propose_substrate_hash's
    formula: canonical JSON over the present premise fields, sha256)."""
    premise = {k: doc[k] for k in _PREMISE_FIELDS if k in doc and doc[k] is not None}
    payload = json.dumps(premise, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _codes(vs: list) -> list[str]:
    return [v.code for v in vs]


# =========================================================================== coverage floor
def test_no_declared_premise_is_noop(tmp_path):
    # A run that declares NO premise at propose has no substrate -> the gate no-ops (mirrors the
    # triage floor's 'no scope declared'). This is what preserves existing propose->plan runs.
    ws = _ws(tmp_path)
    assert validate_propose_screening(ws, "r") == []
    assert validate_propose_findings(ws, "r") == []


def test_premise_with_covering_clean_screening_passes(tmp_path):
    # A premise + a screening whose substrate_hash matches the current premise and verdict=clean ->
    # [] (non-vacuity: the same fixture without the screening fires MISSING below).
    ws = _ws(tmp_path)
    doc = _declare_premise(tmp_path, "r")
    _write_screening(tmp_path, "r", _expected_hash(doc))
    assert validate_propose_screening(ws, "r") == []
    assert validate_propose_findings(ws, "r") == []


def test_premise_without_screening_fires_missing_warn(tmp_path):
    # A premise declared but NO screening -> exactly one PROPOSE_SCREENING_MISSING at default warn.
    ws = _ws(tmp_path)
    doc = _declare_premise(tmp_path, "r")
    vs = validate_propose_screening(ws, "r")
    assert _codes(vs) == ["PROPOSE_SCREENING_MISSING"], _codes(vs)
    assert vs[0].severity == "warn"
    assert vs[0].detail["substrate_hash"] == _expected_hash(doc)
    # the premise fields are surfaced (non-vacuity: at least the declared intent + authority).
    assert "objective" in vs[0].detail["premise_fields"]


def test_stale_screening_fires_stale(tmp_path):
    # A screening built for the OLD premise, then the premise changes (objective re-worded) -> the
    # old hash no longer covers -> PROPOSE_SCREENING_STALE (the fixpoint: re-screen the re-premised
    # run).
    ws = _ws(tmp_path)
    old = _declare_premise(tmp_path, "r", objective="original intent")
    stale = _expected_hash(old)
    _write_screening(tmp_path, "r", stale)
    # Re-premise: the declared objective moves -> the substrate identity moves.
    new = _declare_premise(tmp_path, "r", objective="a materially different intent")
    assert _expected_hash(new) != stale
    vs = validate_propose_screening(ws, "r")
    assert _codes(vs) == ["PROPOSE_SCREENING_STALE"], _codes(vs)
    assert vs[0].severity == "warn"
    assert stale in vs[0].detail["found_hashes"]


def test_config_block_flips_severity(tmp_path):
    # [verification] propose_screening = "block" -> the MISSING fire is severity block.
    ws = _ws(tmp_path)
    (ws / ".uacp" / "config.toml").write_text('[verification]\npropose_screening = "block"\n')
    _declare_premise(tmp_path, "r")
    vs = validate_propose_screening(ws, "r")
    assert _codes(vs) == ["PROPOSE_SCREENING_MISSING"], _codes(vs)
    assert vs[0].severity == "block"


def test_config_garbage_falls_back_to_warn(tmp_path):
    # A non-{warn,block} value is fail-closed to the SAFE migration default (warn), never block.
    ws = _ws(tmp_path)
    (ws / ".uacp" / "config.toml").write_text('[verification]\npropose_screening = "loud"\n')
    _declare_premise(tmp_path, "r")
    vs = validate_propose_screening(ws, "r")
    assert _codes(vs) == ["PROPOSE_SCREENING_MISSING"], _codes(vs)
    assert vs[0].severity == "warn"


# =========================================================================== findings gate
def test_findings_gate_noop_without_covering_screening(tmp_path):
    # Premise declared, NO covering screening -> the findings gate stays silent (MISSING is the
    # coverage floor's job; the findings gate must not double-report).
    ws = _ws(tmp_path)
    _declare_premise(tmp_path, "r")
    assert validate_propose_findings(ws, "r") == []


def test_findings_undispositioned_blocks(tmp_path):
    # verdict=findings with a discharged finding naming a NONEXISTENT fix path (a label, not a fix)
    # -> one PROPOSE_FINDING_UNDISPOSITIONED.
    ws = _ws(tmp_path)
    doc = _declare_premise(tmp_path, "r")
    finding = {
        "id": "P1",
        "severity": "P1",
        "defect_class": "premise",
        "message": "intent unsupported by reality",
        "substrate_ref": "objective",
        "repro": "reproduce the claim",
        "disposition": {"kind": "discharged", "handling_artifact_path": "propose/r/ghost.yaml"},
    }
    _write_screening(tmp_path, "r", _expected_hash(doc), verdict="findings", findings=[finding])
    vs = validate_propose_findings(ws, "r")
    assert _codes(vs) == ["PROPOSE_FINDING_UNDISPOSITIONED"], _codes(vs)
    assert vs[0].severity == "warn"
    assert vs[0].detail["finding_id"] == "P1"


def test_discharged_finding_with_resolving_artifact_clears(tmp_path):
    # verdict=findings, one discharged finding whose handling_artifact_path RESOLVES (run-bound +
    # exists under propose/{run}/) -> no undispositioned block. Non-vacuity vs the nonexistent-path
    # test above.
    ws = _ws(tmp_path)
    doc = _declare_premise(tmp_path, "r")
    fix_rel = _write_fix_artifact(tmp_path, "r")
    finding = {
        "id": "P1",
        "severity": "P1",
        "defect_class": "premise",
        "message": "intent unsupported by reality",
        "substrate_ref": "objective",
        "repro": "reproduce the claim",
        "disposition": {"kind": "discharged", "handling_artifact_path": fix_rel},
    }
    _write_screening(tmp_path, "r", _expected_hash(doc), verdict="findings", findings=[finding])
    assert validate_propose_findings(ws, "r") == []


def test_adjudicated_finding_complete_clears(tmp_path):
    # A complete adjudication (decision + rationale + cost_if_wrong) clears -> [].
    ws = _ws(tmp_path)
    doc = _declare_premise(tmp_path, "r")
    finding = {
        "id": "P2",
        "severity": "P2",
        "defect_class": "premise",
        "message": "intent leans on an unverified assumption",
        "substrate_ref": "objective",
        "repro": "n/a",
        "disposition": {
            "kind": "adjudicated",
            "decision": "accept",
            "rationale": "assumption acknowledged, bounded",
            "cost_if_wrong": "re-propose",
        },
    }
    _write_screening(tmp_path, "r", _expected_hash(doc), verdict="findings", findings=[finding])
    assert validate_propose_findings(ws, "r") == []


def test_adjudicated_missing_cost_blocks(tmp_path):
    # An INCOMPLETE adjudication (no cost_if_wrong) is not a decision made with eyes open ->
    # PROPOSE_FINDING_UNDISPOSITIONED. Non-vacuity vs the complete adjudication above.
    ws = _ws(tmp_path)
    doc = _declare_premise(tmp_path, "r")
    finding = {
        "id": "P2",
        "severity": "P2",
        "defect_class": "premise",
        "message": "intent leans on an unverified assumption",
        "substrate_ref": "objective",
        "repro": "n/a",
        "disposition": {
            "kind": "adjudicated",
            "decision": "accept",
            "rationale": "assumption acknowledged",
        },
    }
    _write_screening(tmp_path, "r", _expected_hash(doc), verdict="findings", findings=[finding])
    vs = validate_propose_findings(ws, "r")
    assert _codes(vs) == ["PROPOSE_FINDING_UNDISPOSITIONED"], _codes(vs)
    assert vs[0].detail["finding_id"] == "P2"


def test_cannot_verify_verdict_surfaces_inconclusive_warn(tmp_path):
    # verdict=cannot_verify -> PROPOSE_SCREENING_INCONCLUSIVE at warn (abstained, never a silent
    # pass).
    ws = _ws(tmp_path)
    doc = _declare_premise(tmp_path, "r")
    _write_screening(tmp_path, "r", _expected_hash(doc), verdict="cannot_verify")
    vs = validate_propose_findings(ws, "r")
    assert _codes(vs) == ["PROPOSE_SCREENING_INCONCLUSIVE"], _codes(vs)
    assert vs[0].severity == "warn"


def test_findings_gate_config_block_flips_severity(tmp_path):
    # [verification] propose_screening = "block" -> the undispositioned finding fires at block.
    ws = _ws(tmp_path)
    (ws / ".uacp" / "config.toml").write_text('[verification]\npropose_screening = "block"\n')
    doc = _declare_premise(tmp_path, "r")
    finding = {
        "id": "P1",
        "severity": "P1",
        "defect_class": "premise",
        "message": "bug",
        "substrate_ref": "objective",
        "repro": "inspect",
        "disposition": {"kind": "discharged", "handling_artifact_path": "propose/r/ghost.yaml"},
    }
    _write_screening(tmp_path, "r", _expected_hash(doc), verdict="findings", findings=[finding])
    vs = validate_propose_findings(ws, "r")
    assert _codes(vs) == ["PROPOSE_FINDING_UNDISPOSITIONED"], _codes(vs)
    assert vs[0].severity == "block"


# =========================================================================== forced-gate wrapper
def test_forced_gate_noops_when_not_propose_exit(tmp_path):
    # The forced wrapper self-selects to propose: for any OTHER from_phase it short-circuits to
    # ([], []) BEFORE reading state — even with a broken (unscreened) premise in the workspace.
    ws = _ws(tmp_path)
    _declare_premise(tmp_path, "r")  # would surface at propose exit
    assert _run_forced_propose_grounding_gate(ws, "r", "verify", "resolved") == ([], [])
    assert _run_forced_propose_grounding_gate(ws, "r", "plan", "execute") == ([], [])
    assert _run_forced_propose_grounding_gate(ws, "r", "triage", "propose") == ([], [])


def test_forced_gate_surfaces_advisories_at_propose_exit(tmp_path):
    # At propose exit with a premise + no screening + default (warn) config, the wrapper returns the
    # findings as ADVISORIES, never blockers — so the transition is NOT blocked (behavior-preserving
    # default), yet the grounding signal is visible.
    ws = _ws(tmp_path)
    _declare_premise(tmp_path, "r")
    blockers, advisories = _run_forced_propose_grounding_gate(ws, "r", "propose", "plan")
    assert blockers == []
    assert any("PROPOSE_SCREENING_MISSING" in a for a in advisories)


def test_forced_gate_blocks_at_propose_exit_when_config_block(tmp_path):
    # With [verification] propose_screening = "block", the same unscreened premise yields BLOCKERS ->
    # the transition would be blocked. Non-vacuity vs the warn default above.
    ws = _ws(tmp_path)
    (ws / ".uacp" / "config.toml").write_text('[verification]\npropose_screening = "block"\n')
    _declare_premise(tmp_path, "r")
    blockers, _advisories = _run_forced_propose_grounding_gate(ws, "r", "propose", "plan")
    assert any("PROPOSE_SCREENING_MISSING" in b for b in blockers)
