"""E2E (#109): a standard-track REWORK run drives the full lifecycle forward under
PRODUCTION gate defaults — the ADR-0016 P2 model (a new forward run, NOT a
verify->execute back-edge).

Parent run A reaches VERIFY and records a finding. A rework run B (`reworks=A`) is a
normal standard run: it RE-AUTHORS its own upstream and drives TRIAGE->...->RESOLVED
through the governed tools, while carrying A's findings forward + a visible
rework_depth. Proves the acceptance: find-bug -> (new run) fix -> re-verify -> resolve
is drivable through governed tools, with NO phase-graph back-edge.

Reuses the production-drivability keystone's seeders so the rework run is driven
through the REAL production gates, not a fixture stub.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
import state_machine
import yaml
from engines.domain import phase_graph

from tests.e2e.driver import Driver
from tests.e2e.test_adaptive_evidence_gate_uacp import REAL_CONFIG, REAL_VALIDATOR
from tests.e2e.test_full_lifecycle import _SEEDERS, PHASES
from tests.e2e.test_lifecycle_production_drivability import (
    _author_lessons,
    _drive_full_lifecycle,
    _seed_triage_artifact,
    _watermark_registered_artifacts,
)

PARENT = "uacp-rework-parent"
CHILD = "uacp-rework-child"


@pytest.fixture
def prod_uacp_root() -> Generator[Path]:
    """Sandbox UACP_ROOT wired with the PRODUCTION config tree (mirrors the keystone)."""
    test_dir = Path(tempfile.mkdtemp(prefix="uacp-rework-e2e-"))
    original_cwd = os.getcwd()
    base = test_dir / ".uacp"
    for sub in (
        "state/runs",
        "state/gate-ledger",
        "state/escalations",
        "plans",
        "proposals",
        "executions",
        "resolutions",
        "verification",
        "knowledge",
    ):
        (base / sub).mkdir(parents=True, exist_ok=True)
    (test_dir / "docs").mkdir(parents=True, exist_ok=True)
    shutil.copytree(REAL_CONFIG, test_dir / "config")
    (test_dir / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(REAL_VALIDATOR, test_dir / "scripts" / "validate_uacp_artifacts.py")
    os.chdir(test_dir)
    old = os.environ.get("UACP_ROOT")
    os.environ["UACP_ROOT"] = str(test_dir)
    try:
        yield test_dir
    finally:
        if old is None:
            os.environ.pop("UACP_ROOT", None)
        else:
            os.environ["UACP_ROOT"] = old
        os.chdir(original_cwd)
        shutil.rmtree(test_dir, ignore_errors=True)


def _manifest(root: Path, run_id: str) -> dict:
    return yaml.safe_load((root / ".uacp" / "state" / "runs" / f"{run_id}.yaml").read_text())


def _author_rework_dispositions(root: Path, run_id: str) -> None:
    """Discharge each carried finding by recording a handled_findings_chain disposition
    in the rework's OWN resolve-readiness artifact (verify_resolve_readiness, open schema)
    — what a real rework agent does per the #135 execute-skill briefing. Authored BEFORE
    the watermark step so artifact_integrity's hash covers it (a post-watermark edit would
    read as AI_TAMPERED, which is correct — the disposition is part of the governed evidence).
    """
    base = root / ".uacp"
    manifest = yaml.safe_load((base / "state" / "runs" / f"{run_id}.yaml").read_text())
    carried = manifest.get("carried_findings") or {}
    rr_rel = (manifest.get("artifacts") or {}).get("resolve_readiness")
    assert rr_rel, "rework did not register a resolve_readiness artifact to dispose into"
    rr_path = base / rr_rel
    doc = yaml.safe_load(rr_path.read_text(encoding="utf-8"))
    # one FULL canonical handled_findings_chain disposition per carried finding, correlated by
    # the carried key — a complete item (#149): all 8 base fields present with valid enums, so
    # the rework_completeness well-formedness floor is cleared, not just the class-evidence field.
    doc["handled_findings_chain"] = [
        {
            "original_finding_id": key,
            "original_artifact_path": path,
            "finding_classification": "concern",
            "handling_classification": "remediated",
            "handling_artifact_path": f"executions/{run_id}-checkpoint-001.yaml",
            # remediated is a HARD_FOLLOWUP handling under the full grammar (#149): it must open
            # a tracked followup (followup_required=true + a council-synthesis artifact) or carry
            # an accepted_exception_artifact. Open the followup so the item is fully well-formed.
            "followup_required": True,
            "followup_council_synthesis_artifact": f"verification/{run_id}-followup-council.yaml",
            "next_phase_obligation": "carry the residual risk into the next phase's acceptance",
            "owner": "rework-author",
            "residual_risk": "no material residual risk on the fix branch",
            "heartgate_validation": "pass",
        }
        for key, path in carried.items()
    ]
    rr_path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def _drive_rework_to_resolved(
    root: Path, run_id: str, reworks: str, *, address_findings: bool = True
) -> dict:
    """Drive a REWORK run through the full standard lifecycle via governed handlers.

    Identical to the keystone's _drive_full_lifecycle EXCEPT the run is initialized
    with `reworks=<parent>` — the rework re-authors its own upstream and drives
    forward normally. When ``address_findings`` (the real path), it also authors a
    disposition for each carried finding before closure; when False, it drives an
    otherwise-valid rework that IGNORED its carried findings (the #135 planted fault).
    """
    driver = Driver(root, run_id)
    init = driver.call(
        "uacp_state_write",
        state_machine.handle_init,
        {
            "workspace": str(root),
            "run_id": run_id,
            "source": "operator-request",
            "reworks": reworks,
        },
        phase="triage",
    )
    assert init.get("ok") is True, init
    assert init["rework_depth"] == 1, init
    assert init["reworks"] == reworks, init

    _seed_triage_artifact(root, run_id)
    for frm, to in PHASES:
        if seeder := _SEEDERS.get((frm, to)):
            seeder(root, run_id)
        tr = driver.call(
            "uacp_state_write",
            state_machine.handle_transition,
            {"workspace": str(root), "run_id": run_id, "from_phase": frm, "to_phase": to},
            phase=frm,
        )
        assert tr.get("ok") is True, f"governed rework transition {frm}->{to} blocked: {tr}"

    _author_lessons(root, run_id)
    if address_findings:
        _author_rework_dispositions(root, run_id)
    _watermark_registered_artifacts(root, run_id)
    return driver.call(
        "uacp_state_write",
        state_machine.handle_finalize,
        {"workspace": str(root), "run_id": run_id},
        phase="verify",
    )


def test_rework_run_drives_forward_to_resolved_carrying_findings(prod_uacp_root: Path) -> None:
    root = prod_uacp_root

    # Parent A drives the REAL standard lifecycle through VERIFY (registering the
    # production verify artifact keys — verification_package / resolve_readiness /
    # assessment — via the keystone seeders), so the carried findings are the ACTUAL
    # keys a real run leaves behind (not a hand-picked stub — Codex #134).
    fin_a = _drive_full_lifecycle(root, PARENT)
    assert fin_a.get("ok") is True, f"parent lifecycle BLOCKED: {fin_a}"
    parent_artifacts = _manifest(root, PARENT)["artifacts"]
    assert "verification_package" in parent_artifacts, parent_artifacts  # non-vacuity guard

    # Rework run B reworks A: carries A's real verify findings + a visible depth,
    # re-authors its own upstream, DISCHARGES each carried finding, and drives the full
    # lifecycle forward to RESOLVED under the production closure sweep (incl. #135's
    # rework_completeness engine).
    fin = _drive_rework_to_resolved(root, CHILD, PARENT)
    assert fin.get("ok") is True, f"rework finalize BLOCKED: {fin}"
    assert fin.get("status") == "resolved", fin
    assert fin.get("closure") in {"pass", "warn"}, fin

    m = _manifest(root, CHILD)
    # Reached the terminal state via the full forward standard path.
    assert m["status"] == "resolved"
    assert m["current_phase"] == "resolved"
    transitions = [
        (h["from_phase"], h["to_phase"])
        for h in m["state_history"]
        if h["event"] == "phase_transition"
    ]
    assert transitions == PHASES, transitions
    # Carried the parent's REAL verify findings (non-empty) + a visible rework depth.
    assert m["reworks"] == PARENT
    assert m["rework_depth"] == 1
    expected_findings = {
        k: parent_artifacts[k]
        for k in ("verification_package", "resolve_readiness", "assessment", "investigation")
        if k in parent_artifacts
    }
    assert expected_findings, "non-vacuity: the parent must have registered verify findings"
    assert m["carried_findings"] == expected_findings
    # Re-author model: no gate-level inheritance was used.
    assert m["inherits_from"] is None
    assert m["inherited_artifacts"] == {}

    # The load-bearing invariant of option B: NO verify->execute back-edge was added.
    assert phase_graph.LIFECYCLE_GRAPH["verify"] == {"resolve"}


def test_rework_closure_blocks_when_carried_finding_ignored(prod_uacp_root: Path) -> None:
    """#135 planted fault on the PRODUCTION path: a rework that drives the whole lifecycle
    but IGNORES its carried findings (authors no disposition) cannot close — closure blocks
    with RW_CARRIED_FINDING_UNADDRESSED. This is the exact defect the slice exists to stop,
    proven under the real closure sweep (not a fixture stub)."""
    root = prod_uacp_root
    fin_a = _drive_full_lifecycle(root, PARENT)
    assert fin_a.get("ok") is True, f"parent lifecycle BLOCKED: {fin_a}"
    parent_artifacts = _manifest(root, PARENT)["artifacts"]
    assert "verification_package" in parent_artifacts, parent_artifacts  # non-vacuity

    fin = _drive_rework_to_resolved(root, CHILD, PARENT, address_findings=False)
    assert fin.get("ok") is not True, f"rework closed while ignoring carried findings: {fin}"
    assert fin.get("decision") == "block", fin
    assert any("RW_CARRIED_FINDING_UNADDRESSED" in b for b in fin.get("blockers", [])), fin
    # finalize reverts its tentative stamp on a closure block: the run reached the
    # 'resolved' PHASE via the verify->resolve transition, but was NOT finalized —
    # finalized_at is reverted to None, so the run is not closed.
    assert _manifest(root, CHILD).get("finalized_at") is None, _manifest(root, CHILD)
