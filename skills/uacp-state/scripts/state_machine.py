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
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from core import HeartgateDecision

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


_VALID_TRACKS: frozenset[str] = frozenset({"standard", "goal-driven"})


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
    track: str = "standard"
    goal_id: str | None = None
    inherits_from: str | None = None
    # Goal-chaining: phase-output references reused from the run named by
    # `inherits_from`. Kept SEPARATE from `artifacts` (which holds THIS run's
    # own freshly-registered outputs) so provenance is unambiguous — an entry
    # here means "reused from the parent run", not "produced by this run".
    inherited_artifacts: dict[str, str] = Field(default_factory=dict)

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

        # Track validation — fail closed on unknown tracks.
        track = str(args.get("track") or "standard").strip()
        if track not in _VALID_TRACKS:
            return json.dumps({"error": f"invalid track '{track}': must be one of {sorted(_VALID_TRACKS)}"})

        goal_id: str | None = str(args["goal_id"]).strip() or None if args.get("goal_id") is not None else None
        inherits_from: str | None = str(args["inherits_from"]).strip() or None if args.get("inherits_from") is not None else None

        manifest_path = _run_manifest_path(workspace, run_id)
        if manifest_path.exists():
            return json.dumps({"error": f"run manifest already exists: {run_id}"})

        # Goal-chaining (Task 3): when launching a forward run under a held goal
        # that inherits a prior run, copy the parent's reusable prior-phase
        # output references into inherited_artifacts. The reused set is the
        # parent's `artifacts` entries for the completed upstream phases
        # (triage/proposal/plan) — the parent's MUTABLE state (state_history,
        # its own in-flight artifacts beyond those phases, status) is NOT
        # carried over, matching design 0016 P2=option-b (a checkpoint is a
        # reusable prior-phase output reference, not an in-run state snapshot).
        # Fail closed if the named parent manifest is absent.
        inherited_artifacts: dict[str, str] = {}
        if inherits_from is not None:
            try:
                parent = _load_manifest(workspace, inherits_from)
            except FileNotFoundError:
                return json.dumps({"error": f"inherits_from parent manifest not found: {inherits_from}"})
            _REUSABLE_PHASE_ARTIFACTS = ("triage", "proposal", "plan")
            inherited_artifacts = {
                k: parent.artifacts[k]
                for k in _REUSABLE_PHASE_ARTIFACTS
                if k in parent.artifacts
            }

        # Optional initial_phase: allows a run to start at 'brainstorm' instead
        # of the default 'triage'. Fail closed on unknown phases.
        initial_phase = str(args.get("initial_phase") or "triage").strip()
        _VALID_INITIAL_PHASES = {"triage", "brainstorm"}
        if initial_phase not in _VALID_INITIAL_PHASES:
            return json.dumps({"error": f"invalid initial_phase '{initial_phase}': must be one of {sorted(_VALID_INITIAL_PHASES)}"})

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

        manifest = RunManifest(
            run_id=run_id,
            current_phase=initial_phase,
            authority=authority,
            workspace=workspace_obj,
            track=track,
            goal_id=goal_id,
            inherits_from=inherits_from,
            inherited_artifacts=inherited_artifacts,
        )
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


def list_runs_for_goal(workspace: Path, goal_id: str) -> list[str]:
    """Return the run_ids of all active registry entries carrying ``goal_id``.

    Goal-chaining query (Task 3): the goal->runs chain is recorded on the run
    registry (state/run-registry.yaml) as a ``goal_id`` field on each
    active_runs[] entry, and queried by a simple registry scan. No separate
    goal index is introduced — the registry is already the authoritative list
    of live runs, so a held goal's chain is exactly its entries that share a
    goal_id. A missing/empty registry means "no active runs" -> [].
    """
    base = base_dir(workspace)
    registry_path = (base / "state" / "run-registry.yaml").resolve()
    if not registry_path.exists():
        return []
    raw = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return []
    active = raw.get("active_runs") or []
    if not isinstance(active, list):
        return []
    out: list[str] = []
    for entry in active:
        if isinstance(entry, dict) and entry.get("goal_id") == goal_id:
            rid = entry.get("run_id")
            if rid:
                out.append(str(rid))
    return out


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


# Phases whose exit has a defined structural-graph subset (D35). Earlier phases
# (triage/propose) have no graph layer yet, so their exit is not graph-gated.
_GRAPH_GATED_PHASES: frozenset[str] = frozenset({"plan", "execute", "verify"})


def _run_transition_graph_gate(workspace: Path, run_id: str, from_phase: str) -> list[str]:
    """Phase-scoped structural graph gate for a LIVE transition (D35).

    Forces ``validate_graph_invariants('<from_phase>_exit')`` onto the live
    transition path — the state-derived structural subset of the Heartgate
    transition gate (dropped intent / orphan / phantom / missing coverage /
    contradiction), which otherwise runs only inside the agent-invoked
    ``validate_transition``. Returns block-severity violations as ``"CODE: message"``
    strings (empty == pass). Phase-independent, so it runs BEFORE the phase mutation
    (no revert needed). Fail-closed: a gate that cannot run blocks the transition.

    Lazy import: keeps the state machine free of the engines package for callers
    that never transition, and avoids the engines->state_machine import cycle.
    """
    if from_phase not in _GRAPH_GATED_PHASES:
        return []
    try:
        from engines.graph_projection import validate_graph_invariants

        violations = validate_graph_invariants(workspace, run_id, f"{from_phase}_exit")
        return [f"{v.code}: {v.message}" for v in violations if v.severity == "block"]
    except Exception as exc:  # fail-closed: an unrunnable gate must not advance
        return [f"TRANSITION_GRAPH_GATE_UNAVAILABLE: {type(exc).__name__}: {exc}"]


def _run_forced_brainstorm_exit_gate(workspace: Path, run_id: str, from_phase: str) -> list[str]:
    """Force the brainstorm admission contract onto BRAINSTORM->TRIAGE on the live path
    (the same "force the exit precondition" pattern as the propose/execute forced gates).
    Without this, ``handle_transition`` advanced brainstorm->triage with NO scope package,
    because the exit invariant was only enforced on the agent-invoked ``validate_transition``
    path that the governed ``uacp_run_transition`` tool bypasses — letting an agent request a
    transition that is effected with the admission contract never measured. Self-gating: only
    fires at brainstorm exit (brainstorm's only exit is triage; the scope package IS that
    exit's deliverable, so there is no bare/ungoverned crossing to skip). Fail-closed: an
    unrunnable gate blocks. Lazy import (engines<->state cycle)."""
    if from_phase != "brainstorm":
        return []
    try:
        from core import Heartgate

        return Heartgate.load(str(workspace)).forced_brainstorm_exit_blockers(run_id)
    except Exception as exc:  # fail-closed
        return [f"FORCED_BRAINSTORM_EXIT_UNAVAILABLE: {type(exc).__name__}: {exc}"]


def _run_forced_proposal_coverage_gate(workspace: Path, run_id: str, from_phase: str) -> list[str]:
    """Force the proposal-gate REGISTRATION precondition onto PROPOSE->PLAN on the
    live path (node-15 residual #1, coverage half). Without this, a package-selection
    run could declare a covered keyed scope module, never register it, skip
    ``validate_transition``, and advance via ``handle_transition`` — leaving the
    forced ``plan_exit`` gate with no scope_items to enforce (a dropped intent
    escapes). Self-gating: only fires at PROPOSE exit and only when a package-selection
    envelope declares a covered keyed scope (bare/ungoverned transitions return []).
    Fail-closed: an unrunnable gate blocks. Lazy import (engines<->state cycle)."""
    if from_phase != "propose":
        return []
    try:
        from core import Heartgate

        return Heartgate.load(str(workspace)).forced_proposal_coverage_blockers(run_id)
    except Exception as exc:  # fail-closed
        return [f"FORCED_PROPOSAL_COVERAGE_UNAVAILABLE: {type(exc).__name__}: {exc}"]


def _run_forced_execute_evidence_gate(workspace: Path, run_id: str, from_phase: str) -> list[str]:
    """Force the execute-evidence PIV precondition onto EXECUTE->VERIFY on the live path (the
    "force one ripple-free precondition" pattern, extended to EXECUTE). Without this, a run could
    register covering execution checkpoints, never author a PIV, skip ``validate_transition``, and
    advance via ``handle_transition`` — the forced ``execute_exit`` gate only checks checkpoint
    coverage, not the PIV the adaptive execute-evidence gate demands. Self-gating: only fires at
    EXECUTE exit and only when the governed-execute marker (ANY ``{run_id}-checkpoint-*.yaml``, not
    only ``-001``) is present (bare / ungoverned transitions return []); goal-driven runs are
    relaxed to the coherent checkpoint manifest. When the PIV declares ``work_units`` it also
    derives per-unit coverage from ``after_work_unit`` checkpoints (each required unit needs a clean
    one). Fail-closed: an unrunnable gate blocks. Lazy import (engines<->state cycle)."""
    if from_phase != "execute":
        return []
    try:
        from core import Heartgate

        return Heartgate.load(str(workspace)).forced_execute_evidence_blockers(run_id)
    except Exception as exc:  # fail-closed
        return [f"FORCED_EXECUTE_EVIDENCE_UNAVAILABLE: {type(exc).__name__}: {exc}"]


def handle_transition(args: dict[str, Any]) -> str:
    """Locked phase transition with validation + the phase-exit structural gate."""
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

        # Phase-exit structural gate: run the state-derived graph invariants for
        # this exit BEFORE advancing. Forces the gate onto the live path so a
        # phase can no longer advance past a dropped/orphan/phantom/contradicted
        # graph just because the agent skipped uacp_heartgate_check. Fail-closed.
        # Plus the forced PROPOSE->PLAN registration precondition (residual #1) so a
        # package-selection run cannot leave its keyed scope module unregistered and
        # thereby starve the plan_exit coverage gate. Plus the forced BRAINSTORM->TRIAGE
        # admission contract so the scope package's real fields are measured here (not only
        # on the agent-invoked validate_transition path the governed transition tool bypasses).
        gate_blockers = _run_transition_graph_gate(workspace, run_id, from_phase)
        gate_blockers += _run_forced_brainstorm_exit_gate(workspace, run_id, from_phase)
        gate_blockers += _run_forced_proposal_coverage_gate(workspace, run_id, from_phase)
        gate_blockers += _run_forced_execute_evidence_gate(workspace, run_id, from_phase)
        if gate_blockers:
            return json.dumps({
                "error": "transition blocked by phase-exit structural gate",
                "from_phase": from_phase,
                "to_phase": to_phase,
                "blockers": gate_blockers,
            }, ensure_ascii=False)

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


def _run_closure_gate(workspace: Path, run_id: str) -> HeartgateDecision:
    """Run the Heartgate closure sweep (the full computed-engine pass) for a run.

    This is the LIVE wiring of ``Heartgate.validate_closure``: it expects the run
    to already be finalized on disk (the engines' terminal checks assume the
    resolved/closed state). ``validate_closure`` never raises — but the kernel
    import / config load can — so we fail CLOSED: any failure to even run the gate
    is surfaced as a block, never a silent pass.

    Lazy import: keeps the state machine free of the kernel for callers that never
    finalize, and avoids the engines->state_machine import cycle (the engines
    package imports this module, so importing it at module load would cycle).
    """
    try:
        from core import Heartgate

        return Heartgate.load(workspace).validate_closure(run_id)
    except Exception as exc:  # fail-closed: an unrunnable gate must not finalize
        return _closure_unavailable_block(exc)


def _closure_unavailable_block(exc: Exception) -> HeartgateDecision:
    from core import HeartgateDecision as _Decision

    return _Decision(
        "block",
        "closure gate could not be run",
        [f"CLOSURE_GATE_UNAVAILABLE: {type(exc).__name__}: {exc}"],
        [],
    )


def handle_finalize(args: dict[str, Any]) -> str:
    """Finalize a run from verify -> resolved, gated by the closure sweep.

    Finalizing stamps the run resolved/finalized, THEN runs the Heartgate closure
    sweep (all computed engines) over the now-finalized state. If the sweep blocks
    the run is reverted to its pre-finalize state and an error with the engine
    blockers is returned — a run can no longer be stamped 'resolved' while the
    strongest verification the system owns goes unrun. Fail-closed.
    """
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

        # Tentatively finalize so the closure engines see a resolved/finalized run
        # (their terminal checks false-positive on a not-yet-finalized run). Keep
        # the prior state to revert if the gate blocks.
        prior_status = manifest.status
        prior_finalized_at = manifest.finalized_at
        manifest.status = Status.resolved
        manifest.finalized_at = _iso_now()
        _save_manifest(workspace, manifest)

        # Fail-closed: a gate that blocks OR cannot run at all reverts the
        # tentative finalize. Wrapped so even a pathological gate failure (e.g.
        # the kernel is unimportable) can never leave a run finalized-on-disk.
        try:
            decision = _run_closure_gate(workspace, run_id)
            blocked = decision.blocks_transition
        except Exception as exc:  # pragma: no cover - kernel totally unavailable
            decision = _closure_unavailable_block(exc)
            blocked = True

        if blocked:
            manifest.status = prior_status
            manifest.finalized_at = prior_finalized_at
            _save_manifest(workspace, manifest)
            return json.dumps({
                "error": "finalize blocked by closure sweep",
                "decision": decision.decision,
                "blockers": decision.blockers,
                "warnings": decision.warnings,
            }, ensure_ascii=False)

        return json.dumps({
            "ok": True,
            "run_id": run_id,
            "status": manifest.status.value,
            "finalized_at": manifest.finalized_at,
            "closure": decision.decision,
            "warnings": decision.warnings,
        }, ensure_ascii=False)
    except FileNotFoundError as exc:
        return json.dumps({"error": f"finalize failed: {exc}"})
    except Exception as exc:
        return json.dumps({"error": f"finalize failed: {type(exc).__name__}: {exc}"})
