"""KEYSTONE E2E: the standard lifecycle must stay drivable end-to-end through
UACP's own governed tools under PRODUCTION gate defaults.

Why this module exists (the bug class it forecloses): the rest of the suite runs
against ``tests/conftest.py``'s ``temp_uacp_root`` fixture, whose synthetic
``config/phase-transitions.yaml`` ships an explicit ``stages`` block with NO
``phase_exit_invariants``. That wholesale-overrides ``stages_default()`` and thereby
HIDES every ``phase_exit_invariants``-driven closure obligation — so CI stays green
on fixture config while a real (production-config) run deadlocks at finalize
(BREAK-1: the ``resolve`` vs ``resolved`` vocabulary contradiction between
``evidence_completeness`` and ``coherence`` C2).

This test deliberately BYPASSES that override for THIS MODULE ONLY: its
``prod_uacp_root`` fixture builds a sandbox whose ``config/`` is the *production*
config tree (``config/phase-transitions.yaml`` with NO ``stages`` block), so
``engines.io.load_phase_transitions`` injects ``stages_default()`` — the real
production ``phase_exit_invariants``. Everything else mirrors ``temp_uacp_root``
(governed ``.uacp/`` layout, cwd, ``UACP_ROOT``, teardown).

It drives the FULL standard lifecycle TRIAGE->PROPOSE->PLAN->EXECUTE->VERIFY->
RESOLVED->finalize through the REAL governed handler functions (the byte-equivalent
of the MCP transport), producing every artifact via the correct governed writers
(invariant #3), and asserts:
  * every governed transition succeeds;
  * ``uacp_run_finalize`` returns a passing/warn closure (never ``block``);
  * the ledger the run PRODUCED satisfies BOTH ``evidence_completeness`` AND
    ``coherence`` with zero block-severity violations.

It is the permanent guarantee that the lifecycle stays drivable through its own
tools — the "green-on-fixture / deadlocked-in-production" class is structurally
impossible while this test is green.
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
from engines.manifest.entity_writer import create_entity
from state import _handle_uacp_gate_ledger_append

from tests.e2e.driver import Driver
from tests.e2e.test_adaptive_evidence_gate_uacp import REAL_CONFIG, REAL_VALIDATOR
from tests.e2e.test_full_lifecycle import (
    _SEEDERS,
    PHASES,
)

RUN_ID = "uacp-prod-drive-001"


@pytest.fixture
def prod_uacp_root() -> Generator[Path]:
    """A sandbox UACP_ROOT wired with the PRODUCTION config tree.

    Identical to ``conftest.temp_uacp_root`` in every respect EXCEPT the
    ``config/`` directory: instead of the fixture's opt-out ``stages`` stub, it
    copies the real repo ``config/`` verbatim. Because production
    ``config/phase-transitions.yaml`` ships NO ``stages`` block,
    ``load_phase_transitions`` injects ``stages_default()`` — activating the
    production ``phase_exit_invariants`` the fixture suppresses. This is the
    deliberate, documented per-module bypass of the conftest override.
    """
    test_dir = Path(tempfile.mkdtemp(prefix="uacp-proddrive-"))
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
    # PRODUCTION config tree (no stages block -> stages_default applies).
    shutil.copytree(REAL_CONFIG, test_dir / "config")
    # The in-process offline validator (execute->verify forced gate) loads
    # <root>/scripts/validate_uacp_artifacts.py.
    (test_dir / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(REAL_VALIDATOR, test_dir / "scripts" / "validate_uacp_artifacts.py")

    os.chdir(test_dir)
    old_uacp_root = os.environ.get("UACP_ROOT")
    os.environ["UACP_ROOT"] = str(test_dir)
    try:
        yield test_dir
    finally:
        if old_uacp_root is None:
            os.environ.pop("UACP_ROOT", None)
        else:
            os.environ["UACP_ROOT"] = old_uacp_root
        os.chdir(original_cwd)
        shutil.rmtree(test_dir, ignore_errors=True)


# The gate-ledger entries the PRODUCTION closure sweep requires per completed
# phase (stages_default phase_exit_invariants -> evidence_completeness) PLUS the
# FROM->TO transition gate coherence C2 pairs 1:1 with each state_history edge.
# Keyed by the from_phase of the edge being crossed.
_REQUIRED_LEDGER_GATES: dict[str, list[str]] = {
    "triage": ["TRIAGE_COMPLETE", "TRIAGE->PROPOSE"],
    "propose": ["PROPOSE->PLAN"],
    "plan": ["PLAN->EXECUTE"],
    "execute": ["EXECUTE->VERIFY"],
    # The GOVERNED transition records verify->resolved (state_machine projection),
    # so the resolve-exit ledger gate MUST be VERIFY->RESOLVED (BREAK-1 fix F1).
    "verify": ["VERIFY->RESOLVED"],
}


def _append_ledger(driver: Driver, root: Path, run_id: str, phase: str, gate: str) -> None:
    out = driver.call(
        "uacp_gate_ledger_append",
        _handle_uacp_gate_ledger_append,
        {
            "uacp_run_id": run_id,
            "uacp_phase": phase,
            "workspace": str(root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "gate": gate,
            "record": {"result": "pass"},
            "authority_artifact": "plans/test.yaml",
        },
        phase=phase,
    )
    assert out.get("ok") is True, out


def _seed_triage_artifact(root: Path, run_id: str) -> None:
    """Produce proposals/{run_id}-triage.yaml via the GOVERNED entity writer so the
    TRIAGE phase-exit artifact invariant (proposals/{run_id}-triage*.yaml) is met."""
    out = create_entity(
        str(root),
        run_id,
        "uacp.triage",
        {
            "triage_id": f"{run_id}-triage",
            "request_summary": "Keystone production-drivability lifecycle run.",
            "authority": {"source": "operator-request", "status": "pass"},
            "factor_scores": {"blast_radius": 1, "reversibility": 1},
            "granularity_level": 1,
            "routing_outcome": "standard",
            "track": "standard",
            "next_step": "propose",
        },
    )
    assert out.get("ok") is True, out


def _author_lessons(root: Path, run_id: str) -> None:
    out = create_entity(
        str(root),
        run_id,
        "uacp.lessons",
        {
            "lessons": [
                {
                    "id": "L1",
                    "category": "process",
                    "finding": "Production-config lifecycle run reaches resolved.",
                    "recommendation": "None.",
                    "applies_to_future_runs": False,
                }
            ],
        },
    )
    assert out.get("ok") is True, out


def _watermark_registered_artifacts(root: Path, run_id: str) -> None:
    """Stamp a governed watermark for every manifest-registered artifact.

    The reused ``test_full_lifecycle`` seeders predate the entity writer and emit
    their gate-satisfying files with raw ``write_text`` (no watermark). Once ANY
    governed writer runs (our triage/lessons ``create_entity`` calls), the run is
    in the governed-writer regime and ``artifact_integrity`` requires EVERY
    registered artifact to carry a watermark (AI_UNRECORDED otherwise). Recording
    their hashes here makes the run a faithful fully-governed run — the state a
    real agent using ``uacp_entity_write`` throughout would leave behind.
    """
    from engines.domain.artifact_hashes import record_hash

    base = root / ".uacp"
    manifest = yaml.safe_load((base / "state" / "runs" / f"{run_id}.yaml").read_text())
    for rel in (manifest.get("artifacts") or {}).values():
        fpath = base / rel
        if fpath.is_file():
            record_hash(str(root), run_id, str(rel), fpath.read_text(encoding="utf-8"))


def _drive_full_lifecycle(root: Path, run_id: str) -> dict:
    """Drive the standard lifecycle to finalize via GOVERNED handlers only.

    Returns the finalize response dict. Never calls heartgate.validate_transition
    (the agent path uses the lifecycle graph, which rejects verify->resolved) —
    exactly the governed sequence the diagnosis proved works up to finalize.
    """
    driver = Driver(root, run_id)

    init = driver.call(
        "uacp_state_write",
        lambda a: state_machine.handle_init(a),
        {"workspace": str(root), "run_id": run_id, "source": "operator-request"},
        phase="triage",
    )
    assert init.get("ok") is True, init

    _seed_triage_artifact(root, run_id)

    for frm, to in PHASES:
        for gate in _REQUIRED_LEDGER_GATES.get(frm, []):
            _append_ledger(driver, root, run_id, frm, gate)

        if seeder := _SEEDERS.get((frm, to)):
            seeder(root, run_id)

        tr = driver.call(
            "uacp_state_write",
            lambda a: state_machine.handle_transition(a),
            {"workspace": str(root), "run_id": run_id, "from_phase": frm, "to_phase": to},
            phase=frm,
        )
        assert tr.get("ok") is True, f"governed transition {frm}->{to} blocked: {tr}"

    _author_lessons(root, run_id)
    _watermark_registered_artifacts(root, run_id)

    fin = driver.call(
        "uacp_state_write",
        lambda a: state_machine.handle_finalize(a),
        {"workspace": str(root), "run_id": run_id},
        phase="verify",
    )
    return fin


def test_production_lifecycle_finalizes_and_is_coherent(prod_uacp_root: Path) -> None:
    root, run_id = prod_uacp_root, RUN_ID

    fin = _drive_full_lifecycle(root, run_id)

    # 1) Finalize must SUCCEED with a non-block closure (pass or warn) — this is
    #    the exact call that BREAK-1 deadlocked before F1.
    assert fin.get("ok") is True, f"finalize BLOCKED (BREAK-1 regression): {fin}"
    assert fin.get("status") == "resolved", fin
    assert fin.get("closure") in {"pass", "warn"}, fin

    # 2) The manifest reached the terminal state via the full standard path.
    manifest = yaml.safe_load((root / ".uacp" / "state" / "runs" / f"{run_id}.yaml").read_text())
    assert manifest["status"] == "resolved"
    assert manifest["current_phase"] == "resolved"
    assert manifest["finalized_at"] is not None
    transitions = [
        (h["from_phase"], h["to_phase"])
        for h in manifest["state_history"]
        if h["event"] == "phase_transition"
    ]
    assert transitions == PHASES, transitions

    # 3) The ledger the run PRODUCED must satisfy BOTH closure engines with zero
    #    block-severity violations — the permanent guarantee that the two engines
    #    agree on the resolve edge (no VERIFY->RESOLVE vs VERIFY->RESOLVED schism).
    from engines.coherence import validate_run_coherence
    from engines.evidence_completeness import validate_evidence_completeness

    ev = validate_evidence_completeness(str(root), run_id)
    ev_blocks = [f"{v.code}: {v.message}" for v in ev if v.severity == "block"]
    assert not ev_blocks, f"evidence_completeness blocked a driven run: {ev_blocks}"

    coh = validate_run_coherence(str(root), run_id)
    coh_blocks = [f"{v.code}: {v.message}" for v in coh if v.severity == "block"]
    assert not coh_blocks, f"coherence blocked a driven run: {coh_blocks}"
