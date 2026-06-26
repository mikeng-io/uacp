"""Integration: interrupt + resume across the wu-status coverage gate.

An agent executes wu-a, is interrupted, a fresh agent resumes by reading the
same checkpoints the gate reads, completes wu-b, and the gate then passes.
This proves the re-derivable design: no separate status file is needed to
know what to resume.

Design: design/work-unit-status/.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from core import Heartgate


def _write(root: Path, rel: str, data: dict) -> None:
    p = root / ".uacp" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.dump(data), encoding="utf-8")


def test_interrupt_then_resume(temp_uacp_root):
    run_id = "run-resume"
    _write(temp_uacp_root, f"plans/{run_id}-piv.yaml", {
        "kind": "uacp.phase_intent_verification_contract",
        "run_id": run_id, "phase": "plan", "applies_to_phase": "execute",
        "work_units": [
            {"id": "wu-a", "intent": "first task", "expected_outputs": ["a.py"]},
            {"id": "wu-b", "intent": "second task", "expected_outputs": ["b.py"]},
        ],
    })

    # Agent completes wu-a, then is interrupted before wu-b.
    _write(temp_uacp_root, f"executions/{run_id}-checkpoint-001.yaml", {
        "kind": "uacp.execution_checkpoint", "run_id": run_id,
        "checkpoint_type": "after_work_unit", "work_unit_id": "wu-a",
    })

    hg = Heartgate({}, uacp_root=temp_uacp_root)

    # Gate blocks: wu-b not yet done; wu-a is not named.
    blockers = hg.forced_execute_evidence_blockers(run_id)
    assert any("wu-b" in b for b in blockers), blockers
    assert not any("'wu-a'" in b for b in blockers), blockers

    # Resumed agent completes wu-b.
    _write(temp_uacp_root, f"executions/{run_id}-checkpoint-002.yaml", {
        "kind": "uacp.execution_checkpoint", "run_id": run_id,
        "checkpoint_type": "after_work_unit", "work_unit_id": "wu-b",
    })

    # Gate passes.
    assert hg.forced_execute_evidence_blockers(run_id) == []
