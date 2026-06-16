"""TDD tests for Phase 1 state machine (init, read, transition, register-artifact, finalize)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from state_machine import (
    Authority,
    RunManifest,
    Status,
    handle_finalize,
    handle_init,
    handle_read,
    handle_register_artifact,
    handle_transition,
)


class TestRunManifestSchema:
    """Pydantic schema validation for RunManifest."""

    def test_valid_manifest(self):
        manifest = RunManifest(
            run_id="uacp-test-001",
            status=Status.active,
            current_phase="triage",
            created_at="2026-06-07T12:00:00Z",
            authority={"source": "operator-request", "status": "pass"},
        )
        assert manifest.run_id == "uacp-test-001"
        assert manifest.status == Status.active
        assert manifest.current_phase == "triage"

    def test_rejects_invalid_status(self):
        with pytest.raises(ValueError):
            RunManifest(
                run_id="uacp-test-001",
                status="invalid_status",
                current_phase="triage",
                created_at="2026-06-07T12:00:00Z",
            )

    def test_rejects_run_id_with_traversal(self):
        with pytest.raises(ValueError):
            RunManifest(
                run_id="../../../etc/passwd",
                status=Status.active,
                current_phase="triage",
                created_at="2026-06-07T12:00:00Z",
            )

    def test_rejects_run_id_with_whitespace(self):
        with pytest.raises(ValueError):
            RunManifest(
                run_id="uacp test 001",
                status=Status.active,
                current_phase="triage",
                created_at="2026-06-07T12:00:00Z",
            )

    def test_default_empty_artifacts(self):
        manifest = RunManifest(
            run_id="uacp-test-001",
            status=Status.active,
            current_phase="triage",
            created_at="2026-06-07T12:00:00Z",
            authority=Authority(source="test"),
        )
        assert manifest.artifacts == {}
        assert manifest.state_history == []


class TestStateMachineInit:
    """Tests for handle_init."""

    def test_creates_run_manifest(self, temp_uacp_root: Path):
        result = json.loads(handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
            "scope": "software",
            "granularity": "medium",
            "risk": "medium",
        }))
        assert result["ok"] is True
        assert result["run_id"] == "uacp-test-001"

        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / "uacp-test-001.yaml"
        assert manifest_path.exists()
        # C-1: manifest lands under .uacp/, never the flat root.
        assert not (temp_uacp_root / "state" / "runs" / "uacp-test-001.yaml").exists()
        data = yaml.safe_load(manifest_path.read_text())
        assert data["run_id"] == "uacp-test-001"
        assert data["status"] == "active"
        assert data["current_phase"] == "triage"
        assert data["authority"]["source"] == "operator-request"
        assert data["authority"]["status"] == "pass"

    def test_rejects_duplicate_run_id(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        result = json.loads(handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        }))
        assert "error" in result
        assert "already exists" in result["error"]

    def test_creates_current_pointer_on_first_run(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        current_path = temp_uacp_root / ".uacp" / "state" / "current.yaml"
        assert current_path.exists()
        # C-1: pointer lands under .uacp/, never the flat root.
        assert not (temp_uacp_root / "state" / "current.yaml").exists()
        data = yaml.safe_load(current_path.read_text())
        assert data["active_run_id"] == "uacp-test-001"
        # Base-relative manifest ref (resolved under .uacp/), not .uacp/-prefixed.
        assert data["active_run_manifest"] == "state/runs/uacp-test-001.yaml"

    def test_does_not_overwrite_current_pointer(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-002",
            "source": "operator-request",
        })
        current_path = temp_uacp_root / ".uacp" / "state" / "current.yaml"
        data = yaml.safe_load(current_path.read_text())
        # First run stays active
        assert data["active_run_id"] == "uacp-test-001"


class TestStateMachineRead:
    """Tests for handle_read."""

    def test_reads_existing_manifest(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        result = json.loads(handle_read({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
        }))
        assert result["ok"] is True
        assert result["manifest"]["run_id"] == "uacp-test-001"

    def test_rejects_missing_manifest(self, temp_uacp_root: Path):
        result = json.loads(handle_read({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
        }))
        assert "error" in result
        assert "not found" in result["error"]


class TestStateMachineTransition:
    """Tests for handle_transition."""

    def test_valid_transition(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        result = json.loads(handle_transition({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "from_phase": "triage",
            "to_phase": "propose",
        }))
        assert result["ok"] is True
        assert result["from_phase"] == "triage"
        assert result["to_phase"] == "propose"

        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / "uacp-test-001.yaml"
        data = yaml.safe_load(manifest_path.read_text())
        assert data["current_phase"] == "propose"
        assert len(data["state_history"]) == 1
        assert data["state_history"][0]["event"] == "phase_transition"

    def test_rejects_invalid_transition(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        result = json.loads(handle_transition({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "from_phase": "triage",
            "to_phase": "execute",  # Invalid: triage -> execute not allowed
        }))
        assert "error" in result
        assert "not allowed" in result["error"]

    def test_rejects_wrong_current_phase(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        result = json.loads(handle_transition({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "from_phase": "propose",  # Wrong: current is triage
            "to_phase": "plan",
        }))
        assert "error" in result
        assert "current phase" in result["error"]

    def test_rejects_transition_from_terminal_state(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        # Mark as resolved
        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / "uacp-test-001.yaml"
        data = yaml.safe_load(manifest_path.read_text())
        data["status"] = "resolved"
        data["current_phase"] = "resolved"
        manifest_path.write_text(yaml.safe_dump(data))

        result = json.loads(handle_transition({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "from_phase": "resolved",
            "to_phase": "triage",
        }))
        assert "error" in result
        assert "terminal" in result["error"]


class TestStateMachineRegisterArtifact:
    """Tests for handle_register_artifact."""

    def test_registers_artifact(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        result = json.loads(handle_register_artifact({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "artifact_type": "triage",
            "path": "proposals/uacp-test-001-triage.yaml",
        }))
        assert result["ok"] is True

        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / "uacp-test-001.yaml"
        data = yaml.safe_load(manifest_path.read_text())
        assert data["artifacts"]["triage"] == "proposals/uacp-test-001-triage.yaml"

    def test_rejects_missing_manifest(self, temp_uacp_root: Path):
        result = json.loads(handle_register_artifact({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "artifact_type": "triage",
            "path": "proposals/test.yaml",
        }))
        assert "error" in result
        assert "not found" in result["error"]

    def test_rejects_path_traversal_in_artifact_path(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        result = json.loads(handle_register_artifact({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "artifact_type": "triage",
            "path": "../../../etc/passwd",
        }))
        assert "error" in result
        assert "escapes" in result["error"]


class TestStateMachineFinalize:
    """Tests for handle_finalize."""

    def test_finalize_resolved_run(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        # Move through phases to resolved
        handle_transition({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "from_phase": "triage",
            "to_phase": "propose",
        })
        handle_transition({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "from_phase": "propose",
            "to_phase": "plan",
        })
        handle_transition({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "from_phase": "plan",
            "to_phase": "execute",
        })
        handle_transition({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "from_phase": "execute",
            "to_phase": "verify",
        })
        handle_transition({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "from_phase": "verify",
            "to_phase": "resolved",
        })

        result = json.loads(handle_finalize({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
        }))
        assert result["ok"] is True
        assert result["status"] == "resolved"

        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / "uacp-test-001.yaml"
        data = yaml.safe_load(manifest_path.read_text())
        assert data["status"] == "resolved"
        assert data["finalized_at"] is not None

    def test_rejects_finalize_from_non_terminal_phase(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        result = json.loads(handle_finalize({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
        }))
        assert "error" in result
        assert "not in terminal phase" in result["error"]


class TestRunManifestTrackFields:
    """Tests for the new track/goal_id/inherits_from fields on RunManifest."""

    def test_defaults_when_not_set(self):
        """RunManifest with none of the new fields set has standard defaults."""
        manifest = RunManifest(
            run_id="uacp-test-defaults",
            authority=Authority(source="test"),
        )
        assert manifest.track == "standard"
        assert manifest.goal_id is None
        assert manifest.inherits_from is None

    def test_goal_driven_track_fields_accepted(self):
        """RunManifest accepts goal-driven track with goal_id and inherits_from."""
        manifest = RunManifest(
            run_id="uacp-test-gd",
            authority=Authority(source="test"),
            track="goal-driven",
            goal_id="g1",
            inherits_from="run-A",
        )
        assert manifest.track == "goal-driven"
        assert manifest.goal_id == "g1"
        assert manifest.inherits_from == "run-A"

    def test_standard_track_explicit(self):
        """RunManifest with explicit track='standard' is identical to default."""
        manifest = RunManifest(
            run_id="uacp-test-explicit",
            authority=Authority(source="test"),
            track="standard",
        )
        assert manifest.track == "standard"
        assert manifest.goal_id is None
        assert manifest.inherits_from is None


class TestHandleInitTrackFields:
    """Tests that handle_init threads track/goal_id/inherits_from into the manifest."""

    def test_goal_driven_fields_persisted(self, temp_uacp_root: Path):
        """handle_init with goal-driven args writes them into the manifest YAML."""
        result = json.loads(handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-gd-001",
            "source": "operator-request",
            "track": "goal-driven",
            "goal_id": "g1",
            "inherits_from": "run-A",
        }))
        assert result["ok"] is True

        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / "uacp-gd-001.yaml"
        data = yaml.safe_load(manifest_path.read_text())
        assert data["track"] == "goal-driven"
        assert data["goal_id"] == "g1"
        assert data["inherits_from"] == "run-A"

    def test_standard_run_defaults_in_manifest(self, temp_uacp_root: Path):
        """handle_init without new args produces a manifest with standard defaults."""
        result = json.loads(handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-std-001",
            "source": "operator-request",
        }))
        assert result["ok"] is True

        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / "uacp-std-001.yaml"
        data = yaml.safe_load(manifest_path.read_text())
        assert data["track"] == "standard"
        assert data["goal_id"] is None
        assert data["inherits_from"] is None
        # Existing fields must still be present
        assert data["run_id"] == "uacp-std-001"
        assert data["status"] == "active"
        assert data["current_phase"] == "triage"

    def test_invalid_track_returns_error(self, temp_uacp_root: Path):
        """handle_init with an unknown track returns a JSON error, no manifest written."""
        result = json.loads(handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-bad-track",
            "source": "operator-request",
            "track": "turbo-mode",
        }))
        assert "error" in result
        assert "track" in result["error"].lower()
        # No manifest should have been created
        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / "uacp-bad-track.yaml"
        assert not manifest_path.exists()
