"""Work-unit status coverage gate at EXECUTE->VERIFY.

`forced_execute_evidence_blockers` derives per-work_unit completion from
`after_work_unit` checkpoints: a standard-track run whose PIV declares
work_units must have an `after_work_unit` checkpoint for each REQUIRED unit
before EXECUTE->VERIFY. This is the re-derivable coverage signal (no separate
status file) — an interrupted agent reconstructs progress from the same
checkpoints the gate reads.

Design: design/work-unit-status/.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from core import Heartgate


def _hg(root: Path) -> Heartgate:
    return Heartgate({}, uacp_root=root)


def _write(root: Path, rel: str, data: dict) -> None:
    p = root / ".uacp" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.dump(data), encoding="utf-8")


def _piv(run_id: str, work_units: list[dict]) -> dict:
    return {
        "kind": "uacp.phase_intent_verification_contract",
        "run_id": run_id,
        "phase": "plan",
        "applies_to_phase": "execute",
        "work_units": work_units,
    }


def _checkpoint(run_id: str, checkpoint_type: str, work_unit_id: str | None = None) -> dict:
    d = {
        "kind": "uacp.execution_checkpoint",
        "run_id": run_id,
        "checkpoint_type": checkpoint_type,
    }
    if work_unit_id:
        d["work_unit_id"] = work_unit_id
    return d


def test_no_checkpoint_no_block(temp_uacp_root):
    # Bare/ungoverned EXECUTE->VERIFY (no checkpoint marker) -> no ripple.
    assert _hg(temp_uacp_root).forced_execute_evidence_blockers("run-bare") == []


def test_all_executed_passes(temp_uacp_root):
    _write(temp_uacp_root, "plans/run-pass-piv.yaml",
           _piv("run-pass", [{"id": "wu-1", "intent": "x", "expected_outputs": ["y"]}]))
    _write(temp_uacp_root, "executions/run-pass-checkpoint-001.yaml",
           _checkpoint("run-pass", "after_work_unit", "wu-1"))
    assert _hg(temp_uacp_root).forced_execute_evidence_blockers("run-pass") == []


def test_missing_after_work_unit_blocks(temp_uacp_root):
    # A non-after_work_unit checkpoint exists (governed marker) but the unit was
    # never completed -> block.
    _write(temp_uacp_root, "plans/run-b-piv.yaml",
           _piv("run-b", [{"id": "wu-1", "intent": "x", "expected_outputs": ["y"]}]))
    _write(temp_uacp_root, "executions/run-b-checkpoint-001.yaml",
           _checkpoint("run-b", "before_side_effect", "wu-1"))
    blockers = _hg(temp_uacp_root).forced_execute_evidence_blockers("run-b")
    assert any("wu-1" in b for b in blockers), blockers


def test_optional_unit_not_blocking(temp_uacp_root):
    _write(temp_uacp_root, "plans/run-opt-piv.yaml",
           _piv("run-opt", [
               {"id": "wu-opt", "intent": "x", "expected_outputs": ["y"], "required": False},
           ]))
    _write(temp_uacp_root, "executions/run-opt-checkpoint-001.yaml",
           _checkpoint("run-opt", "before_side_effect", "wu-opt"))
    assert _hg(temp_uacp_root).forced_execute_evidence_blockers("run-opt") == []


def test_piv_no_work_units_no_block(temp_uacp_root):
    # PIV present but no work_units list -> derivation skipped, no regression.
    _write(temp_uacp_root, "plans/run-nw-piv.yaml", {
        "kind": "uacp.phase_intent_verification_contract",
        "run_id": "run-nw", "phase": "plan", "applies_to_phase": "execute",
    })
    _write(temp_uacp_root, "executions/run-nw-checkpoint-001.yaml",
           _checkpoint("run-nw", "deviation"))
    assert _hg(temp_uacp_root).forced_execute_evidence_blockers("run-nw") == []


def test_partial_execution_blocks_only_incomplete(temp_uacp_root):
    # Two units; only wu-a completed. Block names wu-b, not wu-a.
    _write(temp_uacp_root, "plans/run-p-piv.yaml",
           _piv("run-p", [
               {"id": "wu-a", "intent": "a", "expected_outputs": ["x"]},
               {"id": "wu-b", "intent": "b", "expected_outputs": ["y"]},
           ]))
    _write(temp_uacp_root, "executions/run-p-checkpoint-001.yaml",
           _checkpoint("run-p", "after_work_unit", "wu-a"))
    blockers = _hg(temp_uacp_root).forced_execute_evidence_blockers("run-p")
    assert any("wu-b" in b for b in blockers), blockers
    assert not any("'wu-a'" in b for b in blockers), blockers
