"""Unit tests for the in-EXECUTE checkpoint manifest (goal-driven track, Task 4).

Covers:
  * CheckpointEntry Pydantic model (shape + verdict enum + required fields).
  * Heartgate._validate_checkpoint_entry — the structural claim=>evidence
    (no-self-attestation) check: a checkpoint's `evidence` must reference a
    real artifact contained under the governed root.
  * _handle_uacp_gate_ledger_append accepts gate: "CHECKPOINT" via the EXISTING
    governed ledger writer, while a direct uacp_state_write under
    state/gate-ledger/ remains REFUSED.

Scope boundary (Task 6 does the wiring): the validation method is exercised in
ISOLATION here; it is NOT yet wired into validate_transition.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core import Heartgate
from engines.domain import CheckpointEntry
from state import _handle_uacp_gate_ledger_append, _handle_uacp_state_write


def _checkpoint(**overrides):
    base = {
        "checkpoint_id": "ckpt-001",
        "run_id": "uacp-test-001",
        "goal_id": "goal-001",
        "phase": "execute",
        "what_changed": "drafted hero copy variant B",
        "why": "variant A failed the punchiness invariant",
        "evidence": "executions/uacp-test-001/ckpt-001.md",
        "verdict": "keep",
        "invariant": "hero must read in <3s",
    }
    base.update(overrides)
    return base


def _seed_artifact(root: Path, rel: str, body: str = "real artifact\n") -> None:
    """Write a real artifact under the governed root (.uacp/)."""
    path = root / ".uacp" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


# ---------------------------------------------------------------------------
# (d) model: invalid verdict / missing required field is rejected
# ---------------------------------------------------------------------------


class TestCheckpointEntryModel:
    def test_valid_entry_parses(self):
        entry = CheckpointEntry(**_checkpoint())
        assert entry.verdict == "keep"
        assert entry.rolled_back_to is None

    def test_roll_back_records_target(self):
        entry = CheckpointEntry(**_checkpoint(verdict="roll_back", rolled_back_to="ckpt-000"))
        assert entry.verdict == "roll_back"
        assert entry.rolled_back_to == "ckpt-000"

    def test_invalid_verdict_rejected(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CheckpointEntry(**_checkpoint(verdict="ship_it"))

    def test_missing_required_field_rejected(self):
        from pydantic import ValidationError

        bad = _checkpoint()
        del bad["evidence"]
        with pytest.raises(ValidationError):
            CheckpointEntry(**bad)


# ---------------------------------------------------------------------------
# (a/b/c) Heartgate._validate_checkpoint_entry — structural claim=>evidence
# ---------------------------------------------------------------------------


class TestValidateCheckpointEntry:
    def test_real_artifact_evidence_passes(self, temp_uacp_root: Path):
        # (a) evidence -> EXISTING artifact under governed root => NO blocker.
        _seed_artifact(temp_uacp_root, "executions/uacp-test-001/ckpt-001.md")
        hg = Heartgate.load(temp_uacp_root)
        entry = CheckpointEntry(**_checkpoint())
        blockers: list[str] = []
        hg._validate_checkpoint_entry(entry, blockers)
        assert blockers == []

    def test_prose_evidence_blocked(self, temp_uacp_root: Path):
        # (b) evidence is a prose sentence (no such artifact) => BLOCKED.
        hg = Heartgate.load(temp_uacp_root)
        entry = CheckpointEntry(**_checkpoint(evidence="I checked it and it looks great."))
        blockers: list[str] = []
        hg._validate_checkpoint_entry(entry, blockers)
        assert blockers
        assert any("evidence" in b.lower() for b in blockers)

    def test_missing_artifact_evidence_blocked(self, temp_uacp_root: Path):
        # (b) evidence path that does not exist => BLOCKED.
        hg = Heartgate.load(temp_uacp_root)
        entry = CheckpointEntry(**_checkpoint(evidence="executions/uacp-test-001/nope.md"))
        blockers: list[str] = []
        hg._validate_checkpoint_entry(entry, blockers)
        assert blockers
        assert any("not found" in b.lower() or "evidence" in b.lower() for b in blockers)

    def test_escaping_evidence_blocked(self, temp_uacp_root: Path):
        # (c) evidence escapes the governed root => BLOCKED (containment).
        hg = Heartgate.load(temp_uacp_root)
        entry = CheckpointEntry(**_checkpoint(evidence="../../etc/passwd"))
        blockers: list[str] = []
        hg._validate_checkpoint_entry(entry, blockers)
        assert blockers
        assert any("evidence" in b.lower() for b in blockers)

    def test_empty_evidence_blocked(self, temp_uacp_root: Path):
        hg = Heartgate.load(temp_uacp_root)
        # bypass the model so we exercise the validator's own empty-guard
        entry = CheckpointEntry(**_checkpoint())
        object.__setattr__(entry, "evidence", "")
        blockers: list[str] = []
        hg._validate_checkpoint_entry(entry, blockers)
        assert blockers


# ---------------------------------------------------------------------------
# (e) governed writer accepts gate: "CHECKPOINT"; direct state write refused
# ---------------------------------------------------------------------------


class TestCheckpointLedgerWriter:
    def test_gate_ledger_accepts_checkpoint_record(self, temp_uacp_root: Path, valid_run_id: str):
        _seed_artifact(temp_uacp_root, f"executions/{valid_run_id}/ckpt-001.md")
        record = _checkpoint(run_id=valid_run_id, evidence=f"executions/{valid_run_id}/ckpt-001.md")
        result = json.loads(_handle_uacp_gate_ledger_append({
            "uacp_run_id": valid_run_id,
            "uacp_phase": "execute",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "gate": "CHECKPOINT",
            "record": record,
            "authority_artifact": "plans/test-plan.yaml",
        }))
        assert result["ok"] is True
        assert result["gate"] == "CHECKPOINT"

        ledger_path = temp_uacp_root / ".uacp" / "state" / "gate-ledger" / f"{valid_run_id}.jsonl"
        assert ledger_path.exists()
        rec = json.loads(ledger_path.read_text().strip().splitlines()[-1])
        assert rec["gate"] == "CHECKPOINT"
        assert rec["verdict"] == "keep"

    def test_direct_state_write_under_gate_ledger_refused(self, temp_uacp_root: Path, valid_run_id: str):
        # The gate-ledger direct-write refusal must still hold — a CHECKPOINT
        # cannot be forged via uacp_state_write.
        result = json.loads(_handle_uacp_state_write({
            "target_path": f"state/gate-ledger/{valid_run_id}.jsonl",
            "content": json.dumps(_checkpoint()) + "\n",
            "reason": "trying to forge a checkpoint",
            "authority_artifact": "plans/test-plan.yaml",
            "uacp_run_id": valid_run_id,
            "uacp_phase": "execute",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
        }))
        assert "error" in result
        assert "gate-ledger" in result["error"]
        assert "uacp_gate_ledger_append" in result["error"]
