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


def test_after_work_unit_with_block_evidence_does_not_count(temp_uacp_root):
    # Review concern #1: an after_work_unit checkpoint whose evidence records a
    # `block` result is EXECUTE's own admission the unit did not complete -> the
    # gate must NOT count it as coverage, so the transition blocks.
    _write(temp_uacp_root, "plans/run-blk-piv.yaml",
           _piv("run-blk", [{"id": "wu-1", "intent": "x", "expected_outputs": ["y"]}]))
    cp = _checkpoint("run-blk", "after_work_unit", "wu-1")
    cp["evidence"] = [{"obligation_id": "ev-1", "result": "block", "summary": "blocked"}]
    _write(temp_uacp_root, "executions/run-blk-checkpoint-001.yaml", cp)
    blockers = _hg(temp_uacp_root).forced_execute_evidence_blockers("run-blk")
    assert any("wu-1" in b for b in blockers), blockers


def test_after_work_unit_with_warn_evidence_counts(temp_uacp_root):
    # Non-vacuity counterpart: warn/deferred are acceptable — only `block`
    # disqualifies. A unit with a warn result still counts as executed -> passes.
    _write(temp_uacp_root, "plans/run-warn-piv.yaml",
           _piv("run-warn", [{"id": "wu-1", "intent": "x", "expected_outputs": ["y"]}]))
    cp = _checkpoint("run-warn", "after_work_unit", "wu-1")
    cp["evidence"] = [{"obligation_id": "ev-1", "result": "warn", "summary": "minor"}]
    _write(temp_uacp_root, "executions/run-warn-checkpoint-001.yaml", cp)
    assert _hg(temp_uacp_root).forced_execute_evidence_blockers("run-warn") == []


def test_required_null_is_fail_closed(temp_uacp_root):
    # Review concern #2: `required: null` (and any non-False value) must be
    # treated as required, not silently optional. Unit is unexecuted -> blocks.
    _write(temp_uacp_root, "plans/run-null-piv.yaml",
           _piv("run-null", [
               {"id": "wu-1", "intent": "x", "expected_outputs": ["y"], "required": None},
           ]))
    _write(temp_uacp_root, "executions/run-null-checkpoint-001.yaml",
           _checkpoint("run-null", "before_side_effect", "wu-1"))
    blockers = _hg(temp_uacp_root).forced_execute_evidence_blockers("run-null")
    assert any("wu-1" in b for b in blockers), blockers


def test_required_explicit_true_blocks(temp_uacp_root):
    _write(temp_uacp_root, "plans/run-true-piv.yaml",
           _piv("run-true", [
               {"id": "wu-1", "intent": "x", "expected_outputs": ["y"], "required": True},
           ]))
    _write(temp_uacp_root, "executions/run-true-checkpoint-001.yaml",
           _checkpoint("run-true", "before_side_effect", "wu-1"))
    blockers = _hg(temp_uacp_root).forced_execute_evidence_blockers("run-true")
    assert any("wu-1" in b for b in blockers), blockers


def test_required_unit_missing_id_blocks(temp_uacp_root):
    # Review concern #3: a required work_unit with no id is a malformed PIV and
    # must BLOCK, not be silently skipped.
    _write(temp_uacp_root, "plans/run-noid-piv.yaml",
           _piv("run-noid", [{"intent": "x", "expected_outputs": ["y"]}]))
    _write(temp_uacp_root, "executions/run-noid-checkpoint-001.yaml",
           _checkpoint("run-noid", "before_side_effect"))
    blockers = _hg(temp_uacp_root).forced_execute_evidence_blockers("run-noid")
    assert blockers, "a required work_unit with no id must block"
