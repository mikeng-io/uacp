"""Unit tests for uacp-state mutation handlers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from state import (
    _handle_uacp_gate_ledger_append,
    _handle_uacp_run_registry_update,
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
            "record": {"result": "pass", "check": "piv_1"},
            "authority_artifact": "plans/test-plan.yaml",
        }))
        assert result["ok"] is True
        assert result["gate"] == "EXECUTE->VERIFY"
        assert result["run_id"] == valid_run_id

        # Verify file was created and contains the record
        ledger_path = temp_uacp_root / "state" / "gate-ledger" / f"{valid_run_id}.jsonl"
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
        assert (temp_uacp_root / "state" / "test-file.yaml").read_text() == "hello: world"

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
