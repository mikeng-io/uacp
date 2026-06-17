"""Tests for the deterministic run-state source."""
from __future__ import annotations

from pathlib import Path

import yaml

from engines.oracle.sources.runstate import query_runstate
from engines.oracle.packets import TrustClass


def _write_manifest(root: Path, run_id: str, data: dict) -> None:
    runs_dir = root / ".uacp" / "state" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / f"{run_id}.yaml").write_text(yaml.dump(data))


def test_returns_empty_when_no_runs(temp_uacp_root):
    packets = query_runstate(temp_uacp_root, project="myproject")
    assert packets == []


def test_returns_authoritative_packets_for_matching_project(temp_uacp_root):
    _write_manifest(temp_uacp_root, "run-001", {
        "project": "myproject",
        "phase": "plan",
        "status": "active",
    })
    packets = query_runstate(temp_uacp_root, project="myproject")
    assert len(packets) == 1
    assert packets[0].trust_class == TrustClass.authoritative
    assert packets[0].source == "runstate"
    assert packets[0].evidence_required is False


def test_filters_by_project(temp_uacp_root):
    _write_manifest(temp_uacp_root, "run-001", {"project": "projectA", "phase": "plan", "status": "active"})
    _write_manifest(temp_uacp_root, "run-002", {"project": "projectB", "phase": "plan", "status": "active"})
    packets = query_runstate(temp_uacp_root, project="projectA")
    assert len(packets) == 1
    assert packets[0].payload["run_id"] == "run-001"


def test_filters_by_phase(temp_uacp_root):
    _write_manifest(temp_uacp_root, "run-001", {"project": "proj", "phase": "plan", "status": "active"})
    _write_manifest(temp_uacp_root, "run-002", {"project": "proj", "phase": "execute", "status": "active"})
    packets = query_runstate(temp_uacp_root, project="proj", phase="plan")
    assert len(packets) == 1
    assert packets[0].payload["phase"] == "plan"


def test_respects_limit(temp_uacp_root):
    for i in range(5):
        _write_manifest(temp_uacp_root, f"run-{i:03d}", {"project": "proj", "phase": "plan", "status": "active"})
    packets = query_runstate(temp_uacp_root, project="proj", limit=3)
    assert len(packets) == 3


def test_garbled_manifest_is_skipped_gracefully(temp_uacp_root):
    runs_dir = temp_uacp_root / ".uacp" / "state" / "runs"
    (runs_dir / "bad-run.yaml").write_text("{{{{not valid yaml")
    _write_manifest(temp_uacp_root, "run-good", {"project": "proj", "phase": "plan", "status": "active"})
    packets = query_runstate(temp_uacp_root, project="proj")
    assert len(packets) == 1
    assert packets[0].payload["run_id"] == "run-good"
