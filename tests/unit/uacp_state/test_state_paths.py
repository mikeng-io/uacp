"""Containment tests: governed writers must resolve under .uacp/state/.

Slice 2 relocates the UACP runtime namespace beneath ``<root>/.uacp``. The
governed writers still receive base-relative ``target_path`` strings (e.g.
``state/runs/r1.yaml``) but must resolve and containment-check them under
``base_dir(root)`` so the bytes land under ``.uacp/state/`` and never under a
flat top-level ``state/``.
"""

from __future__ import annotations

import json
from pathlib import Path

import state as state_mod


def _common_ctx(root: Path, run_id: str) -> dict:
    return {
        "uacp_run_id": run_id,
        "uacp_phase": "plan",
        "workspace": str(root),
        "policy_version": "0.1",
        "declared_side_effects": [],
        "authority_artifact": "plans/test-plan.yaml",
    }


def _seed_root(tmp_path: Path) -> None:
    """Mirror the conftest .uacp/ + config/ layout for a bare tmp_path root."""
    (tmp_path / ".uacp" / "state" / "runs").mkdir(parents=True)
    (tmp_path / ".uacp" / "state" / "gate-ledger").mkdir(parents=True)
    (tmp_path / ".uacp" / "state" / "escalations").mkdir(parents=True)
    (tmp_path / "config").mkdir(parents=True)
    (tmp_path / "config" / "guardian-policy.yaml").write_text(
        """
schema_version: "0.1"
protected_categories:
  state.uacp:
    allowed_tools:
      - uacp_state_write
      - uacp_gate_ledger_append
      - uacp_run_registry_update
      - uacp_escalation_event
tool_classification:
  uacp_state_write: state.uacp
self_attesting_tools:
  names:
    - uacp_state_write
"""
    )


def test_state_write_lands_under_uacp(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("UACP_ROOT", str(tmp_path))
    _seed_root(tmp_path)
    args = {
        **_common_ctx(tmp_path, "uacp-test-001"),
        "target_path": "state/runs/r1.yaml",
        "content": "run_id: r1\n",
        "reason": "containment test",
    }
    out = json.loads(state_mod._handle_uacp_state_write(args))
    assert out.get("ok") is True, out
    # C-1: lands under .uacp/state, NOT flat state/.
    assert (tmp_path / ".uacp" / "state" / "runs" / "r1.yaml").exists()
    assert not (tmp_path / "state" / "runs" / "r1.yaml").exists()
    # Response path stays base-relative (not prefixed with .uacp/).
    assert out.get("path") == "state/runs/r1.yaml"


def test_gate_ledger_append_lands_under_uacp(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("UACP_ROOT", str(tmp_path))
    _seed_root(tmp_path)
    args = {
        **_common_ctx(tmp_path, "uacp-test-001"),
        "gate": "EXECUTE->VERIFY",
        "record": {"result": "pass"},
        "reason": "containment test",
    }
    out = json.loads(state_mod._handle_uacp_gate_ledger_append(args))
    assert out.get("ok") is True, out
    assert (tmp_path / ".uacp" / "state" / "gate-ledger" / "uacp-test-001.jsonl").exists()
    assert not (tmp_path / "state" / "gate-ledger" / "uacp-test-001.jsonl").exists()
    assert out.get("path") == "state/gate-ledger/uacp-test-001.jsonl"


def test_run_registry_update_lands_under_uacp(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("UACP_ROOT", str(tmp_path))
    _seed_root(tmp_path)
    args = {
        **_common_ctx(tmp_path, "uacp-test-001"),
        "op": "register",
        "entry": {
            "run_id": "uacp-test-001",
            "phase": "plan",
            "write_paths": ["plans/"],
            "scope_artifact_path": "plans/test-scope.yaml",
            "started_at": 1234567890,
        },
        "reason": "containment test",
    }
    out = json.loads(state_mod._handle_uacp_run_registry_update(args))
    assert out.get("ok") is True, out
    assert (tmp_path / ".uacp" / "state" / "run-registry.yaml").exists()
    assert not (tmp_path / "state" / "run-registry.yaml").exists()


def test_escalation_event_lands_under_uacp(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("UACP_ROOT", str(tmp_path))
    _seed_root(tmp_path)
    args = {
        **_common_ctx(tmp_path, "uacp-test-001"),
        "trigger": "policy_block",
        "severity": "warn",
        "mode": "manual",
        "reason": "containment test",
    }
    out = json.loads(state_mod._handle_uacp_escalation_event(args))
    assert out.get("ok") is True, out
    assert (tmp_path / ".uacp" / "state" / "escalations" / "uacp-test-001.jsonl").exists()
    assert not (tmp_path / "state" / "escalations" / "uacp-test-001.jsonl").exists()
    assert out.get("path") == "state/escalations/uacp-test-001.jsonl"
