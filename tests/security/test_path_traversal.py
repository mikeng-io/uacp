"""Security tests for path traversal and injection prevention."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from filesystem import _resolve_uacp_path
from state import _handle_uacp_gate_ledger_append, _handle_uacp_run_registry_update


# Payloads that traverse on ALL platforms (forward-slash only)
_UNIVERSAL_TRAVERSAL = [
    "../../../etc/passwd",
    "state/runs/../../../etc/shadow",
    "./../../../etc/passwd",
    "state//..//..//etc/passwd",
]

# Payloads that only traverse on Windows (backslash as separator)
_WINDOWS_TRAVERSAL = [
    "..\\..\\windows\\system32\\config\\sam",
    "state/runs/..\\..\\tmp",
]

# All payloads that _is_safe_run_id rejects (contains /, \, or ..)
_ALL_RUN_ID_PAYLOADS = _UNIVERSAL_TRAVERSAL + _WINDOWS_TRAVERSAL


class TestPathTraversalPrevention:
    """Verify path traversal attacks are blocked at every entry point."""

    @pytest.mark.parametrize("payload", _UNIVERSAL_TRAVERSAL)
    def test_resolve_uacp_path_blocks_traversal(self, temp_uacp_root: Path, payload: str):
        with pytest.raises(ValueError):
            _resolve_uacp_path(payload, temp_uacp_root)

    @pytest.mark.skipif(sys.platform != "win32", reason="backslash is a valid filename char on POSIX")
    @pytest.mark.parametrize("payload", _WINDOWS_TRAVERSAL)
    def test_resolve_uacp_path_blocks_windows_traversal(self, temp_uacp_root: Path, payload: str):
        with pytest.raises(ValueError):
            _resolve_uacp_path(payload, temp_uacp_root)

    @pytest.mark.parametrize("run_id", _ALL_RUN_ID_PAYLOADS)
    def test_gate_ledger_append_blocks_traversal_run_id(self, temp_uacp_root: Path, run_id: str):
        import json
        result = json.loads(_handle_uacp_gate_ledger_append({
            "uacp_run_id": run_id,
            "uacp_phase": "execute",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "gate": "TEST",
            "record": {"result": "pass"},
            "authority_artifact": "plans/test.yaml",
        }))
        assert "error" in result
        assert "illegal path characters" in result["error"]

    @pytest.mark.parametrize("run_id", _ALL_RUN_ID_PAYLOADS)
    def test_run_registry_blocks_traversal_run_id(self, temp_uacp_root: Path, run_id: str):
        import json
        result = json.loads(_handle_uacp_run_registry_update({
            "uacp_run_id": run_id,
            "uacp_phase": "plan",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "op": "register",
            "entry": {
                "run_id": run_id,
                "phase": "plan",
                "write_paths": ["plans/"],
                "scope_artifact_path": "plans/test.yaml",
                "started_at": 1234567890,
            },
            "reason": "test",
            "authority_artifact": "plans/test.yaml",
        }))
        assert "error" in result


class TestNullByteAndUnicodeAttacks:
    """Verify null bytes and unusual unicode are rejected."""

    def test_null_byte_in_run_id(self, temp_uacp_root: Path):
        import json
        result = json.loads(_handle_uacp_gate_ledger_append({
            "uacp_run_id": "test\x00evil",
            "uacp_phase": "execute",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "gate": "TEST",
            "record": {"result": "pass"},
            "authority_artifact": "plans/test.yaml",
        }))
        assert "error" in result
