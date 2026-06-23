"""CUT2 e2e — the graph gate is ACTIVE end-to-end.

A run written via the governed entity-writer (uacp_entity_write) auto-registers into the run manifest,
so the graph_projection phase-exit gate actually SEES it and fires. This proves the full activation
chain (entity_write -> register -> project -> gate) for the 5/7 checks that do not depend on the D43
scope-coverage layer (here: execute_exit checkpoint-coverage + verify_exit contradicted)."""

import json

from engines.graph_projection import validate_graph_invariants
from governed_handlers import _handle_uacp_entity_write
from state_machine import handle_init


def _init(root, run_id="uacp-act-001"):
    handle_init({"workspace": str(root), "run_id": run_id, "source": "operator-request"})
    return run_id


def _ew(root, run_id, kind, fields, **ctx):
    args = {
        "workspace": str(root),
        "uacp_run_id": run_id,
        "kind": kind,
        "fields": fields,
        "reason": "t",
        "authority_artifact": "proposals/x.yaml",
    }
    if ctx:
        args["ctx"] = ctx
    return json.loads(_handle_uacp_entity_write(args))


def _piv_fields():
    return {
        "phase": "plan",
        "applies_to_phase": "execute",
        "phase_intent": "ship x",
        "work_units": [{"id": "wu-1", "intent": "do x", "expected_outputs": ["o"]}],
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


def _cp_fields(result="pass"):
    return {
        "phase": "execute",
        "checkpoint_id": "cp-1",
        "piv_contract": "plans/uacp-act-001-piv.yaml",
        "checkpoint_type": "after_work_unit",
        "work_unit_id": "wu-1",
        "work_performed": "did x",
        "decisions": [],
        "evidence": [{"obligation_id": "ev-1", "result": result, "summary": "green"}],
        "intent_drift": {},
        "invariants": [],
        "next_phase_readiness": "ready",
    }


def test_entity_written_piv_activates_execute_gate(tmp_path):
    # A PIV written via the governed entity-writer auto-registers, so the gate SEES it: wu-1 has an
    # obligation but no checkpoint yet -> execute_exit FIRES (the gate is no longer a dormant no-op).
    run_id = _init(tmp_path)
    res = _ew(tmp_path, run_id, "uacp.phase_intent_verification_contract", _piv_fields())
    assert res.get("ok") is True, res
    codes = {v.code for v in validate_graph_invariants(tmp_path, run_id, "execute_exit")}
    assert "GP_WORK_UNIT_NO_CHECKPOINT" in codes, codes


def test_entity_written_run_passes_execute_gate_with_checkpoint(tmp_path):
    # Non-vacuity: add the checkpoint (also entity-written) -> execute_exit clean.
    run_id = _init(tmp_path)
    _ew(tmp_path, run_id, "uacp.phase_intent_verification_contract", _piv_fields())
    res = _ew(tmp_path, run_id, "uacp.execution_checkpoint", _cp_fields(), seq="1")
    assert res.get("ok") is True, res
    codes = {v.code for v in validate_graph_invariants(tmp_path, run_id, "execute_exit")}
    assert "GP_WORK_UNIT_NO_CHECKPOINT" not in codes, codes
