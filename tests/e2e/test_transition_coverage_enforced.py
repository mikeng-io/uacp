"""E2E: a dropped intent is BLOCKED on the live transition path for a governed run.

`tests/integration/test_graph_gate_activation_e2e.py` proves the D43 coverage check
binds when called directly (`validate_graph_invariants(..., "plan_exit")`). This test
closes the loop: it drives a GOVERNED entity-written run (keyed `uacp.proposal` +
PIV auto-register, so the manifest carries them) to the `plan` phase, then calls
`state_machine.handle_transition(plan -> execute)` and asserts the phase-exit
structural gate wired into handle_transition this session BLOCKS the advance when an
intent is uncovered — and lets a fully-covered run through.

This is the end-to-end chain: entity_write -> auto-register -> handle_transition's
graph gate -> GP_UNCOVERED_INTENT -> block. It is the realistic-path proof that the
coverage guarantee is enforced on the LIVE path, not just by a direct engine call.
"""

from __future__ import annotations

import json
from pathlib import Path

import state_machine
from governed_handlers import _handle_uacp_entity_write

from tests.e2e.test_full_lifecycle import seed_plan_exit_prerequisites


def _ew(root: Path, run_id: str, kind: str, fields: dict) -> dict:
    return json.loads(
        _handle_uacp_entity_write(
            {
                "workspace": str(root),
                "uacp_run_id": run_id,
                "kind": kind,
                "fields": fields,
                "reason": "t",
                "authority_artifact": "proposals/x.yaml",
                "uacp_phase": "plan",
                "policy_version": "0.1",
                "declared_side_effects": "none",
            }
        )
    )


def _proposal_fields(in_scope: list[dict]) -> dict:
    return {
        "proposal_id": "p-1",
        "phase": "propose",
        "triage_artifact": "proposals/x-triage.yaml",
        "title": "t",
        "objective": "o",
        "scope": {"in_scope": in_scope, "out_of_scope": []},
        "declared_side_effects": "none",
        "authority": {"status": "pass"},
        "human_involvement": "none",
    }


def _piv_fields(derives_from: list[str]) -> dict:
    return {
        "phase": "plan",
        "applies_to_phase": "execute",
        "phase_intent": "ship x",
        "work_units": [
            {
                "id": "wu-1",
                "intent": "do x",
                "expected_outputs": ["o"],
                "derives_from": derives_from,
            }
        ],
        "evidence_obligations": [
            {
                "id": "ev-1",
                "work_unit_id": "wu-1",
                "evidence_type": "test",
                "required": True,
                "sufficiency": "green",
            }
        ],
        "checkpoint_policy": {},
        "intent_drift_conditions": [],
        "next_phase_handoff": {},
    }


def _init(root: Path, run_id: str) -> None:
    state_machine.handle_init(
        {"workspace": str(root), "run_id": run_id, "source": "operator-request"}
    )


def _advance_to_plan(root: Path, run_id: str) -> None:
    for frm, to in [("triage", "propose"), ("propose", "plan")]:
        out = json.loads(
            state_machine.handle_transition(
                {"workspace": str(root), "run_id": run_id, "from_phase": frm, "to_phase": to}
            )
        )
        assert out.get("ok"), f"{frm}->{to}: {out}"


def _try_plan_to_execute(root: Path, run_id: str) -> dict:
    return json.loads(
        state_machine.handle_transition(
            {"workspace": str(root), "run_id": run_id, "from_phase": "plan", "to_phase": "execute"}
        )
    )


def _phase(root: Path, run_id: str) -> str:
    import yaml

    return yaml.safe_load((root / ".uacp" / "state" / "runs" / f"{run_id}.yaml").read_text())[
        "current_phase"
    ]


def test_dropped_intent_blocks_plan_to_execute(temp_uacp_root: Path):
    run_id = "uacp-cov-001"
    _init(temp_uacp_root, run_id)
    # Two declared intents; the PIV covers only si-1 -> si-2 is dropped.
    assert _ew(
        temp_uacp_root,
        run_id,
        "uacp.proposal",
        _proposal_fields(
            [{"id": "si-1", "statement": "a"}, {"id": "si-2", "statement": "b dropped"}]
        ),
    ).get("ok")
    assert _ew(
        temp_uacp_root, run_id, "uacp.phase_intent_verification_contract", _piv_fields(["si-1"])
    ).get("ok")
    _advance_to_plan(temp_uacp_root, run_id)

    out = _try_plan_to_execute(temp_uacp_root, run_id)
    assert "error" in out, f"expected dropped intent to block plan->execute, got {out}"
    assert any("GP_UNCOVERED_INTENT" in b for b in out.get("blockers", [])), out
    assert _phase(temp_uacp_root, run_id) == "plan", "blocked transition must not advance"


def test_fully_covered_run_advances(temp_uacp_root: Path):
    run_id = "uacp-cov-002"
    _init(temp_uacp_root, run_id)
    # Both intents covered -> the gate is clean and the run advances.
    assert _ew(
        temp_uacp_root,
        run_id,
        "uacp.proposal",
        _proposal_fields([{"id": "si-1", "statement": "a"}, {"id": "si-2", "statement": "b"}]),
    ).get("ok")
    assert _ew(
        temp_uacp_root,
        run_id,
        "uacp.phase_intent_verification_contract",
        _piv_fields(["si-1", "si-2"]),
    ).get("ok")
    _advance_to_plan(temp_uacp_root, run_id)

    # #99: cross the forced plan-exit gates (scope artifact + PLAN_VALIDATION + run
    # registry) faithfully; the entity-written proposal/PIV above supply the graph coverage.
    seed_plan_exit_prerequisites(temp_uacp_root, run_id)
    out = _try_plan_to_execute(temp_uacp_root, run_id)
    assert out.get("ok") is True, out
    assert _phase(temp_uacp_root, run_id) == "execute"
