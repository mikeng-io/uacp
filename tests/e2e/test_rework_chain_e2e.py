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
from state import _handle_uacp_run_register_artifact

from tests.e2e.driver import Driver
from tests.e2e.test_adaptive_evidence_gate_uacp import REAL_CONFIG, REAL_VALIDATOR
from tests.e2e.test_full_lifecycle import _SEEDERS, PHASES
from tests.e2e.test_lifecycle_production_drivability import (
    _author_lessons,
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


def _seed_parent_with_finding(root: Path, run_id: str) -> None:
    """Parent run A that reached VERIFY and recorded a verification finding (the
    defect the rework exists to fix)."""
    driver = Driver(root, run_id)
    init = driver.call(
        "uacp_state_write",
        state_machine.handle_init,
        {"workspace": str(root), "run_id": run_id, "source": "operator-request"},
        phase="triage",
    )
    assert init.get("ok") is True, init
    # Register A's verification finding (governed) so the rework can carry it forward.
    finding_rel = f"verification/{run_id}-package.yaml"
    (root / ".uacp" / "verification").mkdir(parents=True, exist_ok=True)
    (root / ".uacp" / finding_rel).write_text(
        yaml.safe_dump({"kind": "uacp.verification_package", "run_id": run_id, "verdict": "fail"})
    )
    reg = driver.call(
        "uacp_run_register_artifact",
        _handle_uacp_run_register_artifact,
        {
            "uacp_run_id": run_id,
            "uacp_phase": "verify",
            "workspace": str(root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "reason": "record verify finding",
            "authority_artifact": "plans/test.yaml",
            "artifact_type": "verification",
            "path": finding_rel,
        },
        phase="verify",
    )
    assert reg.get("ok") is True, reg


def _drive_rework_to_resolved(root: Path, run_id: str, reworks: str) -> dict:
    """Drive a REWORK run through the full standard lifecycle via governed handlers.

    Identical to the keystone's _drive_full_lifecycle EXCEPT the run is initialized
    with `reworks=<parent>` — the rework re-authors its own upstream and drives
    forward normally.
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
    _watermark_registered_artifacts(root, run_id)
    return driver.call(
        "uacp_state_write",
        state_machine.handle_finalize,
        {"workspace": str(root), "run_id": run_id},
        phase="verify",
    )


def test_rework_run_drives_forward_to_resolved_carrying_findings(prod_uacp_root: Path) -> None:
    root = prod_uacp_root

    # Parent A reached VERIFY and recorded a finding.
    _seed_parent_with_finding(root, PARENT)

    # Rework run B reworks A: carries A's finding + a visible depth, re-authors its own
    # upstream, and drives the full lifecycle forward to RESOLVED.
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
    # Carried the parent's finding + a visible rework depth (the #109 metadata).
    assert m["reworks"] == PARENT
    assert m["rework_depth"] == 1
    assert m["carried_findings"] == {"verification": f"verification/{PARENT}-package.yaml"}
    # Re-author model: no gate-level inheritance was used.
    assert m["inherits_from"] is None
    assert m["inherited_artifacts"] == {}

    # The load-bearing invariant of option B: NO verify->execute back-edge was added.
    assert phase_graph.LIFECYCLE_GRAPH["verify"] == {"resolve"}
