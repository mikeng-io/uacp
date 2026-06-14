"""E2E: a full run threaded through real Guardian/Heartgate/state machine/writers.

Drives a single run INIT -> (per phase: gate-ledger append + Heartgate-validated
transition) -> FINALIZE using the real kernel components, then asserts on the
emitted trajectory (run manifest state_history/status/finalized_at + gate-ledger
line count) rather than on file paths or config contents, so the test survives a
later config refactor.
"""
from __future__ import annotations

from pathlib import Path

import yaml

import state_machine
from core import Heartgate
from state import _handle_uacp_gate_ledger_append
from tests.e2e.driver import Driver

PHASES = [
    ("triage", "propose"),
    ("propose", "plan"),
    ("plan", "execute"),
    ("execute", "verify"),
    ("verify", "resolved"),
]

# universal_core concerns the kernel's always-on package gates enforce. We mark
# each "not_applicable" with full justification so no per-key artifact file is
# needed — the gate still verifies the package envelope exists and is coherent.
_PROPOSAL_CORE = [
    "intent", "authority", "scope", "containment",
    "risk", "verification", "transition", "artifact_map",
]
_PLAN_CORE = [
    "work_breakdown", "dependencies", "authority_and_side_effects",
    "tool_runtime_selection", "artifact_write_surfaces", "verification_strategy",
    "rollback_recovery", "council_review_topology", "transition_readiness",
]


def _na_block(*, with_trigger: bool = False) -> dict:
    block = {
        "status": "not_applicable",
        "reason": "trivial e2e run; concern not material",
        "accepted_by": "e2e-harness",
        "owner": "e2e-harness",
        "residual_risk": "none",
        "revisit_phase": "resolved",
    }
    if with_trigger:
        block["revisit_trigger"] = "scope expands beyond harness"
    return block


def _seed_proposal_package(root: Path, run_id: str) -> None:
    """Create the proposal package + selection the propose->plan gate requires."""
    pkg_dir = root / "proposals" / run_id
    pkg_dir.mkdir(parents=True, exist_ok=True)
    module_artifact = f"proposals/{run_id}/module-core.yaml"
    (root / module_artifact).write_text("kind: uacp.proposal_module\nbody: stub\n")
    selection = {
        "kind": "uacp.proposal_package_selection",
        "run_id": run_id,
        "universal_core": {key: _na_block() for key in _PROPOSAL_CORE},
        "selected_modules": {
            "core": {"reason": "minimal e2e module", "artifact": module_artifact},
        },
    }
    (root / "proposals" / f"{run_id}-package-selection.yaml").write_text(
        yaml.safe_dump(selection, sort_keys=False)
    )


def _seed_plan_package(root: Path, run_id: str) -> None:
    """Create the plan package + selection + scope the plan->execute gate requires."""
    pkg_dir = root / "plans" / run_id
    pkg_dir.mkdir(parents=True, exist_ok=True)
    module_artifact = f"plans/{run_id}/module-core.yaml"
    (root / module_artifact).write_text("kind: uacp.plan_module\nbody: stub\n")
    (root / "plans" / f"{run_id}-scope.yaml").write_text(
        "kind: uacp.scope\nwrite_paths: []\nbody: stub\n"
    )
    # The run_registry_rule fires on plan->execute and warns when the registry
    # is absent. Seed it (empty active set) so this is a clean pass, not a warn.
    (root / "state" / "run-registry.yaml").write_text(
        yaml.safe_dump({"active_runs": []}, sort_keys=False)
    )
    selection = {
        "kind": "uacp.plan_package_selection",
        "phase": "plan",
        "run_id": run_id,
        "universal_core": {key: _na_block(with_trigger=True) for key in _PLAN_CORE},
        "selected_modules": {
            "core": {"reason": "minimal e2e module", "artifact": module_artifact},
        },
        "transition_readiness": {"status": "ready_for_execute"},
    }
    (root / "plans" / f"{run_id}-plan-selection.yaml").write_text(
        yaml.safe_dump(selection, sort_keys=False)
    )


# Per-(from,to) real-evidence seeding the kernel's adaptive gates REQUIRE — not
# optional. The propose->plan and plan->execute gates read config via
# `self.config.get(key) or {}`: an absent key becomes `{}`, still a Mapping, so
# the gate fires and demands its artifacts regardless of config. Drop these
# seeders and the happy path fails (e.g. "adaptive_proposal_package_gate: missing
# proposals/<run>-package-selection.yaml"). By contrast the execute/verify/resolve
# gates guard with `if not isinstance(self.config.get(key), Mapping): return`, so
# they self-disable on absent config — hence nothing is seeded for them.
_SEEDERS = {
    ("propose", "plan"): _seed_proposal_package,
    ("plan", "execute"): _seed_plan_package,
}


def test_full_lifecycle_reaches_resolved(temp_uacp_root: Path, valid_run_id: str):
    d = Driver(temp_uacp_root, valid_run_id)
    heartgate = Heartgate.load(str(temp_uacp_root))

    init = d.call(
        "uacp_state_write",
        lambda a: state_machine.handle_init(a),
        {
            "workspace": str(temp_uacp_root),
            "run_id": valid_run_id,
            "source": "operator-request",
        },
        phase="triage",
    )
    assert init.get("ok") is True, init

    for frm, to in PHASES:
        ledger = d.call(
            "uacp_gate_ledger_append",
            _handle_uacp_gate_ledger_append,
            {
                "uacp_run_id": valid_run_id,
                "uacp_phase": frm,
                "workspace": str(temp_uacp_root),
                "policy_version": "0.1",
                "declared_side_effects": [],
                "gate": f"{frm.upper()}->{to.upper()}",
                "record": {"result": "pass"},
                "authority_artifact": "plans/test.yaml",
            },
            phase=frm,
        )
        assert ledger.get("ok") is True, ledger

        # Seed the evidence artifacts the kernel's always-on adaptive gates
        # require for this transition (real evidence, not a loosened assertion).
        if seeder := _SEEDERS.get((frm, to)):
            seeder(temp_uacp_root, valid_run_id)

        hg = heartgate.validate_transition(
            {
                "from_phase": frm,
                "to_phase": to,
                "run_id": valid_run_id,
                "artifact_path": "plans/test.yaml",
            }
        )
        assert hg.decision == "pass", f"Heartgate blocked legit {frm}->{to}: {hg.blockers}"

        tr = d.call(
            "uacp_state_write",
            lambda a: state_machine.handle_transition(a),
            {
                "workspace": str(temp_uacp_root),
                "run_id": valid_run_id,
                "from_phase": frm,
                "to_phase": to,
            },
            phase=frm,
        )
        assert tr.get("ok") is True, tr

    fin = d.call(
        "uacp_state_write",
        lambda a: state_machine.handle_finalize(a),
        {"workspace": str(temp_uacp_root), "run_id": valid_run_id},
        phase="verify",
    )
    assert fin.get("ok") is True and fin["status"] == "resolved", fin

    # Assert on the emitted TRAJECTORY, not file paths / config contents.
    manifest = yaml.safe_load(
        (temp_uacp_root / "state" / "runs" / f"{valid_run_id}.yaml").read_text()
    )
    assert manifest["status"] == "resolved"
    assert manifest["current_phase"] == "resolved"
    assert manifest["finalized_at"] is not None
    transitions = [h for h in manifest["state_history"] if h["event"] == "phase_transition"]
    assert [(h["from_phase"], h["to_phase"]) for h in transitions] == PHASES

    ledger_lines = (
        (temp_uacp_root / "state" / "gate-ledger" / f"{valid_run_id}.jsonl")
        .read_text()
        .strip()
        .split("\n")
    )
    assert len(ledger_lines) == len(PHASES)
