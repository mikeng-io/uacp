"""Unit tests for uacp-state mutation handlers."""

from __future__ import annotations

import json
from pathlib import Path


from state import (
    _handle_uacp_gate_ledger_append,
    _handle_uacp_run_finalize,
    _handle_uacp_run_init,
    _handle_uacp_run_register_artifact,
    _handle_uacp_run_registry_update,
    _handle_uacp_run_transition,
    _handle_uacp_state_write,
)


class TestGateLedgerAppend:
    """Tests for _handle_uacp_gate_ledger_append"""

    def test_appends_record(self, temp_uacp_root: Path, valid_run_id: str):
        result = json.loads(_handle_uacp_gate_ledger_append({
            "uacp_run_id": valid_run_id,
            "uacp_phase": "execute",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "gate": "EXECUTE->VERIFY",
            "record": {"result": "pass", "check": "ppv_1"},
            "authority_artifact": "plans/test-plan.yaml",
        }))
        assert result["ok"] is True
        assert result["gate"] == "EXECUTE->VERIFY"
        assert result["run_id"] == valid_run_id

        # Verify file was created and contains the record
        ledger_path = temp_uacp_root / ".uacp" / "state" / "gate-ledger" / f"{valid_run_id}.jsonl"
        assert ledger_path.exists()
        lines = ledger_path.read_text().strip().split("\n")
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["gate"] == "EXECUTE->VERIFY"
        assert record["result"] == "pass"

    def test_rejects_missing_gate(self, temp_uacp_root: Path, valid_run_id: str):
        result = json.loads(_handle_uacp_gate_ledger_append({
            "uacp_run_id": valid_run_id,
            "uacp_phase": "execute",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "record": {"result": "pass"},
            "authority_artifact": "plans/test-plan.yaml",
        }))
        assert "error" in result
        assert "gate is required" in result["error"]

    def test_rejects_path_traversal_in_run_id(self, temp_uacp_root: Path):
        result = json.loads(_handle_uacp_gate_ledger_append({
            "uacp_run_id": "../../../etc/passwd",
            "uacp_phase": "execute",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "gate": "TEST",
            "record": {"result": "pass"},
            "authority_artifact": "plans/test-plan.yaml",
        }))
        assert "error" in result
        assert "illegal path characters" in result["error"]

    def test_enforces_pipe_buf_limit(self, temp_uacp_root: Path, valid_run_id: str):
        huge_record = {"data": "x" * 4000}
        result = json.loads(_handle_uacp_gate_ledger_append({
            "uacp_run_id": valid_run_id,
            "uacp_phase": "execute",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "gate": "TEST",
            "record": huge_record,
            "authority_artifact": "plans/test-plan.yaml",
        }))
        assert "error" in result
        assert "3584-byte ledger limit" in result["error"]


class TestRunRegistryUpdate:
    """Tests for _handle_uacp_run_registry_update"""

    def test_registers_run(self, temp_uacp_root: Path, valid_run_id: str):
        result = json.loads(_handle_uacp_run_registry_update({
            "uacp_run_id": valid_run_id,
            "uacp_phase": "plan",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "op": "register",
            "entry": {
                "run_id": valid_run_id,
                "phase": "plan",
                "write_paths": ["plans/"],
                "scope_artifact_path": "plans/test-scope.yaml",
                "started_at": 1234567890,
            },
            "reason": "test registration",
            "authority_artifact": "plans/test-plan.yaml",
        }))
        assert result["ok"] is True
        assert result["op"] == "register"
        assert result["run_id"] == valid_run_id

    def test_rejects_foreign_run_id(self, temp_uacp_root: Path):
        result = json.loads(_handle_uacp_run_registry_update({
            "uacp_run_id": "uacp-caller-001",
            "uacp_phase": "plan",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "op": "register",
            "entry": {
                "run_id": "uacp-foreign-002",  # Different from caller
                "phase": "plan",
                "write_paths": ["plans/"],
                "scope_artifact_path": "plans/test-scope.yaml",
                "started_at": 1234567890,
            },
            "reason": "test registration",
            "authority_artifact": "plans/test-plan.yaml",
        }))
        assert "error" in result
        assert "registry mutations must be caller-owned" in result["error"]

    def test_rejects_empty_write_paths(self, temp_uacp_root: Path, valid_run_id: str):
        result = json.loads(_handle_uacp_run_registry_update({
            "uacp_run_id": valid_run_id,
            "uacp_phase": "plan",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "op": "register",
            "entry": {
                "run_id": valid_run_id,
                "phase": "plan",
                "write_paths": [],
                "scope_artifact_path": "plans/test-scope.yaml",
                "started_at": 1234567890,
            },
            "reason": "test registration",
            "authority_artifact": "plans/test-plan.yaml",
        }))
        assert "error" in result
        assert "empty write_paths requires explicit entry.no_writes_intended=true" in result["error"]


class TestStateWrite:
    """Tests for _handle_uacp_state_write"""

    def test_writes_state_file(self, temp_uacp_root: Path, valid_run_id: str):
        result = json.loads(_handle_uacp_state_write({
            "uacp_run_id": valid_run_id,
            "uacp_phase": "plan",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "target_path": "state/test-file.yaml",
            "content": "hello: world",
            "reason": "test write",
            "authority_artifact": "plans/test-plan.yaml",
        }))
        assert result["ok"] is True
        assert (temp_uacp_root / ".uacp" / "state" / "test-file.yaml").read_text() == "hello: world"

    def test_rejects_write_outside_state(self, temp_uacp_root: Path, valid_run_id: str):
        result = json.loads(_handle_uacp_state_write({
            "uacp_run_id": valid_run_id,
            "uacp_phase": "plan",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "target_path": "docs/INDEX.md",
            "content": "hacked",
            "reason": "test write",
            "authority_artifact": "plans/test-plan.yaml",
        }))
        assert "error" in result
        assert "may only write under state/" in result["error"]

    def test_rejects_direct_gate_ledger_write(self, temp_uacp_root: Path, valid_run_id: str):
        result = json.loads(_handle_uacp_state_write({
            "uacp_run_id": valid_run_id,
            "uacp_phase": "plan",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "target_path": "state/gate-ledger/test.jsonl",
            "content": "fake record",
            "reason": "test write",
            "authority_artifact": "plans/test-plan.yaml",
        }))
        assert "error" in result
        assert "use uacp_gate_ledger_append" in result["error"]


# ---------------------------------------------------------------------------
# New governed lifecycle tool handlers
# ---------------------------------------------------------------------------

_CTX = {
    "uacp_phase": "triage",
    "policy_version": "0.1",
    "declared_side_effects": [],
}


def _init_args(workspace: str, run_id: str, **extra) -> dict:
    return {
        "workspace": workspace,
        "uacp_run_id": run_id,
        "source": "operator-request",
        "reason": "start a governed run",
        "authority_artifact": "proposals/test-proposal.yaml",
        **_CTX,
        **extra,
    }


class TestRunInit:
    """Tests for _handle_uacp_run_init."""

    def test_creates_run_manifest(self, temp_uacp_root: Path, valid_run_id: str):
        result = json.loads(_handle_uacp_run_init(_init_args(str(temp_uacp_root), valid_run_id)))
        assert result.get("ok") is True
        assert result["run_id"] == valid_run_id
        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / f"{valid_run_id}.yaml"
        assert manifest_path.exists(), "manifest file was not created"

    def test_rejects_missing_reason(self, temp_uacp_root: Path, valid_run_id: str):
        args = _init_args(str(temp_uacp_root), valid_run_id)
        del args["reason"]
        result = json.loads(_handle_uacp_run_init(args))
        assert "error" in result
        assert "reason is required" in result["error"]

    def test_rejects_missing_authority(self, temp_uacp_root: Path, valid_run_id: str):
        args = _init_args(str(temp_uacp_root), valid_run_id)
        del args["authority_artifact"]
        result = json.loads(_handle_uacp_run_init(args))
        assert "error" in result
        assert "authority_artifact is required" in result["error"]

    def test_rejects_missing_uacp_context(self, temp_uacp_root: Path, valid_run_id: str):
        # Missing uacp_phase triggers context guard
        args = _init_args(str(temp_uacp_root), valid_run_id)
        del args["uacp_phase"]
        result = json.loads(_handle_uacp_run_init(args))
        assert "error" in result
        assert "missing UACP context" in result["error"]

    def test_duplicate_run_is_rejected(self, temp_uacp_root: Path, valid_run_id: str):
        # First call succeeds
        first = json.loads(_handle_uacp_run_init(_init_args(str(temp_uacp_root), valid_run_id)))
        assert first.get("ok") is True
        # Second call with same run_id must fail
        second = json.loads(_handle_uacp_run_init(_init_args(str(temp_uacp_root), valid_run_id)))
        assert "error" in second
        assert "already exists" in second["error"]


class TestRunTransition:
    """Tests for _handle_uacp_run_transition."""

    def _transition_args(self, workspace: str, run_id: str, from_phase: str, to_phase: str) -> dict:
        return {
            "workspace": workspace,
            "uacp_run_id": run_id,
            "from_phase": from_phase,
            "to_phase": to_phase,
            "reason": "phase complete",
            "authority_artifact": "proposals/test-proposal.yaml",
            **_CTX,
        }

    def test_transitions_run(self, temp_uacp_root: Path, valid_run_id: str):
        # Seed a run manifest first (via handle_init delegate)
        _handle_uacp_run_init(_init_args(str(temp_uacp_root), valid_run_id))
        result = json.loads(
            _handle_uacp_run_transition(
                self._transition_args(str(temp_uacp_root), valid_run_id, "triage", "propose")
            )
        )
        assert result.get("ok") is True
        assert result["from_phase"] == "triage"
        assert result["to_phase"] == "propose"

    def test_rejects_missing_reason(self, temp_uacp_root: Path, valid_run_id: str):
        _handle_uacp_run_init(_init_args(str(temp_uacp_root), valid_run_id))
        args = self._transition_args(str(temp_uacp_root), valid_run_id, "triage", "propose")
        del args["reason"]
        result = json.loads(_handle_uacp_run_transition(args))
        assert "error" in result
        assert "reason is required" in result["error"]

    def test_rejects_missing_from_phase(self, temp_uacp_root: Path, valid_run_id: str):
        _handle_uacp_run_init(_init_args(str(temp_uacp_root), valid_run_id))
        args = self._transition_args(str(temp_uacp_root), valid_run_id, "triage", "propose")
        del args["from_phase"]
        result = json.loads(_handle_uacp_run_transition(args))
        assert "error" in result
        assert "from_phase is required" in result["error"]

    def test_rejects_wrong_current_phase(self, temp_uacp_root: Path, valid_run_id: str):
        _handle_uacp_run_init(_init_args(str(temp_uacp_root), valid_run_id))
        # Run is in triage; claiming it's in propose must fail
        result = json.loads(
            _handle_uacp_run_transition(
                self._transition_args(str(temp_uacp_root), valid_run_id, "propose", "plan")
            )
        )
        assert "error" in result
        assert "transition refused" in result["error"]


class TestRunRegisterArtifact:
    """Tests for _handle_uacp_run_register_artifact."""

    def _reg_args(self, workspace: str, run_id: str, artifact_type: str, path: str) -> dict:
        return {
            "workspace": workspace,
            "uacp_run_id": run_id,
            "artifact_type": artifact_type,
            "path": path,
            "reason": "register triage artifact",
            "authority_artifact": "proposals/test-proposal.yaml",
            **_CTX,
        }

    def test_registers_artifact(self, temp_uacp_root: Path, valid_run_id: str):
        _handle_uacp_run_init(_init_args(str(temp_uacp_root), valid_run_id))
        result = json.loads(
            _handle_uacp_run_register_artifact(
                self._reg_args(str(temp_uacp_root), valid_run_id, "triage", "state/runs/triage-001.yaml")
            )
        )
        assert result.get("ok") is True
        assert result["artifact_type"] == "triage"

    def test_rejects_missing_artifact_type(self, temp_uacp_root: Path, valid_run_id: str):
        _handle_uacp_run_init(_init_args(str(temp_uacp_root), valid_run_id))
        args = self._reg_args(str(temp_uacp_root), valid_run_id, "", "state/runs/triage-001.yaml")
        result = json.loads(_handle_uacp_run_register_artifact(args))
        assert "error" in result
        assert "artifact_type is required" in result["error"]

    def test_rejects_missing_authority(self, temp_uacp_root: Path, valid_run_id: str):
        _handle_uacp_run_init(_init_args(str(temp_uacp_root), valid_run_id))
        args = self._reg_args(str(temp_uacp_root), valid_run_id, "triage", "state/runs/t.yaml")
        del args["authority_artifact"]
        result = json.loads(_handle_uacp_run_register_artifact(args))
        assert "error" in result
        assert "authority_artifact is required" in result["error"]


class TestRunFinalize:
    """Tests for _handle_uacp_run_finalize."""

    def _finalize_args(self, workspace: str, run_id: str) -> dict:
        return {
            "workspace": workspace,
            "uacp_run_id": run_id,
            "reason": "run complete",
            "authority_artifact": "resolutions/test-res.yaml",
            **_CTX,
        }

    def test_rejects_missing_reason(self, temp_uacp_root: Path, valid_run_id: str):
        args = self._finalize_args(str(temp_uacp_root), valid_run_id)
        del args["reason"]
        result = json.loads(_handle_uacp_run_finalize(args))
        assert "error" in result
        assert "reason is required" in result["error"]

    def test_rejects_missing_authority(self, temp_uacp_root: Path, valid_run_id: str):
        args = self._finalize_args(str(temp_uacp_root), valid_run_id)
        del args["authority_artifact"]
        result = json.loads(_handle_uacp_run_finalize(args))
        assert "error" in result
        assert "authority_artifact is required" in result["error"]

    def test_rejects_missing_uacp_context(self, temp_uacp_root: Path, valid_run_id: str):
        args = self._finalize_args(str(temp_uacp_root), valid_run_id)
        del args["policy_version"]
        result = json.loads(_handle_uacp_run_finalize(args))
        assert "error" in result
        assert "missing UACP context" in result["error"]

    def test_rejects_non_terminal_phase(self, temp_uacp_root: Path, valid_run_id: str):
        # Seed a manifest in triage (not terminal)
        _handle_uacp_run_init(_init_args(str(temp_uacp_root), valid_run_id))
        result = json.loads(_handle_uacp_run_finalize(self._finalize_args(str(temp_uacp_root), valid_run_id)))
        assert "error" in result
        assert "finalize" in result["error"].lower()


class TestRunLifecycleSequence:
    """Integration: init → transition → register_artifact through governed handlers."""

    def test_init_then_transition_then_register(self, temp_uacp_root: Path, valid_run_id: str):
        ws = str(temp_uacp_root)
        ctx = {
            "uacp_phase": "triage",
            "policy_version": "0.1",
            "declared_side_effects": [],
            "reason": "governed op",
            "authority_artifact": "proposals/test-proposal.yaml",
        }

        # 1. init
        r = json.loads(_handle_uacp_run_init({
            "workspace": ws, "uacp_run_id": valid_run_id, "source": "test", **ctx,
        }))
        assert r.get("ok") is True, f"init failed: {r}"

        # 2. transition triage -> propose
        r = json.loads(_handle_uacp_run_transition({
            "workspace": ws, "uacp_run_id": valid_run_id,
            "from_phase": "triage", "to_phase": "propose", **ctx,
        }))
        assert r.get("ok") is True, f"transition failed: {r}"

        # 3. register a proposal artifact
        r = json.loads(_handle_uacp_run_register_artifact({
            "workspace": ws, "uacp_run_id": valid_run_id,
            "artifact_type": "proposal", "path": "proposals/test.yaml", **ctx,
        }))
        assert r.get("ok") is True, f"register_artifact failed: {r}"
        assert r["artifact_type"] == "proposal"
