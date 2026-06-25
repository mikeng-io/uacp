"""The Heartgate phase-transition gate (Phase A3 extraction from ``core.py``).

Heartgate validates UACP lifecycle transition artifacts and run closures,
orchestrating a sequence of ``_validate_*`` checks into a pass / warn / block
decision. Moved verbatim out of the ``core.py`` monolith as the A3 increment
(design/graph-engine nodes 30/31): a behaviour-preserving relocation — the class
body and the module-level helpers below are byte-identical to the originals; only
this import header is new. ``core.py`` re-exports ``Heartgate`` (and the private
helpers ``_is_safe_run_id`` / ``_truthy`` / ``_load_artifact_schemas`` that
``state.py`` and the hermes guardian kernel shim import) so callers are unaffected.

Transitional decomposition debt (A3.0): this module carries the whole ~2.3k-line
god-class verbatim, so it is still held to pyflakes-only lint + deferred
formatting (pyproject ``per-file-ignores`` / ``format.exclude``). Removal owner:
the A3.1+ carve increments (``validators/*`` + ``goal_driven.py``) and the
heartgate strict-typing gate — each lands a cohesive slice in its final module
held to the full ruleset, shrinking these exceptions until both are gone.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from config import base_dir
from engines.artifact_integrity import validate_artifact_integrity
from engines.base import run_all_engines
from engines.domain.gate_rules import (
    PLAN_NOT_APPLICABLE_REQUIRED_FIELDS,
    PROPOSAL_NOT_APPLICABLE_REQUIRED_FIELDS,
)
from engines.domain.paths import resolve_uacp_root
from engines.domain.phase_transitions import (
    phase_transition_required_fields,
    stages_default,
)
from engines.io import load_phase_transitions
from engines.io import loaders as io_loaders
from engines.manifest import validators as manifest_validators

from . import goal_driven
from .models import HeartgateDecision, HeartgateError
from .validators import adaptive_gates, coherence, phase_exit, plan_validation, ppv, run_registry

# Re-export of the helpers leaf: NOT used in-file anymore (the manifest doc-validators that
# used it moved to engines.manifest.validators in Phase C), but core.py re-exports it via this
# module for state.py / the hermes shim, and test_heartgate_extraction asserts
# ``core._is_safe_run_id is heartgate_mod._is_safe_run_id``. Keep the module-level re-export.
from .validators.helpers import _is_safe_run_id  # noqa: F401

try:
    import yaml
except ImportError:  # pragma: no cover - Hermes ships with PyYAML in normal use.
    yaml = None  # type: ignore[assignment]


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _load_artifact_schemas(uacp_root: Path) -> dict[str, Any]:  # noqa: ARG001
    """Return the codified artifact schemas (Slice 4a).

    Previously read ``config/artifact-schemas.yaml`` via yaml.safe_load.
    Now returns the same dict shape from the Pydantic models in
    ``engines.domain.artifact_schema`` — no filesystem I/O, no YAML dependency.
    The ``uacp_root`` argument is kept for call-site compatibility but is no
    longer used.

    The two operator-tunable path tables (tool_path_capabilities and
    handler_refusals) are NOT in the returned dict; they have moved to
    ``config/uacp.toml [scope]`` and are read via ``get_config(uacp_root)``.
    """
    try:
        from engines.domain.artifact_schema import artifact_schemas_dict

        return artifact_schemas_dict()
    except Exception:
        return {}


class Heartgate:
    """Validate UACP lifecycle transition artifacts.

    Heartgate validates the adaptive evidence selected for a specific run; it
    does not define a fixed gate checklist.
    """

    def __init__(self, config: Mapping[str, Any], *, uacp_root: str | Path | None = None):
        self.config = dict(config)
        self.uacp_root = resolve_uacp_root(uacp_root)
        self.governed_root = base_dir(self.uacp_root)
        # Slice 4b T4d-1: stages grammar (exits_to/allowed_tools/forbidden_tools/
        # phase_exit_invariants) is codified in
        # engines.domain.phase_transitions.stages_default(). Heartgate.load reads
        # via load_phase_transitions, which already injects that default when the
        # loaded config omits `stages`; this constructor-level fallback covers any
        # direct Heartgate(config) construction with a stage-less config so the
        # transition/exit-invariant/scope-tool checks never silently go absent.
        # A loaded non-empty `stages` block wholesale-overrides the default.
        stages = self.config.get("stages")
        if not stages:
            stages = stages_default()
        self.stages = stages
        # Slice 5 W2 (closes T4d-2) + BLOCKER fix: artifact_schema.required_fields
        # is codified in engines.domain.phase_transition_required_fields()
        # (enforce-by-default). The W2 slim removed only the required_fields KEY from
        # config/phase-transitions.yaml but LEFT the artifact_schema BLOCK present
        # (it still carries unconsumed doctrine: kind, fields, conventions). So the
        # fallback must key on KEY PRESENCE, not block presence: when the loaded
        # block OMITS required_fields (production, after the slim), use the code
        # default (ENFORCE); when the KEY is PRESENT (e.g. the test fixture's opt-out
        # stub `required_fields: []`), its value wins (an explicit empty list opts
        # the gate OFF, exactly as before, and lets a project deliberately disable).
        schema = self.config.get("artifact_schema")
        if isinstance(schema, Mapping) and "required_fields" in schema:
            self.required_fields = list(schema.get("required_fields") or [])
        else:
            self.required_fields = phase_transition_required_fields()
        # Phase 2: artifact schemas (scope, intent, evidence_disposition, lessons)
        self.artifact_schemas = _load_artifact_schemas(self.uacp_root)

    @classmethod
    def load(cls, uacp_root: str | Path | None = None) -> Heartgate:
        root = resolve_uacp_root(uacp_root)
        loaded = load_phase_transitions(root)
        if loaded.error is not None:
            raise HeartgateError(f"Heartgate config failed to load: {loaded.error}")
        raw = loaded.value
        if not isinstance(raw, dict):
            raise HeartgateError(
                "Heartgate config must be a YAML mapping: "
                f"{root / 'config' / 'phase-transitions.yaml'}"
            )
        return cls(raw, uacp_root=root)

    def validate_transition(self, artifact: Mapping[str, Any]) -> HeartgateDecision:
        blockers: list[str] = []
        warnings: list[str] = []

        for field_name in self.required_fields:
            if field_name not in artifact:
                blockers.append(f"missing required field: {field_name}")

        from_phase = str(artifact.get("from_phase") or "")
        to_phase = str(artifact.get("to_phase") or "")
        if not self._transition_allowed(from_phase, to_phase):
            blockers.append(f"transition not allowed: {from_phase} -> {to_phase}")

        for invariant in artifact.get("invariant_summary") or []:
            status = str((invariant or {}).get("status") or "")
            invariant_id = str((invariant or {}).get("id") or "unknown")
            if status != "pass":
                blockers.append(f"invariant {invariant_id} is {status or 'missing'}")

        accepted = self._accepted_exceptions_by_path(artifact)
        for cluster in artifact.get("cluster_summary") or []:
            cluster_id = str((cluster or {}).get("cluster_id") or "unknown")
            state = str((cluster or {}).get("state") or "")
            artifact_path = str((cluster or {}).get("artifact_path") or "")
            if state == "block":
                blockers.append(f"cluster {cluster_id} blocks transition")
            elif state == "warn":
                if artifact_path and cluster_id in accepted.get(artifact_path, set()):
                    warnings.append(f"cluster {cluster_id} accepted as warn")
                else:
                    blockers.append(f"cluster {cluster_id} warns without accepted exception")
            elif state == "deferred":
                if self._deferred_accepted(artifact, cluster_id):
                    warnings.append(f"cluster {cluster_id} deferred to next phase")
                else:
                    blockers.append(f"cluster {cluster_id} deferred without next-phase acceptance")
            elif state in {"pass", "not_applicable"}:
                continue
            else:
                blockers.append(f"cluster {cluster_id} has invalid state: {state or 'missing'}")

        for blocker in artifact.get("blockers") or []:
            if blocker:
                blockers.append(f"unresolved blocker: {blocker}")

        raw_warnings = artifact.get("warnings") or []
        if raw_warnings:
            if not self._warnings_owned(raw_warnings):
                blockers.append("warnings require owner and residual risk")
            else:
                warnings.append("transition has owned warnings")

        deferred_items = artifact.get("deferred_items") or []
        if deferred_items:
            for item in deferred_items:
                if not self._deferred_item_accepted(item):
                    blockers.append("deferred item lacks owner/condition/accepted_by")
            if not any("deferred item lacks" in b for b in blockers):
                warnings.append("transition has accepted deferred items")

        self._validate_heartgate_coherence(artifact, blockers, warnings)
        self._validate_heartgate_coherence_requirement(artifact, blockers)
        self._validate_phase_exit_invariants(artifact, blockers)
        self._validate_artifact_integrity(artifact, blockers)
        self._validate_adaptive_proposal_package_gate(artifact, blockers)
        self._validate_convergence_budget_gate(artifact, blockers)
        self._validate_adaptive_plan_package_gate(artifact, blockers)
        self._validate_adaptive_execute_evidence_gate(artifact, blockers)
        self._validate_adaptive_verify_evidence_gate(artifact, blockers)
        self._validate_adaptive_resolve_closure_gate(artifact, blockers)
        self._validate_ppv_record(artifact, blockers)
        # Phase 2: per-transition artifact-structure checks.
        self._validate_intent_doc(artifact, blockers)
        self._validate_scope_artifact(artifact, blockers, warnings)
        self._validate_evidence_dispositions(artifact, blockers)
        self._validate_lessons_artifact(artifact, blockers)
        # Phase 3: plan-validation gate + run-registry overlap.
        self._validate_plan_validation_gate(artifact, blockers, warnings)
        self._validate_run_registry_overlap(artifact, blockers, warnings)

        declared_decision = str(artifact.get("decision") or "")
        if declared_decision == "block":
            blockers.append("transition artifact declares block")

        if blockers:
            return HeartgateDecision("block", "transition blocked", blockers, warnings)
        if declared_decision == "warn" or warnings:
            return HeartgateDecision(
                "warn", "transition passes with accepted warnings", [], warnings
            )
        return HeartgateDecision("pass", "transition passes", [], [])

    def forced_proposal_coverage_blockers(self, run_id: str) -> list[str]:
        """The ONE proposal-gate check that must hold on the FORCED transition path
        (``state_machine.handle_transition``), not only the agent-invoked
        ``validate_transition`` — closing the coverage half of node-15 residual #1
        ("the package gates aren't forced").

        Why only this check, forced: the forced ``plan_exit`` structural gate can
        only enforce intent coverage over REGISTERED scope_items. A package-selection
        run can declare a covered keyed scope module but reference it WITHOUT
        registering it, so projection sees nothing and a dropped intent escapes on a
        run that never calls ``validate_transition``. Forcing the full proposal
        package gate would demand every package artifact on every transition (the
        bare-transition ripple the structural gate deliberately avoids); forcing just
        the registration precondition closes the coverage bypass with no such ripple.

        Self-gating is on ENVELOPE PRESENCE, and the body is FAIL-CLOSED (a council
        review caught the earlier fail-open): it returns ``[]`` only when NO
        package-selection envelope file exists for ``run_id`` (a bare / ungoverned
        transition). Once an envelope IS present — i.e. the run is a governed
        package-selection PROPOSE — its ``scope`` concern MUST be ``covered`` by a
        non-empty keyed scope module that is REGISTERED in ``manifest.artifacts`` (or
        inherited), else this forced precondition BLOCKS. A garbled envelope, a
        ``not_applicable`` / markdown scope, or an unregistered keyed module all block
        here — closing the bypass where an agent skips ``validate_transition`` and
        simply declines to mark its scope covered (which would otherwise leave the
        plan_exit coverage gate with no scope_items to enforce). This mirrors the
        agent-invoked ``validate_adaptive_proposal_package_gate`` scope requirement,
        but forced and scope-only (no other package artifacts demanded → no
        bare-transition ripple).
        """
        selection_rel = f"proposals/{run_id}-package-selection.yaml"
        # Self-gate on FILE PRESENCE: no envelope -> bare/ungoverned transition -> skip.
        if not (self.governed_root / selection_rel).exists():
            return []
        prefix = f"forced_proposal_coverage[{run_id}]: package-selection envelope present, so"
        doc = self._load_yaml_under_root(selection_rel, [], "forced_proposal_coverage")
        if not isinstance(doc, Mapping):
            return [
                f"{prefix} it must parse as a mapping "
                "(a garbled envelope cannot bypass coverage)"
            ]
        core = doc.get("universal_core") if isinstance(doc.get("universal_core"), Mapping) else {}
        scope_concern = core.get("scope") if isinstance(core, Mapping) else None
        if not (
            isinstance(scope_concern, Mapping) and str(scope_concern.get("status")) == "covered"
        ):
            return [
                f"{prefix} its scope concern must be 'covered' by a keyed scope module "
                "(scope.in_scope:[{id,statement}]); not_applicable/markdown scope cannot "
                "bypass intent coverage on the forced path (D43 Option B / residual #1)"
            ]
        rel = str(scope_concern.get("artifact") or "")
        if not adaptive_gates._scope_concern_is_keyed(self, rel):
            return [
                f"{prefix} the covered scope artifact '{rel}' must declare a non-empty keyed "
                "scope.in_scope:[{id,statement}] (D43)"
            ]
        if rel not in self._registered_artifact_rels(run_id):
            return [
                f"{prefix} the keyed scope module '{rel}' must be registered in the run "
                "manifest so the forced plan_exit coverage gate can project its scope_items "
                "(D43 Option B / residual #1)"
            ]
        return []

    def forced_execute_evidence_blockers(self, run_id: str) -> list[str]:
        """The ONE execute-evidence precondition that must hold on the FORCED transition path
        (``state_machine.handle_transition`` EXECUTE->VERIFY), not only the agent-invoked
        ``validate_transition`` — extending the "force a ripple-free precondition" pattern of
        :meth:`forced_proposal_coverage_blockers` to the EXECUTE exit.

        Why only this precondition, forced: the forced ``execute_exit`` structural gate enforces
        checkpoint COVERAGE (checkpoints span the work units), but NOT that the standard-track
        Phase-Intent-Verification (PIV) evidence artifact exists — so a run that registers covering
        checkpoints but never authors a PIV can advance EXECUTE->VERIFY via ``handle_transition``,
        skipping the PIV the agent-invoked ``validate_adaptive_execute_evidence_gate`` demands. This
        forces JUST that PIV precondition. Forcing the gate's FULL artifact set (package dir,
        offline validation) would demand every execution artifact on every transition — the bare
        ripple the structural gate deliberately avoids (see
        :meth:`forced_proposal_coverage_blockers`); requiring only the PIV closes the bypass with no
        such ripple.

        Self-gating is on the GOVERNED-EXECUTE marker — the presence of ANY execution checkpoint
        ``executions/{run_id}-checkpoint-*.yaml`` (NOT only ``-001``: a council probe showed a run
        whose covering checkpoint is ``-002`` would otherwise skip the PIV demand, MOVING the bypass
        rather than closing it; checkpoints are ``{seq}``-parametrized). No checkpoint -> a bare /
        ungoverned EXECUTE->VERIFY -> ``[]`` (no ripple). Track relaxation is REPLICATED from the
        adaptive gate (ADR-0016): a GOAL-DRIVEN run is satisfied by a coherent checkpoint manifest
        in lieu of the PIV, delegating to the same ``_validate_goal_driven_checkpoint_gate`` the
        agent path uses. The track is read from the run manifest; relabeling a standard run as
        goal-driven is not a free pass (it swaps the PIV demand for the manifest-coherence demand) —
        the track-vs-TRIAGE cross-check lives in the PROPOSE->PLAN convergence-budget gate.
        Fail-closed: once a checkpoint is present, a standard-track PIV that is missing,
        unparseable, of wrong ``kind``, or whose ``run_id`` mismatches BLOCKS (the adaptive
        PIV-identity check, forced).
        """
        executions = self.governed_root / "executions"
        # Self-gate on the governed-execute marker — ANY checkpoint, not the -001 literal.
        if not any(executions.glob(f"{run_id}-checkpoint-*.yaml")):
            return []
        # Track relaxation (ADR-0016): goal-driven is satisfied by a coherent manifest, not a PIV.
        if self._run_track(run_id) == "goal-driven":
            blockers: list[str] = []
            self._validate_goal_driven_checkpoint_gate(run_id, blockers)
            return blockers
        prefix = f"forced_execute_evidence[{run_id}]: governed execute (checkpoint registered), so"
        piv_rel = f"plans/{run_id}-piv.yaml"
        if not (self.governed_root / piv_rel).exists():
            return [f"{prefix} a PIV ({piv_rel}) must be present before EXECUTE->VERIFY"]
        doc = self._load_yaml_under_root(piv_rel, [], "forced_execute_evidence")
        if not isinstance(doc, Mapping):
            return [f"{prefix} the PIV ({piv_rel}) must parse as a mapping"]
        # PIV-IDENTITY (mirror the adaptive gate, scope-minimal): a placeholder file cannot satisfy
        # the precondition — the contract kind + run_id must match.
        if doc.get("kind") != "uacp.phase_intent_verification_contract":
            return [f"{prefix} the PIV kind must be uacp.phase_intent_verification_contract"]
        if doc.get("run_id") != run_id:
            return [f"{prefix} the PIV run_id must match the run ({run_id})"]
        return []

    def validate_transition_file(self, path: str | Path) -> HeartgateDecision:
        raw_path = Path(path)
        if not raw_path.is_absolute():
            raw_path = self.governed_root / raw_path
        if yaml is None:
            raise HeartgateError("PyYAML is required to load transition artifact")
        artifact = yaml.safe_load(raw_path.read_text(encoding="utf-8"))
        if not isinstance(artifact, dict):
            return HeartgateDecision(
                "block", "transition artifact must be a YAML mapping", ["invalid artifact"]
            )
        return self.validate_transition(artifact)

    def validate_closure(self, run_id: str) -> HeartgateDecision:
        """Run the computed engines as the RESOLVE / closure gate for a run.

        This is the operator-facing closure check: it sweeps all five computed
        engines (coherence, ledger_integrity, scope_conformance,
        evidence_completeness, deferral_completeness) over the run's emitted
        state and maps their violations onto a :class:`HeartgateDecision` — any
        ``severity == "block"`` violation becomes a blocker, ``"warn"`` becomes a
        warning. Decision is ``"block"`` if any blockers, else ``"warn"`` if any
        warnings, else ``"pass"``.

        Contract / preconditions: ``validate_closure`` expects a FINALIZED run —
        ``finalized_at`` set on the manifest and the closure/lessons artifact
        registered. The engines' terminal checks (coherence C4, evidence
        ``EV_RESOLVED_WITHOUT_EVIDENCE``, deferral ``DF_DEFERRAL_DROPPED_AT_RESOLVE``)
        assume the closed/resolved state; calling it on a run that has not yet
        been finalized would false-positive — which is why ``handle_finalize``
        sets ``finalized_at`` FIRST, then runs this gate, reverting if it blocks.
        It is auto-called on the live RESOLVE path: ``state_machine.handle_finalize``
        runs it (via ``_run_closure_gate``) so a run cannot be stamped resolved
        while the engine sweep finds blockers. Also exposed to the RESOLVE
        runtime (and the future MCP ``uacp_validate_closure`` tool).

        Never raises: the engines themselves never raise, and the whole sweep is
        wrapped defensively so a closure check can never crash the kernel — an
        unexpected failure is surfaced as a single block decision.
        """
        try:
            # Lazy import: keeps core.py's module load free of the engines
            # package (which bootstraps sys.path on import) for adapters that
            # never run a closure check. No import cycle — engines depend on
            # state_machine, never on core.
            violations = run_all_engines(self.uacp_root, run_id)
            violations = self._dedupe_scope_registry_disagreement(violations)

            blockers: list[str] = []
            warnings: list[str] = []
            for v in violations:
                line = f"{v.code}: {v.message}"
                if v.severity == "block":
                    blockers.append(line)
                else:
                    warnings.append(line)

            if blockers:
                return HeartgateDecision(
                    "block", "closure blocked by computed engines", blockers, warnings
                )
            if warnings:
                return HeartgateDecision(
                    "warn", "closure passes with engine warnings", [], warnings
                )
            return HeartgateDecision("pass", "closure passes all computed engines", [], [])
        except Exception as exc:  # defensive: a closure check must never crash the kernel
            return HeartgateDecision(
                "block",
                "closure check failed unexpectedly",
                [f"VALIDATE_CLOSURE_CRASHED: {type(exc).__name__}: {exc}"],
                [],
            )

    @staticmethod
    def _dedupe_scope_registry_disagreement(violations: list) -> list:
        """Collapse the documented overlap between scope_conformance's
        ``SC_SCOPE_REGISTRY_DISAGREE`` and coherence's ``C6_WRITE_PATHS_DISAGREE``.

        Both engines fire on the same scope-vs-registry write_paths divergence.
        When a coherence C6 finding is present we drop the SC findings that are
        about the SAME write_paths divergence (prefer the coherence C6 line),
        so the operator sees ONE finding for one problem. SC findings about a
        distinct concern (e.g. ``scope_artifact_path`` mismatch) are preserved.
        """
        has_c6 = any(v.code == "C6_WRITE_PATHS_DISAGREE" for v in violations)
        if not has_c6:
            return violations
        kept: list = []
        for v in violations:
            if v.code == "SC_SCOPE_REGISTRY_DISAGREE" and "write_paths" in v.message:
                continue  # collapsed into the C6 finding
            kept.append(v)
        return kept

    def _validate_heartgate_coherence(
        self, artifact: Mapping[str, Any], blockers: list[str], warnings: list[str]
    ) -> None:
        coherence.validate_heartgate_coherence(self, artifact, blockers, warnings)

    def _artifact_path_exists(self, artifact_path: str) -> bool:
        try:
            path = Path(artifact_path)
            if not path.is_absolute():
                path = self.governed_root / path
            resolved = path.resolve()
            root = self.governed_root.resolve()
            if resolved != root and root not in resolved.parents:
                return False
            return resolved.exists()
        except Exception:
            return False

    def _registered_artifact_rels(self, run_id: str) -> set[str]:
        """The run-root-relative artifact paths REGISTERED in the run manifest's
        ``artifacts`` map — i.e. exactly what :mod:`engines.manifest.projection`
        loads into the coverage graph. Package gates use this to require that a
        referenced coverage artifact (the keyed scope module; the PIV) be
        *registered*, not merely present on disk — so the forced phase-exit graph
        gate (D35 ``plan_exit``) projects its scope_items/work_units and the
        dropped-intent detector can BIND (D43 Option B). A missing/garbled manifest
        yields the empty set (caller treats "not registered" as a blocker —
        fail-closed)."""
        loaded = io_loaders.load_manifest(self.uacp_root, run_id)
        if loaded.error is not None or loaded.value is None:
            return set()
        rels: set[str] = set()
        # Match graph projection's load set EXACTLY (projection._load_and_project reads
        # artifacts + inherited_artifacts). A goal-chained child REUSES a parent's
        # registered scope module / PIV via inherited_artifacts; counting only `artifacts`
        # would false-block such a child at the registration precondition even though
        # projection sees (and the coverage gate verifies) the inherited scope.
        for field in ("artifacts", "inherited_artifacts"):
            m = loaded.value.raw.get(field)
            if isinstance(m, dict):
                rels |= {str(v) for v in m.values()}
        return rels

    def _validate_checkpoint_entry(self, entry: Any, blockers: list[str]) -> None:
        goal_driven.validate_checkpoint_entry(self, entry, blockers)

    def _heartgate_coherence_rule(self) -> Mapping[str, Any]:
        return coherence.heartgate_coherence_rule(self)

    def _validate_heartgate_coherence_requirement(
        self, artifact: Mapping[str, Any], blockers: list[str]
    ) -> None:
        coherence.validate_heartgate_coherence_requirement(self, artifact, blockers)

    def _validate_phase_exit_invariants(
        self, artifact: Mapping[str, Any], blockers: list[str]
    ) -> None:
        """Enforce phase_exit_invariants from config (A3.1: delegates to
        validators.phase_exit; logic + tests unchanged)."""
        phase_exit.validate_phase_exit_invariants(
            artifact,
            stages=self.stages,
            uacp_root=self.uacp_root,
            governed_root=self.governed_root,
            blockers=blockers,
        )

    def _validate_artifact_integrity(
        self, artifact: Mapping[str, Any], blockers: list[str]
    ) -> None:
        """Hardening #6: run the artifact-integrity (SHA-256 watermark) check at
        EVERY transition, not only at terminal closure, so an out-of-band tamper of
        a recorded artifact is caught at the boundary instead of being swapped back
        before RESOLVE. No-op on runs with no watermark index (legacy / non-governed-
        writer runs). The engine never raises."""
        run_id = str(artifact.get("run_id") or "")
        if not run_id:
            return

        for v in validate_artifact_integrity(self.uacp_root, run_id):
            if v.severity == "block":
                blockers.append(f"{v.code}: {v.message}")

    def _validate_adaptive_proposal_package_gate(
        self, artifact: Mapping[str, Any], blockers: list[str]
    ) -> None:
        adaptive_gates.validate_adaptive_proposal_package_gate(self, artifact, blockers)

    def _run_track(self, run_id: str) -> str:
        return goal_driven.run_track(self, run_id)

    def _goal_checkpoint_count(self, goal_id: str) -> int:
        return goal_driven.goal_checkpoint_count(self, goal_id)

    def _load_convergence_budget(self, run_id: str):
        return goal_driven.load_convergence_budget(self, run_id)

    def _triage_track(self, run_id: str) -> str:
        return goal_driven.triage_track(self, run_id)

    def _validate_convergence_budget_gate(
        self, artifact: Mapping[str, Any], blockers: list[str]
    ) -> None:
        goal_driven.validate_convergence_budget_gate(self, artifact, blockers)

    def _load_checkpoint_manifest(self, run_id: str) -> list[Mapping[str, Any]]:
        return goal_driven.load_checkpoint_manifest(self, run_id)

    def _validate_goal_driven_checkpoint_gate(self, run_id: str, blockers: list[str]) -> bool:
        return goal_driven.validate_goal_driven_checkpoint_gate(self, run_id, blockers)

    def _validate_adaptive_plan_package_gate(
        self, artifact: Mapping[str, Any], blockers: list[str]
    ) -> None:
        adaptive_gates.validate_adaptive_plan_package_gate(self, artifact, blockers)

    def _validate_plan_na(self, artifact: str, label: str, item: Any, blockers: list[str]) -> None:
        if not isinstance(item, Mapping):
            blockers.append(f"adaptive_plan_package_gate: {label} in {artifact} must be a mapping")
            return
        for field_name in PLAN_NOT_APPLICABLE_REQUIRED_FIELDS:
            if item.get(field_name) in (None, ""):
                blockers.append(f"adaptive_plan_package_gate: {label} missing {field_name}")

    def _validate_package_na(
        self, artifact: str, label: str, item: Any, blockers: list[str]
    ) -> None:
        if not isinstance(item, Mapping):
            blockers.append(
                f"adaptive_proposal_package_gate: {label} in {artifact} must be a mapping"
            )
            return
        for field_name in PROPOSAL_NOT_APPLICABLE_REQUIRED_FIELDS:
            if item.get(field_name) in (None, ""):
                blockers.append(f"adaptive_proposal_package_gate: {label} missing {field_name}")

    def _load_yaml_under_root(
        self, rel_path: str, blockers: list[str], label: str
    ) -> Mapping[str, Any] | None:
        # Adapter (A2): the load logic now lives in engines/io under the Loaded[T]
        # contract; this maps a Loaded error onto the gate's blocker list,
        # preserving the exact messages. The yaml-None guard stays here — core
        # tolerates a missing PyYAML, whereas the io layer hard-imports it.
        if yaml is None:
            blockers.append(f"{label} requires PyYAML")
            return None
        result = io_loaders.load_yaml_under_root(self.uacp_root, rel_path)
        if result.error is not None:
            blockers.append(f"{label}: {result.error}")
            return None
        return result.value

    def _dir_under_root_exists(self, rel_path: str) -> bool:
        try:
            p = (self.governed_root / rel_path).resolve()
            root = self.governed_root.resolve()
            return p.is_dir() and (p == root or root in p.parents)
        except Exception:
            return False

    def _offline_validate_artifacts(
        self, rel_paths: list[str], blockers: list[str], label: str
    ) -> None:
        """Run the canonical artifact validator in-process for runtime gates.

        Heartgate performs transition-time checks; the offline validator owns the
        deeper artifact semantics. Importing and calling it here prevents drift
        where Heartgate only checks artifact presence while validator catches the
        real semantic false-pass.
        """
        validator_path = self.uacp_root / "scripts" / "validate_uacp_artifacts.py"
        if not validator_path.exists():
            blockers.append(
                f"{label}: validator script missing: scripts/validate_uacp_artifacts.py"
            )
            return
        try:
            spec = importlib.util.spec_from_file_location("uacp_validate_runtime", validator_path)
            if spec is None or spec.loader is None:
                blockers.append(f"{label}: unable to load validator module")
                return
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            issues: list[str] = []
            configs = module.validate_configs(self.uacp_root, issues)
            module.validate_transition_config_consistency(configs, issues)
            phase_config = configs.get("config/phase-transitions.yaml") or {}
            # The offline validator (validate_uacp_artifacts.py) is now .uacp/-aware:
            # it reads config flat under the project root but resolves state/artifact
            # paths under base_dir(root). So the artifact `path` Heartgate loads here
            # resolves under governed_root, while validate_configs + the validate_*
            # kwargs keep passing the project root (self.uacp_root) — the validator
            # base_dir's internally. (Council C-A: keeps the in-process path correct
            # on a migrated repo instead of fail-closed BLOCKing real transitions.)
            for rel in rel_paths:
                path = (self.governed_root / rel).resolve()
                root = self.governed_root.resolve()
                if path != root and root not in path.parents:
                    issues.append(f"BLOCK {label}: artifact path escapes UACP root: {rel}")
                    continue
                obj = module.require_map(module.load_yaml(path), path)
                kind = obj.get("kind", "")
                module.validate_finding_states(path, obj, issues)
                if kind == "uacp.phase_transition":
                    module.validate_phase_transition(
                        path, obj, phase_config, issues, root=self.uacp_root
                    )
                elif kind == "uacp.phase_intent_verification_contract":
                    module.validate_piv_contract(path, obj, issues, root=self.uacp_root)
                elif kind == "uacp.execution_checkpoint":
                    module.validate_execution_checkpoint(path, obj, issues, root=self.uacp_root)
                elif kind == "uacp.piv_assessment":
                    module.validate_piv_assessment(path, obj, issues, root=self.uacp_root)
                elif kind == "uacp.verification_package":
                    module.validate_verify_package_selection(path, obj, issues, root=self.uacp_root)
                elif kind == "uacp.verify_resolve_readiness":
                    module.validate_verify_resolve_readiness(path, obj, issues, root=self.uacp_root)
                elif kind == "uacp.resolve_package":
                    module.validate_resolve_package_selection(
                        path, obj, issues, root=self.uacp_root
                    )
                elif kind == "uacp.resolve_closure":
                    module.validate_resolve_closure(path, obj, issues, root=self.uacp_root)
            for issue in issues:
                if str(issue).startswith("BLOCK"):
                    blockers.append(f"{label}: {issue}")
        except Exception as exc:
            blockers.append(f"{label}: validator execution failed: {type(exc).__name__}: {exc}")

    def _validate_adaptive_execute_evidence_gate(
        self, artifact: Mapping[str, Any], blockers: list[str]
    ) -> None:
        adaptive_gates.validate_adaptive_execute_evidence_gate(self, artifact, blockers)

    def _validate_goal_driven_closure_gate(self, run_id: str, blockers: list[str]) -> bool:
        return goal_driven.validate_goal_driven_closure_gate(self, run_id, blockers)

    def _final_checkpoint_entry(self, run_id: str):
        return goal_driven.final_checkpoint_entry(self, run_id)

    def _run_goal_id(self, run_id: str) -> str:
        return goal_driven.run_goal_id(self, run_id)

    def _validate_adaptive_verify_evidence_gate(
        self, artifact: Mapping[str, Any], blockers: list[str]
    ) -> None:
        adaptive_gates.validate_adaptive_verify_evidence_gate(self, artifact, blockers)

    def _validate_adaptive_resolve_closure_gate(
        self, artifact: Mapping[str, Any], blockers: list[str]
    ) -> None:
        adaptive_gates.validate_adaptive_resolve_closure_gate(self, artifact, blockers)

    def _ppv_rule(self) -> Mapping[str, Any]:
        return ppv.ppv_rule(self)

    def _validate_ppv_record(self, artifact: Mapping[str, Any], blockers: list[str]) -> None:
        ppv.validate_ppv_record(self, artifact, blockers)

    def _validate_intent_doc(self, artifact: Mapping[str, Any], blockers: list[str]) -> None:
        manifest_validators.validate_intent_doc(self, artifact, blockers)

    def _validate_scope_artifact(
        self, artifact: Mapping[str, Any], blockers: list[str], warnings: list[str]
    ) -> None:
        manifest_validators.validate_scope_artifact(self, artifact, blockers, warnings)

    def _validate_evidence_dispositions(
        self, artifact: Mapping[str, Any], blockers: list[str]
    ) -> None:
        manifest_validators.validate_evidence_dispositions(self, artifact, blockers)

    def _tool_path_capabilities(self) -> dict[str, list[str]]:
        # Delegating wrapper (C3a carve): moved to engines.manifest.validators with
        # validate_scope_artifact, but external callers remain (scripts/phase2_verify.py,
        # scripts/phase3_verify.py call hg._tool_path_capabilities()). Kept so the carve is
        # behaviour-preserving for them — a regression the suite missed (those scripts aren't
        # pytest-run) and Codex PR#5 caught (the A3 repo-wide-caller-search lesson again).
        return manifest_validators._tool_path_capabilities(self)

    def _plan_validation_gate_rule(self) -> Mapping[str, Any]:
        return plan_validation.plan_validation_gate_rule(self)

    def _validate_plan_validation_gate(
        self, artifact: Mapping[str, Any], blockers: list[str], warnings: list[str] | None = None
    ) -> None:
        plan_validation.validate_plan_validation_gate(self, artifact, blockers, warnings)

    @staticmethod
    def _canon_write_path(p: Any) -> str:
        # Re-export the run_registry path canonicalizer: state.py reuses it as
        # ``Heartgate._canon_write_path`` for its own overlap pre-check (A3.6).
        return run_registry._canon_write_path(p)

    def _run_registry_rule(self) -> Mapping[str, Any]:
        return run_registry.run_registry_rule(self)

    def _validate_run_registry_overlap(
        self, artifact: Mapping[str, Any], blockers: list[str], warnings: list[str]
    ) -> None:
        return run_registry.validate_run_registry_overlap(self, artifact, blockers, warnings)

    def _validate_lessons_artifact(self, artifact: Mapping[str, Any], blockers: list[str]) -> None:
        manifest_validators.validate_lessons_artifact(self, artifact, blockers)

    def _transition_allowed(self, from_phase: str, to_phase: str) -> bool:
        stage = self.stages.get(from_phase) or {}
        exits = stage.get("exits_to") or []
        return to_phase in exits

    def _accepted_exceptions_by_path(self, artifact: Mapping[str, Any]) -> dict[str, set[str]]:
        accepted: dict[str, set[str]] = {}
        for item in artifact.get("accepted_exceptions") or []:
            if not isinstance(item, Mapping):
                continue
            artifact_path = str(item.get("artifact_path") or "")
            cluster_id = str(item.get("cluster_id") or "")
            if not artifact_path or not cluster_id:
                continue
            if not (
                item.get("id")
                and item.get("accepted_by")
                and item.get("owner")
                and item.get("rationale")
                and item.get("next_phase_acceptance")
            ):
                continue
            run_id = str(artifact.get("run_id") or "")
            if not artifact_path.startswith(("verification/", "resolutions/")):
                continue
            if run_id and not artifact_path.startswith(
                (f"verification/{run_id}", f"resolutions/{run_id}")
            ):
                continue
            if not self._artifact_path_exists(artifact_path):
                continue
            accepted.setdefault(artifact_path, set()).add(cluster_id)
        return accepted

    def _deferred_accepted(self, artifact: Mapping[str, Any], cluster_id: str) -> bool:
        for item in artifact.get("deferred_items") or []:
            if not isinstance(item, Mapping):
                continue
            if item.get("cluster_id") and str(item.get("cluster_id")) != cluster_id:
                continue
            if self._deferred_item_accepted(item):
                return True
        return False

    def _deferred_item_accepted(self, item: Any) -> bool:
        if not isinstance(item, Mapping):
            return False
        return bool(
            item.get("id")
            and item.get("cluster_id")
            and item.get("owner")
            and item.get("condition")
            and item.get("accepted_by")
            and item.get("next_phase_acceptance")
        )

    def _warnings_owned(self, warnings: Any) -> bool:
        for item in warnings:
            if not isinstance(item, Mapping):
                return False
            if not (item.get("owner") and item.get("residual_risk")):
                return False
        return True
