"""TDD tests for Task 3: goal-anchored run chaining.

UACP's goal-driven track realizes "roll back to a checkpoint" as launching a
NEW forward run under the same persistent goal, reusing the prior run's phase
output (design: docs/architecture/0016-goal-driven-track.md, P2=option-b).

This module pins the chaining MECHANISM only:
  - a run can be launched under an existing goal, inheriting a prior run's
    declared phase-artifact references;
  - the run-chain is queryable by goal_id;
  - standard runs (no goal_id) are entirely unaffected;
  - the registry writer's caller-binding survives the goal_id addition.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from state import _handle_uacp_run_registry_update
from state_machine import (
    Authority,
    RunManifest,
    handle_init,
    list_runs_for_goal,
)


def _seed_parent_with_artifacts(workspace: Path, run_id: str) -> RunManifest:
    """Create a parent run manifest with some registered phase artifacts and
    mutable execution state we expect NOT to be inherited."""
    manifest = RunManifest(
        run_id=run_id,
        authority=Authority(source="operator-request"),
        track="goal-driven",
        goal_id="g1",
        current_phase="plan",
        artifacts={
            "triage": "knowledge/run-A-triage.md",
            "proposal": "proposals/run-A.md",
            "plan": "plans/run-A.yaml",
        },
    )
    # Mutable execution state that MUST NOT cross the chain boundary.
    from state_machine import StateHistoryEntry, _save_manifest

    manifest.state_history.append(
        StateHistoryEntry(event="phase_transition", from_phase="triage", to_phase="propose")
    )
    _save_manifest(workspace, manifest)
    return manifest


class TestInheritOnInit:
    """(a) inherit-on-init: a new run under an existing goal reuses the parent's
    declared phase-artifact references."""

    def test_inherits_prior_phase_artifacts(self, temp_uacp_root: Path):
        _seed_parent_with_artifacts(temp_uacp_root, "run-A")

        result = json.loads(handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "run-B",
            "source": "operator-request",
            "track": "goal-driven",
            "goal_id": "g1",
            "inherits_from": "run-A",
        }))
        assert result["ok"] is True

        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / "run-B.yaml"
        data = yaml.safe_load(manifest_path.read_text())
        assert data["goal_id"] == "g1"
        assert data["inherits_from"] == "run-A"
        # Reused phase-output references copied from run-A's artifacts map.
        assert data["inherited_artifacts"] == {
            "triage": "knowledge/run-A-triage.md",
            "proposal": "proposals/run-A.md",
            "plan": "plans/run-A.yaml",
        }
        # Mutable execution state is NOT inherited.
        assert data["state_history"] == []
        assert data["artifacts"] == {}

    def test_missing_parent_fails_closed(self, temp_uacp_root: Path):
        result = json.loads(handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "run-B",
            "source": "operator-request",
            "track": "goal-driven",
            "goal_id": "g1",
            "inherits_from": "run-does-not-exist",
        }))
        assert "error" in result
        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / "run-B.yaml"
        assert not manifest_path.exists()


class TestChainQueryableByGoal:
    """(b) chain queryable by goal: the registry can hold multiple active
    entries sharing a goal_id; given a goal_id you can list its runs."""

    def _register(self, workspace: Path, run_id: str, goal_id: str | None) -> dict:
        entry = {
            "run_id": run_id,
            "phase": "execute",
            "write_paths": ["src/x.py"],
            "scope_artifact_path": f"plans/{run_id}-scope.yaml",
            "started_at": 1,
        }
        if goal_id is not None:
            entry["goal_id"] = goal_id
        return json.loads(_handle_uacp_run_registry_update({
            "workspace": str(workspace),
            "uacp_run_id": run_id,
            "uacp_phase": "execute",
            "policy_version": "0.1",
            "declared_side_effects": [],
            "op": "register",
            "entry": entry,
            "reason": "register run",
            "authority_artifact": f"plans/{run_id}-scope.yaml",
        }))

    def test_lists_runs_sharing_goal(self, temp_uacp_root: Path):
        assert self._register(temp_uacp_root, "run-A", "g1")["ok"] is True
        assert self._register(temp_uacp_root, "run-B", "g1")["ok"] is True
        assert self._register(temp_uacp_root, "run-C", "g2")["ok"] is True

        runs = list_runs_for_goal(temp_uacp_root, "g1")
        assert sorted(runs) == ["run-A", "run-B"]
        assert list_runs_for_goal(temp_uacp_root, "g2") == ["run-C"]
        assert list_runs_for_goal(temp_uacp_root, "no-such-goal") == []


class TestStandardUnaffected:
    """(c) standard unaffected: no goal_id/inherits_from => identical to today."""

    def test_standard_init_has_no_goal_fields(self, temp_uacp_root: Path):
        result = json.loads(handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-std-001",
            "source": "operator-request",
        }))
        assert result["ok"] is True
        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / "uacp-std-001.yaml"
        data = yaml.safe_load(manifest_path.read_text())
        assert data["goal_id"] is None
        assert data["inherits_from"] is None
        assert data["inherited_artifacts"] == {}
        assert data["track"] == "standard"


class TestCallerBindingPreserved:
    """(d) caller-binding preserved: registry writer still rejects an entry
    whose run_id != caller uacp_run_id, even with goal_id present."""

    def test_rejects_mismatched_caller_with_goal_id(self, temp_uacp_root: Path):
        result = json.loads(_handle_uacp_run_registry_update({
            "workspace": str(temp_uacp_root),
            "uacp_run_id": "run-A",
            "uacp_phase": "execute",
            "policy_version": "0.1",
            "declared_side_effects": [],
            "op": "register",
            "entry": {
                "run_id": "run-B",  # mismatch
                "phase": "execute",
                "write_paths": ["src/x.py"],
                "scope_artifact_path": "plans/run-B-scope.yaml",
                "started_at": 1,
                "goal_id": "g1",
            },
            "reason": "squat attempt",
            "authority_artifact": "plans/run-B-scope.yaml",
        }))
        assert "error" in result
        assert "does not match caller" in result["error"]
