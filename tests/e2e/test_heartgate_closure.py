"""E2E tests for Heartgate.validate_closure — the RESOLVE / closure gate that
runs the five computed engines (coherence, ledger_integrity, scope_conformance,
evidence_completeness, deferral_completeness) and maps their violations onto a
HeartgateDecision.

The positive test drives a genuinely complete, finalized, compliant run (reusing
``seed_coherent_run`` from test_coherence.py) and asserts validate_closure
returns "pass" — and proves the pass is NON-VACUOUS by asserting the run really
carries the manifest / ledger / scope / registry / lessons the engines inspect.

Each "teeth" test starts from that good run, corrupts EXACTLY one thing, and
asserts validate_closure returns "block" with the expected engine code in the
blockers — while the good run did NOT block. We cover >=3 engines (coherence,
ledger_integrity, evidence_completeness). A dedup test proves the SC/C6
scope-vs-registry write_paths overlap collapses to ONE blocker. A defensive test
proves validate_closure returns a decision (never raises) on a missing run.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from core import Heartgate

from tests.e2e.test_coherence import (
    _load_manifest_raw,
    _write_manifest_raw,
    seed_coherent_run,
)


def _closure(root: Path, run_id: str):
    return Heartgate.load(str(root)).validate_closure(run_id)


def _blocker_codes(decision) -> list[str]:
    """Engine codes carried in a decision's blockers (lines are 'CODE: message')."""
    return [b.split(":", 1)[0].strip() for b in decision.blockers]


# ---------------------------------------------------------------- positive test
def test_compliant_finalized_run_passes_closure(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)

    # --- non-vacuity: the run really carries the artifacts/ledger/state the
    #     engines inspect, so "pass" is a real pass, not "nothing to check".
    manifest = _load_manifest_raw(temp_uacp_root, valid_run_id)
    assert manifest["run_id"] == valid_run_id
    assert manifest["status"] == "resolved"
    assert manifest.get("finalized_at"), "engines' terminal checks need a finalized run"
    assert manifest.get("state_history"), "ledger_integrity/coherence need phase history"
    assert (temp_uacp_root / ".uacp" / "state" / "gate-ledger" / f"{valid_run_id}.jsonl").exists()
    assert (temp_uacp_root / ".uacp" / "plans" / f"{valid_run_id}-scope.yaml").exists()
    assert (temp_uacp_root / ".uacp" / "resolutions" / f"{valid_run_id}-lessons.yaml").exists()
    assert (temp_uacp_root / ".uacp" / "state" / "run-registry.yaml").exists()

    decision = _closure(temp_uacp_root, valid_run_id)
    assert decision.decision == "pass", (
        f"expected pass, got {decision.decision}; blockers={decision.blockers}; "
        f"warnings={decision.warnings}"
    )
    assert decision.blockers == []
    assert isinstance(decision, type(Heartgate.load(str(temp_uacp_root)).validate_transition({})))


# ---------------------------------------------------- teeth 1: coherence (C1)
def test_manifest_run_id_mismatch_blocks_with_c1(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    assert _closure(temp_uacp_root, valid_run_id).decision == "pass"

    data = _load_manifest_raw(temp_uacp_root, valid_run_id)
    data["run_id"] = "uacp-test-IMPOSTER"
    _write_manifest_raw(temp_uacp_root, valid_run_id, data)

    decision = _closure(temp_uacp_root, valid_run_id)
    assert decision.decision == "block", decision.warnings
    assert "C1_RUN_ID_MISMATCH" in _blocker_codes(decision), decision.blockers


# ------------------------------------------- teeth 2: evidence_completeness (EV)
def _add_plan_exit_invariant(root: Path) -> None:
    """Declare a required plan-phase exit invariant in the run's workspace config.

    The bundled test config has no phase_exit_invariants, so evidence_completeness
    has nothing to enforce. We add a real, required invariant (the plan phase must
    leave a 'plans/{run_id}-plan-selection.yaml' artifact) so the engine has teeth
    — this is exactly the "invariant-declaring config" the EV engine consumes.
    """
    cfg_path = root / "config" / "phase-transitions.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    cfg["stages"]["plan"]["phase_exit_invariants"] = [
        {"artifact_glob": "plans/{run_id}-plan-selection.yaml", "required": True}
    ]
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))


def test_missing_phase_exit_artifact_blocks_with_ev(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _add_plan_exit_invariant(temp_uacp_root)
    # With the required plan-exit artifact present, closure is still clean.
    assert (temp_uacp_root / ".uacp" / "plans" / f"{valid_run_id}-plan-selection.yaml").exists()
    assert _closure(temp_uacp_root, valid_run_id).decision == "pass"

    # Remove ONLY the required plan-phase exit artifact (leave scope etc. intact so
    # no other engine fires). evidence_completeness must report a missing exit
    # artifact for the completed 'plan' phase.
    (temp_uacp_root / ".uacp" / "plans" / f"{valid_run_id}-plan-selection.yaml").unlink()

    decision = _closure(temp_uacp_root, valid_run_id)
    assert decision.decision == "block", decision.warnings
    assert "EV_PHASE_EXIT_ARTIFACT_MISSING" in _blocker_codes(decision), decision.blockers


# ----------------------------------------------- teeth 3: ledger_integrity (LI)
def test_non_monotonic_ledger_ts_blocks_with_li(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    assert _closure(temp_uacp_root, valid_run_id).decision == "pass"

    # Rewrite the gate ledger so timestamps go backwards (non-monotonic ts).
    ledger_path = temp_uacp_root / ".uacp" / "state" / "gate-ledger" / f"{valid_run_id}.jsonl"
    lines = ledger_path.read_text().strip().splitlines()
    records = [json.loads(line) for line in lines]
    assert len(records) >= 2, "need >=2 ledger records to make ts non-monotonic"
    # Stamp strictly decreasing timestamps: first high, rest lower.
    for i, rec in enumerate(records):
        rec["ts"] = 1000 - i * 10
    ledger_path.write_text("\n".join(json.dumps(r) for r in records) + "\n")

    decision = _closure(temp_uacp_root, valid_run_id)
    assert decision.decision == "block", decision.warnings
    assert "LI_TIMESTAMP_NON_MONOTONIC" in _blocker_codes(decision), decision.blockers


# ------------------------------------------------------- dedup test (SC vs C6)
def test_scope_registry_disagreement_collapses_to_one_blocker(
    temp_uacp_root: Path, valid_run_id: str
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    assert _closure(temp_uacp_root, valid_run_id).decision == "pass"

    # Make scope.write_paths disagree with the run-registry write_paths. Both the
    # coherence engine (C6_WRITE_PATHS_DISAGREE) and the scope_conformance engine
    # (SC_SCOPE_REGISTRY_DISAGREE) detect this same divergence. validate_closure
    # must collapse them to ONE operator-facing write_paths blocker (prefer C6).
    scope_path = temp_uacp_root / ".uacp" / "plans" / f"{valid_run_id}-scope.yaml"
    body = yaml.safe_load(scope_path.read_text())
    body["write_paths"] = ["docs/something-else/"]
    scope_path.write_text(yaml.safe_dump(body, sort_keys=False))

    decision = _closure(temp_uacp_root, valid_run_id)
    assert decision.decision == "block", decision.warnings
    codes = _blocker_codes(decision)
    assert "C6_WRITE_PATHS_DISAGREE" in codes, codes
    # The overlapping SC write_paths finding must have been collapsed away.
    sc_writepath_blockers = [
        b
        for b in decision.blockers
        if b.startswith("SC_SCOPE_REGISTRY_DISAGREE") and "write_paths" in b
    ]
    assert sc_writepath_blockers == [], (
        f"expected the SC write_paths finding to be deduped into C6, got: "
        f"{sc_writepath_blockers}"
    )
    # And exactly ONE write_paths blocker total for the one problem.
    write_path_blockers = [b for b in decision.blockers if "write_paths" in b]
    assert len(write_path_blockers) == 1, write_path_blockers


# --------------------------------------------------- defensive: never raises
def test_validate_closure_never_raises_on_missing_run(temp_uacp_root: Path):
    decision = _closure(temp_uacp_root, "no-such-run")
    # A decision, not an exception. A missing run has no coherent state, so the
    # engines surface block-severity violations -> decision is "block" (or "warn").
    assert decision.decision in {"block", "warn"}, decision
    assert isinstance(
        decision, type(Heartgate.load(str(temp_uacp_root)).validate_transition({}))
    )
