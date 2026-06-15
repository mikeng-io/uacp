"""Phase 1 state machine: init, read, transition, register-artifact, finalize.

Runtime-neutral — contains no Hermes or framework-specific imports.
Uses Pydantic v2 for schema validation.
"""

from __future__ import annotations

import json
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

# Ensure uacp-core/scripts is on the path for filesystem utilities.
_CORE_DIR = Path(__file__).resolve().parents[2] / "uacp-core" / "scripts"
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

# The canonical phase graph lives in engines/domain/phase_graph.py. Import it as
# a BARE module (mirroring the config/filesystem bootstrap above) so we do NOT
# trigger engines/domain/__init__, which re-exports VALID_TRANSITIONS from this
# module — importing the package here would create a circular import. phase_graph
# is a pure leaf (stdlib only), so this bare import is safe.
_PHASE_GRAPH_DIR = _CORE_DIR / "engines" / "domain"
if str(_PHASE_GRAPH_DIR) not in sys.path:
    sys.path.insert(0, str(_PHASE_GRAPH_DIR))

from config import base_dir
from filesystem import _resolve_uacp_path, _write_uacp_file
from phase_graph import runtime_terminal_phases, state_machine_projection


try:
    from pydantic import BaseModel, Field, field_validator
except Exception as exc:  # pragma: no cover
    raise ImportError("Pydantic v2 is required for state_machine") from exc


class Status(str, Enum):
    active = "active"
    paused = "paused"
    resolved = "resolved"
    aborted = "aborted"


# Valid phase transitions.  Each key is a "from" phase; value is the set of
# allowed "to" phases.  The graph is a DAG ending in "resolved".
#
# DERIVED, not hand-authored: this is the runtime-state-machine *projection* of
# the canonical lifecycle graph in engines/domain/phase_graph.py (the single
# source of truth, which also backs config/phase-transitions.yaml and
# config/uacp.toml). The projection collapses the lifecycle `resolve` phase into
# the terminal `resolved` status and drops early-exit `terminal` edges; see that
# module's docstring for the full reconciliation. The repo-level agreement test
# (tests/unit/uacp_core/test_phase_graph.py) pins this to the production config.
VALID_TRANSITIONS: dict[str, set[str]] = state_machine_projection()

# `resolved` is the projection of the lifecycle `resolve` phase; `aborted` is a
# runtime-only early-termination status with no lifecycle-graph counterpart.
TERMINAL_PHASES: set[str] = runtime_terminal_phases()


class Authority(BaseModel):
    source: str
    status: str = "pass"


class StateHistoryEntry(BaseModel):
    event: str
    timestamp: str = Field(default_factory=lambda: _iso_now())
    from_phase: str | None = None
    to_phase: str | None = None
    source: str | None = None
    artifact: str | None = None


class Workspace(BaseModel):
    kind: str = "worktree"
    path: str | None = None
    branch: str | None = None
    created_at: str = Field(default_factory=lambda: _iso_now())
    validated_at: str | None = None


class RunManifest(BaseModel):
    run_id: str
    status: Status = Status.active
    current_phase: str = "triage"
    created_at: str = Field(default_factory=lambda: _iso_now())
    authority: Authority
    workspace: Workspace = Field(default_factory=Workspace)
    artifacts: dict[str, str] = Field(default_factory=dict)
    state_history: list[StateHistoryEntry] = Field(default_factory=list)
    finalized_at: str | None = None

    @field_validator("run_id")
    @classmethod
    def _validate_run_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("run_id must not be empty")
        if any(c in v for c in ("/", "\\", "..")):
            raise ValueError("run_id contains illegal path characters")
        if " " in v or "\t" in v or "\n" in v:
            raise ValueError("run_id must not contain whitespace")
        return v


def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _run_manifest_path(workspace: Path, run_id: str) -> Path:
    return (_resolve_uacp_path(f"state/runs/{run_id}.yaml", base_dir(workspace))).resolve()


def _load_manifest(workspace: Path, run_id: str) -> RunManifest:
    path = _run_manifest_path(workspace, run_id)
    if not path.exists():
        raise FileNotFoundError(f"run manifest not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("run manifest must be a YAML mapping")
    # Pydantic v2: RunManifest.model_validate
    return RunManifest.model_validate(raw)


def _save_manifest(workspace: Path, manifest: RunManifest) -> Path:
    path = _run_manifest_path(workspace, manifest.run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump(manifest.model_dump(mode="json"), sort_keys=False)
    _write_uacp_file(path, body)
    return path


def handle_init(args: dict[str, Any]) -> str:
    """Create a new run manifest.

    Required args:
      workspace: UACP_ROOT path
      run_id: unique run identifier
      source: authority source (e.g. "operator-request")
    Optional args:
      scope, granularity, risk, domains — stored in authority metadata
      workspace_kind, workspace_path, workspace_branch — workspace declaration
    """
    try:
        workspace = Path(str(args.get("workspace") or ".")).resolve()
        run_id = str(args.get("run_id") or "").strip()
        source = str(args.get("source") or "").strip()

        if not run_id:
            return json.dumps({"error": "run_id is required"})
        if not source:
            return json.dumps({"error": "source is required"})

        manifest_path = _run_manifest_path(workspace, run_id)
        if manifest_path.exists():
            return json.dumps({"error": f"run manifest already exists: {run_id}"})

        authority = Authority(source=source, status="pass")
        # Attach optional metadata to authority
        for key in ("scope", "granularity", "risk", "domains"):
            value = args.get(key)
            if value is not None:
                if not hasattr(authority, "_metadata"):
                    authority._metadata = {}
                authority._metadata[key] = value

        # Workspace declaration (optional at init, required by PROPOSE)
        ws_kind = str(args.get("workspace_kind") or "worktree").strip()
        ws_path = str(args.get("workspace_path") or "").strip() or None
        ws_branch = str(args.get("workspace_branch") or "").strip() or None
        workspace_obj = Workspace(kind=ws_kind, path=ws_path, branch=ws_branch)

        manifest = RunManifest(run_id=run_id, authority=authority, workspace=workspace_obj)
        _save_manifest(workspace, manifest)

        # Create current.yaml pointer if none exists
        current_path = base_dir(workspace) / "state" / "current.yaml"
        if not current_path.exists():
            current_body = yaml.safe_dump(
                {"active_run_id": run_id, "active_run_manifest": str(manifest_path.relative_to(base_dir(workspace)))},
                sort_keys=False,
            )
            current_path.parent.mkdir(parents=True, exist_ok=True)
            _write_uacp_file(current_path, current_body)

        return json.dumps({
            "ok": True,
            "run_id": run_id,
            "manifest_path": str(manifest_path.relative_to(base_dir(workspace))),
        }, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": f"init failed: {type(exc).__name__}: {exc}"})


def handle_read(args: dict[str, Any]) -> str:
    """Read an existing run manifest."""
    try:
        workspace = Path(str(args.get("workspace") or ".")).resolve()
        run_id = str(args.get("run_id") or "").strip()
        if not run_id:
            return json.dumps({"error": "run_id is required"})

        manifest = _load_manifest(workspace, run_id)
        return json.dumps({
            "ok": True,
            "manifest": manifest.model_dump(mode="json"),
        }, ensure_ascii=False)
    except FileNotFoundError as exc:
        return json.dumps({"error": f"read failed: {exc}"})
    except Exception as exc:
        return json.dumps({"error": f"read failed: {type(exc).__name__}: {exc}"})


def handle_transition(args: dict[str, Any]) -> str:
    """Locked phase transition with validation."""
    try:
        workspace = Path(str(args.get("workspace") or ".")).resolve()
        run_id = str(args.get("run_id") or "").strip()
        from_phase = str(args.get("from_phase") or "").strip()
        to_phase = str(args.get("to_phase") or "").strip()

        if not run_id:
            return json.dumps({"error": "run_id is required"})
        if not from_phase:
            return json.dumps({"error": "from_phase is required"})
        if not to_phase:
            return json.dumps({"error": "to_phase is required"})

        manifest = _load_manifest(workspace, run_id)

        if manifest.status == Status.resolved or manifest.current_phase in TERMINAL_PHASES:
            return json.dumps({"error": f"transition refused: run is in terminal phase '{manifest.current_phase}'"})

        if manifest.current_phase != from_phase:
            return json.dumps({
                "error": f"transition refused: current phase is '{manifest.current_phase}', not '{from_phase}'",
            })

        allowed = VALID_TRANSITIONS.get(from_phase, set())
        if to_phase not in allowed:
            return json.dumps({
                "error": f"transition not allowed: {from_phase} -> {to_phase} (allowed: {sorted(allowed)})",
            })

        manifest.current_phase = to_phase
        if to_phase in TERMINAL_PHASES:
            manifest.status = Status(to_phase) if to_phase in {s.value for s in Status} else manifest.status

        manifest.state_history.append(StateHistoryEntry(
            event="phase_transition",
            from_phase=from_phase,
            to_phase=to_phase,
            source="uacp-state",
        ))

        _save_manifest(workspace, manifest)
        return json.dumps({
            "ok": True,
            "run_id": run_id,
            "from_phase": from_phase,
            "to_phase": to_phase,
        }, ensure_ascii=False)
    except FileNotFoundError as exc:
        return json.dumps({"error": f"transition failed: {exc}"})
    except Exception as exc:
        return json.dumps({"error": f"transition failed: {type(exc).__name__}: {exc}"})


def handle_register_artifact(args: dict[str, Any]) -> str:
    """Link a phase artifact into the run manifest."""
    try:
        workspace = Path(str(args.get("workspace") or ".")).resolve()
        run_id = str(args.get("run_id") or "").strip()
        artifact_type = str(args.get("artifact_type") or "").strip()
        path_raw = str(args.get("path") or "").strip()

        if not run_id:
            return json.dumps({"error": "run_id is required"})
        if not artifact_type:
            return json.dumps({"error": "artifact_type is required"})
        if not path_raw:
            return json.dumps({"error": "path is required"})

        manifest = _load_manifest(workspace, run_id)

        # Ensure artifact path stays inside the governed namespace (.uacp/).
        # Paths are base-relative (e.g. proposals/x.md, resolutions/x.yaml), so
        # containment is checked under base_dir, and path_raw is stored verbatim.
        try:
            base = base_dir(workspace)
            resolved = _resolve_uacp_path(path_raw, base)
            resolved.relative_to(base)
        except ValueError:
            return json.dumps({"error": f"artifact path escapes workspace: {path_raw}"})

        manifest.artifacts[artifact_type] = path_raw
        _save_manifest(workspace, manifest)
        return json.dumps({
            "ok": True,
            "run_id": run_id,
            "artifact_type": artifact_type,
            "path": path_raw,
        }, ensure_ascii=False)
    except FileNotFoundError as exc:
        return json.dumps({"error": f"register-artifact failed: {exc}"})
    except Exception as exc:
        return json.dumps({"error": f"register-artifact failed: {type(exc).__name__}: {exc}"})


def handle_workspace(args: dict[str, Any]) -> str:
    """Update or validate workspace metadata in the run manifest.

    Required args:
      workspace: UACP_ROOT path
      run_id: unique run identifier
    Optional args:
      kind, path, branch, validated_at — update workspace fields
    """
    try:
        workspace = Path(str(args.get("workspace") or ".")).resolve()
        run_id = str(args.get("run_id") or "").strip()

        if not run_id:
            return json.dumps({"error": "run_id is required"})

        manifest = _load_manifest(workspace, run_id)

        # Update workspace fields if provided
        for key in ("kind", "path", "branch"):
            value = args.get(f"workspace_{key}")
            if value is not None:
                setattr(manifest.workspace, key, str(value))

        validated_at = args.get("workspace_validated_at")
        if validated_at is not None:
            manifest.workspace.validated_at = str(validated_at)

        _save_manifest(workspace, manifest)
        return json.dumps({
            "ok": True,
            "run_id": run_id,
            "workspace": manifest.workspace.model_dump(mode="json"),
        }, ensure_ascii=False)
    except FileNotFoundError as exc:
        return json.dumps({"error": f"workspace update failed: {exc}"})
    except Exception as exc:
        return json.dumps({"error": f"workspace update failed: {type(exc).__name__}: {exc}"})


def handle_finalize(args: dict[str, Any]) -> str:
    """Finalize a run from verify -> resolved."""
    try:
        workspace = Path(str(args.get("workspace") or ".")).resolve()
        run_id = str(args.get("run_id") or "").strip()

        if not run_id:
            return json.dumps({"error": "run_id is required"})

        manifest = _load_manifest(workspace, run_id)

        if manifest.current_phase not in TERMINAL_PHASES:
            return json.dumps({
                "error": f"finalize refused: run is in phase '{manifest.current_phase}', not in terminal phase ({sorted(TERMINAL_PHASES)})",
            })

        if manifest.status != Status.resolved:
            manifest.status = Status.resolved

        manifest.finalized_at = _iso_now()
        _save_manifest(workspace, manifest)
        return json.dumps({
            "ok": True,
            "run_id": run_id,
            "status": manifest.status.value,
            "finalized_at": manifest.finalized_at,
        }, ensure_ascii=False)
    except FileNotFoundError as exc:
        return json.dumps({"error": f"finalize failed: {exc}"})
    except Exception as exc:
        return json.dumps({"error": f"finalize failed: {type(exc).__name__}: {exc}"})
