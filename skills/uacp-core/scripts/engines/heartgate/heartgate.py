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

from config import base_dir, get_config
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

from . import goal_driven
from .models import HeartgateDecision, HeartgateError
from .validators import adaptive_gates, coherence, phase_exit, plan_validation, ppv, run_registry
from .validators.helpers import _is_safe_run_id  # re-exported by core; many internal uses

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
        been finalized would false-positive. It is invoked by the RESOLVE flow /
        runtime (and exposed by the future MCP ``uacp_validate_closure`` tool) —
        it is NOT auto-called inside ``state_machine.handle_finalize`` to keep
        the state machine decoupled from the kernel.

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
        """Phase 2.3: TRIAGE->PROPOSE requires proposals/{run_id}-intent.md
        with the four required sections.
        """
        schema = self.artifact_schemas.get("intent") or {}
        required_transition = str(schema.get("required_for_transition") or "")
        if not required_transition:
            return
        from_phase = str(artifact.get("from_phase") or "")
        to_phase = str(artifact.get("to_phase") or "")
        if f"{from_phase}->{to_phase}" != required_transition:
            return
        run_id = str(artifact.get("run_id") or "")
        if not _is_safe_run_id(run_id):
            blockers.append("intent doc: unsafe or missing run_id")
            return
        template = str(schema.get("path_template") or "proposals/{run_id}-intent.md")
        path = self.governed_root / template.replace("{run_id}", run_id)
        if not path.exists():
            blockers.append(f"intent doc missing: {path.relative_to(self.governed_root)}")
            return
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            blockers.append(f"intent doc unreadable: {type(exc).__name__}")
            return
        # Phase 3 hardening (pc_p2_t5 + SKEP-004): anchored per-line regex;
        # skip both ``` and ~~~ CommonMark fences AND any leading YAML
        # frontmatter delimited by `---` at the top of the file.
        required_sections = list(schema.get("required_sections") or [])
        import re as _re

        lines = text.splitlines()
        # Detect leading YAML frontmatter and skip it entirely.
        skip_until = 0
        if lines and lines[0].strip() == "---":
            for idx in range(1, len(lines)):
                if lines[idx].strip() == "---":
                    skip_until = idx + 1
                    break
        in_fence = False
        present: set[str] = set()
        for ln_no, raw_line in enumerate(lines):
            if ln_no < skip_until:
                continue
            line = raw_line.rstrip()
            stripped = line.lstrip()
            # CommonMark recognizes both ``` and ~~~ as code fences.
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            m = _re.match(r"^(#{1,2})\s+(.+?)\s*$", line)
            if not m:
                continue
            raw_header = m.group(2).strip()
            # Accept "Header" and "Header: free text" (split on first colon).
            header_main = raw_header.split(":", 1)[0].strip()
            for section in required_sections:
                if raw_header == section or header_main == section:
                    present.add(section)
        for section in required_sections:
            if section not in present:
                blockers.append(f"intent doc missing required section: '{section}'")

    def _validate_scope_artifact(
        self, artifact: Mapping[str, Any], blockers: list[str], warnings: list[str]
    ) -> None:
        """Phase 2.1: PLAN->EXECUTE requires plans/{run_id}-scope.yaml.
        Validates required fields, cross-checks write_paths against Layer B
        allowed_tools (pc_p1_gov_2).
        """
        schema = self.artifact_schemas.get("scope") or {}
        required_transition = str(schema.get("required_for_transition") or "")
        if not required_transition:
            return
        from_phase = str(artifact.get("from_phase") or "")
        to_phase = str(artifact.get("to_phase") or "")
        if f"{from_phase}->{to_phase}" != required_transition:
            return
        run_id = str(artifact.get("run_id") or "")
        if not _is_safe_run_id(run_id):
            blockers.append("scope artifact: unsafe or missing run_id")
            return
        template = str(schema.get("path_template") or "plans/{run_id}-scope.yaml")
        path = self.governed_root / template.replace("{run_id}", run_id)
        if not path.exists():
            blockers.append(f"scope artifact missing: {path.relative_to(self.governed_root)}")
            return
        if yaml is None:
            blockers.append("scope artifact requires PyYAML to validate")
            return
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:
            blockers.append(f"scope artifact unparseable: {type(exc).__name__}")
            return
        if not isinstance(data, Mapping):
            blockers.append("scope artifact must be a YAML mapping")
            return
        for field_name in schema.get("required_fields") or []:
            if field_name not in data:
                blockers.append(f"scope artifact missing required field: {field_name}")
        # Cross-check write_paths against EXECUTE Layer B (pc_p1_gov_2).
        write_paths = data.get("write_paths") or []
        if not isinstance(write_paths, list):
            blockers.append("scope.write_paths must be a list")
            return
        # Phase 3 R2 (SKEP-R1-004): empty write_paths is "containment by
        # absence" — both overlap detection and reachability cross-check
        # silently no-op on empty lists, allowing a run to declare no writes,
        # pass governance, then write through governed tools without bound.
        # Require either at least one write path OR an explicit
        # no_writes_intended sentinel that the scope author has acknowledged.
        if len(write_paths) == 0 and not bool(data.get("no_writes_intended")):
            blockers.append(
                "scope.write_paths is empty (write authority cannot be inferred from absence; "
                "either declare at least one path or set 'no_writes_intended: true')"
            )
            return
        execute_stage = self.stages.get("execute") or {}
        allowed_tools = list((execute_stage or {}).get("allowed_tools") or [])
        tool_path_capabilities = self._tool_path_capabilities()
        # SKEP-008 remediation: a positive prefix match is not enough — some
        # handlers refuse sub-paths of an allowed prefix. Honor those refusals
        # here so a scope can't launder unreachable paths.
        # Slice 4a: handler_refusals moved from artifact-schemas.yaml to
        # config/uacp.toml [scope.handler_refusals] (operator-tunable knob).
        try:
            cfg_raw = get_config(self.uacp_root).model_dump()
            handler_refusals = (cfg_raw.get("scope") or {}).get("handler_refusals") or {}
        except Exception:
            handler_refusals = {}
        if not isinstance(handler_refusals, Mapping):
            handler_refusals = {}
        for wp in write_paths:
            wp_str = str(wp)
            reachable = False
            for tool in allowed_tools:
                prefixes = tool_path_capabilities.get(tool) or []
                if not any(wp_str.startswith(pfx) or wp_str == pfx.rstrip("/") for pfx in prefixes):
                    continue
                # Apply per-tool refusals (e.g. uacp_state_write refuses state/gate-ledger/).
                refused = handler_refusals.get(tool) or []
                if isinstance(refused, list) and any(
                    isinstance(r, str) and r and (wp_str == r.rstrip("/") or wp_str.startswith(r))
                    for r in refused
                ):
                    continue
                reachable = True
                break
            if not reachable and self._self_patch_authorizes_path(data, wp_str, blockers):
                reachable = True
            if not reachable:
                blockers.append(
                    f"scope.write_paths cross-check: '{wp_str}' is not reachable "
                    "by any execute-phase allowed_tool"
                )

    def _self_patch_authorizes_path(
        self, scope: Mapping[str, Any], write_path: str, blockers: list[str]
    ) -> bool:
        """Narrow bootstrap escape hatch for UACP self-repair paths.

        This does not make terminal/patch a general governed writer. It only lets
        Heartgate accept specific UACP self-patch paths when the scope carries an
        explicit authority block with owner, rollback, and verification duties.
        """
        auth = scope.get("self_patch_write_authority")
        if not isinstance(auth, Mapping) or not bool(auth.get("enabled")):
            return False
        for field_name in (
            "reason",
            "authority_artifact",
            "owner",
            "rollback_path",
            "verification_obligations",
        ):
            if auth.get(field_name) in (None, "", []):
                blockers.append(f"self_patch_write_authority missing {field_name}")
                return False
        obligations = auth.get("verification_obligations")
        if not isinstance(obligations, list) or not all(
            isinstance(item, str) and item.strip() for item in obligations
        ):
            blockers.append(
                "self_patch_write_authority.verification_obligations must be a "
                "non-empty list of strings"
            )
            return False
        allowed = auth.get("allowed_prefixes") or [
            "skills/devops/uacp/",
            "scripts/",
            "runtime-adapters/",
        ]
        if not isinstance(allowed, list):
            blockers.append("self_patch_write_authority.allowed_prefixes must be a list")
            return False
        safe_prefixes = {"skills/devops/uacp/", "scripts/", "runtime-adapters/"}
        cleaned = [
            str(prefix) for prefix in allowed if isinstance(prefix, str) and prefix in safe_prefixes
        ]
        if not cleaned:
            blockers.append("self_patch_write_authority has no safe allowed_prefixes")
            return False
        return any(write_path.startswith(prefix) for prefix in cleaned)

    def _tool_path_capabilities(self) -> dict[str, list[str]]:
        """Path prefixes each governed writer tool can reach.

        Slice 4a: the canonical source is now ``config/uacp.toml [scope.tool_path_capabilities]``
        (operator-tunable). Previously read from
        ``config/artifact-schemas.yaml#cross_checks.scope_write_paths_vs_layer_b.tool_path_capabilities``
        via ``self.artifact_schemas``. Schemas are codified in engines.domain; the
        operator knobs moved to uacp.toml so project operators can tune them without
        touching kernel code.

        Shell/exec surfaces are deliberately absent — they target the workspace,
        not UACP_ROOT, and do not satisfy UACP-rooted scope.write_paths (F1).

        Phase 3 hardening (pc_p2_n1): drop prefixes that are empty or the
        literal "*" so a future config-author mistake cannot accidentally
        wildcard-match every write_path.

        Fail-closed default: if the config section is missing or malformed,
        return an empty mapping so every write_path is unreachable.
        """
        try:
            cfg_raw = get_config(self.uacp_root).model_dump()
            caps = (cfg_raw.get("scope") or {}).get("tool_path_capabilities") or {}
        except Exception:
            caps = {}
        if not isinstance(caps, Mapping):
            return {}
        # SKEP-007 remediation: schema metadata keys (description, purpose, notes,
        # documentation) must never be loaded as writer tools. Sibling fields are
        # legitimate metadata, not policy.
        metadata_keys = {"description", "purpose", "notes", "documentation"}
        # SKEP-003 / TECH-004 remediation: reject footgun prefixes that would
        # collapse path-segment boundaries (bare wildcards, root, dot-relative).
        forbidden_prefixes = {"", "*", "**", "/", ".", "..", "./", "../"}
        result: dict[str, list[str]] = {}
        for tool, prefixes in caps.items():
            if not isinstance(tool, str) or tool in metadata_keys:
                continue
            if isinstance(prefixes, list):
                cleaned = [
                    str(p)
                    for p in prefixes
                    if isinstance(p, str) and str(p).strip() not in forbidden_prefixes
                ]
            elif isinstance(prefixes, str) and prefixes.strip() not in forbidden_prefixes:
                cleaned = [prefixes]
            else:
                cleaned = []
            if cleaned:
                result[tool] = cleaned
        return result

    def _validate_evidence_dispositions(
        self, artifact: Mapping[str, Any], blockers: list[str]
    ) -> None:
        """Phase 2.2: VERIFY->RESOLVE requires verified-facts + assumptions
        pair files for each required cluster. Pending assumptions without
        owner/next_phase_obligation block.
        """
        schema = self.artifact_schemas.get("evidence_disposition") or {}
        required_transition = str(schema.get("required_for_transition") or "")
        if not required_transition:
            return
        from_phase = str(artifact.get("from_phase") or "")
        to_phase = str(artifact.get("to_phase") or "")
        if f"{from_phase}->{to_phase}" != required_transition:
            return
        run_id = str(artifact.get("run_id") or "")
        if not _is_safe_run_id(run_id):
            blockers.append("evidence_disposition: unsafe or missing run_id")
            return
        cluster_summary = artifact.get("cluster_summary") or []
        if not isinstance(cluster_summary, list):
            return
        # Phase 3 (pc_p2_t3): empty cluster_summary at VERIFY->RESOLVE is a block.
        # If a run truly has no clusters to verify, it must declare that
        # explicitly elsewhere (handled_findings_chain or accepted_exceptions);
        # silent zero-cluster passage is not acceptable for traceable state.
        handled_chain = artifact.get("handled_findings_chain") or []
        accepted_exc = artifact.get("accepted_exceptions") or []

        # Phase 3 R2 (SKEP-R1-002): escape-hatch presence is not sufficient;
        # entries must be non-empty mappings with the documented shape.
        # Garbage lists ([None, {}, ""]) no longer satisfy the escape hatch.
        def _valid_handled(c: Any) -> bool:
            if not isinstance(c, Mapping):
                return False
            ofid = c.get("original_finding_id") or c.get("finding_id")
            klass = c.get("handling_classification") or c.get("classification")
            return bool(ofid) and bool(klass)

        def _valid_exception(e: Any) -> bool:
            if not isinstance(e, Mapping):
                return False
            return (
                bool(e.get("artifact_path")) and bool(e.get("owner")) and bool(e.get("rationale"))
            )

        handled_valid = isinstance(handled_chain, list) and any(
            _valid_handled(c) for c in handled_chain
        )
        exc_valid = isinstance(accepted_exc, list) and any(
            _valid_exception(e) for e in accepted_exc
        )
        has_escape_hatch = handled_valid or exc_valid
        if len(cluster_summary) == 0:
            if not has_escape_hatch:
                blockers.append(
                    "evidence_disposition: cluster_summary is empty at VERIFY->RESOLVE "
                    "(must declare at least one cluster or non-empty "
                    "handled_findings_chain/accepted_exceptions)"
                )
            return
        # Phase 3 R1 (SKEP-006): a run cannot pass VERIFY->RESOLVE by declaring
        # every cluster as not_applicable/deferred. At least one cluster must
        # be in a real verification state, OR an escape hatch must be present.
        non_na_count = 0
        for c in cluster_summary:
            if isinstance(c, Mapping):
                st = str(c.get("state") or "")
                if st and st not in {"not_applicable", "deferred"}:
                    non_na_count += 1
        if non_na_count == 0 and not has_escape_hatch:
            blockers.append(
                "evidence_disposition: all clusters are not_applicable/deferred and no "
                "handled_findings_chain or accepted_exceptions declared (silent skip not allowed)"
            )
            return
        paired = schema.get("paired_paths") or {}
        facts_tmpl = str(paired.get("verified_facts") or "")
        assumptions_tmpl = str(paired.get("assumptions") or "")
        if not facts_tmpl or not assumptions_tmpl:
            return
        for cluster in cluster_summary:
            if not isinstance(cluster, Mapping):
                continue
            cluster_id = str(cluster.get("cluster_id") or "")
            state = str(cluster.get("state") or "")
            if not cluster_id or state in {"not_applicable", "deferred"}:
                continue
            # Phase 2 F3 remediation: file existence is insufficient; each file
            # must contain at least the documented table header (Fact / Disposition).
            cross = self.artifact_schemas.get("cross_checks") or {}
            minc = cross.get("evidence_disposition_minimum_content") or {}
            facts_req = str(minc.get("verified_facts_required_header_substring") or "")
            assump_req = str(minc.get("assumptions_required_header_substring") or "")
            for tmpl, label, required_substring in (
                (facts_tmpl, "verified-facts", facts_req),
                (assumptions_tmpl, "assumptions", assump_req),
            ):
                rel = tmpl.replace("{run_id}", run_id).replace("{cluster}", cluster_id)
                p = self.governed_root / rel
                if not p.exists():
                    blockers.append(
                        f"evidence_disposition: missing {label} for cluster '{cluster_id}': {rel}"
                    )
                    continue
                if required_substring:
                    try:
                        body = p.read_text(encoding="utf-8")
                    except Exception:
                        body = ""
                    if required_substring not in body:
                        blockers.append(
                            f"evidence_disposition: {label} file for cluster '{cluster_id}' "
                            f"is empty or missing required header '{required_substring}': {rel}"
                        )
            # Inspect assumptions for unowned 'pending' rows.
            assumptions_rel = assumptions_tmpl.replace("{run_id}", run_id).replace(
                "{cluster}", cluster_id
            )
            assumptions_path = self.governed_root / assumptions_rel
            if assumptions_path.exists():
                try:
                    text = assumptions_path.read_text(encoding="utf-8")
                    self._check_pending_assumptions(text, cluster_id, blockers)
                except Exception:
                    pass

    def _check_pending_assumptions(self, text: str, cluster_id: str, blockers: list[str]) -> None:
        """Parse a markdown table looking for `pending` rows with empty owner
        or empty next_phase_obligation. The expected table shape is:
            | Assumption | Disposition | Owner | Next-phase obligation |

        Phase 3 R1 hardening (SKEP-005): header detection uses exact column-name
        match (not substring), with optional leading pipe per CommonMark. After
        the separator row, every non-blank pipe-bearing line is a data row
        regardless of substring content.
        """
        expected_header = ["assumption", "disposition", "owner", "next-phase obligation"]
        # State machine: 0 = before header, 1 = header seen / awaiting separator, 2 = in data rows
        state = 0
        column_count_warned = False
        saw_pipe_row = False
        for raw_line in text.splitlines():
            line = raw_line.strip()
            # Allow rows without leading pipe — strip pipes uniformly via split.
            if "|" not in line:
                continue
            saw_pipe_row = True
            # Skip separator-only lines (`---|---|---`).
            if set(line) <= {"|", "-", " ", ":"}:
                if state == 1:
                    state = 2
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            cells_lower = [c.lower() for c in cells]
            if state == 0:
                if cells_lower == expected_header:
                    state = 1
                    continue
                # State remains 0 — but a malformed table that has rows but no
                # recognized header is itself a blocker (covers SKEP-005's "no
                # exact header" silent-skip case AND pc_p2_t4 column-count
                # detection for tables that omit the canonical header).
                if len(cells) != 4 and not column_count_warned:
                    blockers.append(
                        f"evidence_disposition: cluster '{cluster_id}' assumptions table "
                        f"has unexpected column count ({len(cells)} != 4)"
                    )
                    column_count_warned = True
                continue
            # state in {1, 2}: data rows (or a stray separator/header repeat)
            if cells_lower == expected_header:
                # repeated header; ignore
                continue
            if len(cells) != 4:
                if not column_count_warned:
                    blockers.append(
                        f"evidence_disposition: cluster '{cluster_id}' assumptions table "
                        f"has unexpected column count ({len(cells)} != 4)"
                    )
                    column_count_warned = True
                continue
            disposition = cells[1].lower()
            owner = cells[2]
            next_obl = cells[3]
            if disposition == "pending" and (not owner or not next_obl):
                blockers.append(
                    f"evidence_disposition: cluster '{cluster_id}' has unowned "
                    f"'pending' assumption: {cells[0][:60]}"
                )
        # If the file had table-like rows but no canonical header was ever seen,
        # the table is structurally malformed for the disposition contract.
        if saw_pipe_row and state == 0 and not column_count_warned:
            blockers.append(
                f"evidence_disposition: cluster '{cluster_id}' assumptions table "
                "missing canonical header "
                "'| Assumption | Disposition | Owner | Next-phase obligation |'"
            )

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
        """Phase 2.4: VERIFY->RESOLVE requires resolutions/{run_id}-lessons.yaml
        with structured schema (run_id + lessons list).
        """
        schema = self.artifact_schemas.get("lessons") or {}
        required_transition = str(schema.get("required_for_transition") or "")
        if not required_transition:
            return
        from_phase = str(artifact.get("from_phase") or "")
        to_phase = str(artifact.get("to_phase") or "")
        if f"{from_phase}->{to_phase}" != required_transition:
            return
        run_id = str(artifact.get("run_id") or "")
        if not _is_safe_run_id(run_id):
            blockers.append("lessons: unsafe or missing run_id")
            return
        template = str(schema.get("path_template") or "resolutions/{run_id}-lessons.yaml")
        path = self.governed_root / template.replace("{run_id}", run_id)
        if not path.exists():
            blockers.append(f"lessons artifact missing: {path.relative_to(self.governed_root)}")
            return
        if yaml is None:
            return
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:
            blockers.append(f"lessons artifact unparseable: {type(exc).__name__}")
            return
        if not isinstance(data, Mapping):
            blockers.append("lessons artifact must be a YAML mapping")
            return
        for field_name in schema.get("required_fields") or []:
            if field_name not in data:
                blockers.append(f"lessons artifact missing required field: {field_name}")
        lessons_list = data.get("lessons")
        if lessons_list is not None and not isinstance(lessons_list, list):
            blockers.append("lessons.lessons must be a list")

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
