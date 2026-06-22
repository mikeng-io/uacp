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
import json
from pathlib import Path
from typing import Any, Mapping

from config import base_dir, get_config
from engines.domain.paths import resolve_uacp_root
from engines.io import loaders as io_loaders

from .models import HeartgateDecision, HeartgateError

try:
    import yaml
except ImportError:  # pragma: no cover - Hermes ships with PyYAML in normal use.
    yaml = None  # type: ignore[assignment]


_RUN_ID_RE = __import__("re").compile(r"^[A-Za-z0-9._-]{1,128}$")


def _is_safe_run_id(run_id: str) -> bool:
    """True if run_id is safe for use as a filesystem name segment.

    Phase 1 remediation (skeptic F1 / technical F1): bound run_id to a
    conservative charset so it cannot escape state/gate-ledger/ via "..",
    "/", "\\", control chars, or pathological lengths.

    Phase 2 hardening (pc_p1_t2 / CRR-2): also reject the literal `.` and
    `..` so any future code that uses run_id without the .jsonl suffix
    cannot construct a directory reference.
    """
    if not isinstance(run_id, str) or not run_id:
        return False
    if run_id in {".", ".."}:
        return False
    return bool(_RUN_ID_RE.match(run_id))


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
            from engines.domain.phase_transitions import stages_default

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
            from engines.domain.phase_transitions import (
                phase_transition_required_fields,
            )

            self.required_fields = phase_transition_required_fields()
        # Phase 2: artifact schemas (scope, intent, evidence_disposition, lessons)
        self.artifact_schemas = _load_artifact_schemas(self.uacp_root)

    @classmethod
    def load(cls, uacp_root: str | Path | None = None) -> "Heartgate":
        from engines.io import load_phase_transitions
        root = resolve_uacp_root(uacp_root)
        loaded = load_phase_transitions(root)
        if loaded.error is not None:
            raise HeartgateError(f"Heartgate config failed to load: {loaded.error}")
        raw = loaded.value
        if not isinstance(raw, dict):
            raise HeartgateError(f"Heartgate config must be a YAML mapping: {root / 'config' / 'phase-transitions.yaml'}")
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
            return HeartgateDecision("warn", "transition passes with accepted warnings", [], warnings)
        return HeartgateDecision("pass", "transition passes", [], [])

    def validate_transition_file(self, path: str | Path) -> HeartgateDecision:
        raw_path = Path(path)
        if not raw_path.is_absolute():
            raw_path = self.governed_root / raw_path
        if yaml is None:
            raise HeartgateError("PyYAML is required to load transition artifact")
        artifact = yaml.safe_load(raw_path.read_text(encoding="utf-8"))
        if not isinstance(artifact, dict):
            return HeartgateDecision("block", "transition artifact must be a YAML mapping", ["invalid artifact"])
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
            from engines.base import run_all_engines

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
                return HeartgateDecision("block", "closure blocked by computed engines", blockers, warnings)
            if warnings:
                return HeartgateDecision("warn", "closure passes with engine warnings", [], warnings)
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

    def _validate_heartgate_coherence(self, artifact: Mapping[str, Any], blockers: list[str], warnings: list[str]) -> None:
        """Validate optional Heartgate transition-coherence evidence.

        SUPERSEDED: this is the original SELF-ATTESTED coherence check — it
        trusts an agent-supplied ``heartgate_coherence.status`` flag. The
        authoritative coherence judgement is now produced by the COMPUTED
        ``coherence`` engine run via :meth:`validate_closure`, which inspects the
        run's emitted state directly rather than trusting a declared status.

        This method is retained for back-compat (existing transition artifacts
        may still carry a ``heartgate_coherence`` block), but the self-attested
        ``status`` field is advisory only; the computed engine is the source of
        truth for coherence at closure. Do not extend this self-attested path —
        add coherence checks to the computed engine instead.
        """
        coherence = artifact.get("heartgate_coherence")
        if coherence in (None, ""):
            return
        if not isinstance(coherence, Mapping):
            blockers.append("heartgate_coherence must be a mapping")
            return
        status = str(coherence.get("status") or "")
        if status not in {"pass", "warn", "block"}:
            blockers.append("heartgate_coherence.status must be pass, warn, or block")
        if status == "block":
            blockers.append("heartgate coherence blocks transition")
        artifact_path = str(coherence.get("artifact_path") or "")
        if not artifact_path:
            blockers.append("heartgate_coherence requires artifact_path")
        elif not self._artifact_path_exists(artifact_path):
            blockers.append(f"heartgate_coherence artifact not found: {artifact_path}")
        required_lenses = {
            "doctrine_coherence",
            "cross_artifact_consistency",
            "runtime_state_alignment",
            "warning_and_deferred_item_honesty",
            "authority_plane_integrity",
            "next_phase_readiness",
        }
        lenses = coherence.get("lenses") or []
        if not isinstance(lenses, list):
            blockers.append("heartgate_coherence.lenses must be a list")
        else:
            missing = sorted(required_lenses - {str(item) for item in lenses})
            if missing:
                blockers.append("heartgate_coherence missing lens(es): " + ", ".join(missing))
        if status == "warn":
            warnings.append("heartgate coherence passed with warnings")

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
        """Structural claim=>evidence check for an in-EXECUTE checkpoint (ADR-0016).

        The goal-driven track records each EXECUTE iteration as a checkpoint
        manifest entry (gate-ledger ``gate: "CHECKPOINT"``). The manifest is NOT
        an honor system: a checkpoint's ``evidence`` must reference a real,
        governed-root-contained artifact — not a prose sentence, not a missing
        path, not a path that escapes the root. This is the same
        no-self-attestation rule Heartgate applies to other gate-ledger evidence,
        applied at the checkpoint boundary.

        Reuses :meth:`_artifact_path_exists` (the existing governed-root
        containment + existence helper) so the containment matches the rest of
        Heartgate — no hand-rolled path logic. A missing/empty evidence ref or a
        ref that escapes the governed root or does not resolve to a real file is
        a BLOCKER.

        Note: this validates the structural evidence coupling only. Wiring the
        checkpoint into the transition/gate flow (so it substitutes for PIV) is
        a later task; this method is exercised in isolation.
        """
        checkpoint_id = str(getattr(entry, "checkpoint_id", "") or "unknown")
        evidence = str(getattr(entry, "evidence", "") or "")
        if not evidence.strip():
            blockers.append(
                f"checkpoint {checkpoint_id}: evidence is required (no self-attestation — a checkpoint claim must reference a real artifact)"
            )
            return
        # Reuse the governed-root containment + existence helper: an evidence ref
        # that escapes the root or does not resolve to an existing file is not a
        # real artifact and cannot back the checkpoint's claim.
        if not self._artifact_path_exists(evidence):
            blockers.append(
                f"checkpoint {checkpoint_id}: evidence artifact not found or escapes governed root: {evidence}"
            )

    def _heartgate_coherence_rule(self) -> Mapping[str, Any]:
        """Resolve the heartgate_coherence_required_when rule.

        Slice 4b T4c-1: the structural grammar (required_field/required_lenses)
        and the selection policy (threshold + phases/routing/domains) are codified
        in engines.domain.gate_rules. The block is read from the loaded
        phase-transitions config WHEN PRESENT (production behavior, unchanged);
        when ABSENT it falls back to the code default, whose operator-tunable
        threshold + selectors come from config/uacp.toml [heartgate.coherence].

        A test fixture may opt OUT by supplying an empty mapping for the block
        (preserving prior test laxity): an explicit ``{}`` is honored as
        "rule present but empty" and disables the gate, exactly as before.
        """
        if "heartgate_coherence_required_when" in self.config:
            return self.config.get("heartgate_coherence_required_when") or {}
        from engines.domain.gate_rules import heartgate_coherence_required_when_default

        coherence_knob: Mapping[str, Any] = {}
        try:
            cfg_raw = get_config(self.uacp_root).model_dump()
            coherence_knob = ((cfg_raw.get("heartgate") or {}).get("coherence")) or {}
        except Exception:
            coherence_knob = {}
        if not isinstance(coherence_knob, Mapping):
            coherence_knob = {}
        threshold = coherence_knob.get("min_composite_granularity")
        return heartgate_coherence_required_when_default(
            min_composite_granularity=threshold if isinstance(threshold, int) else None,
            selectors=dict(coherence_knob),
        )

    def _validate_heartgate_coherence_requirement(self, artifact: Mapping[str, Any], blockers: list[str]) -> None:
        rule = self._heartgate_coherence_rule()
        if not rule:
            return
        coherence = artifact.get("heartgate_coherence")
        if coherence not in (None, ""):
            return
        reasons = []
        min_granularity = rule.get("min_composite_granularity")
        if min_granularity is not None:
            try:
                if int(artifact.get("composite_granularity") or 0) >= int(min_granularity):
                    reasons.append(f"composite_granularity>={min_granularity}")
            except Exception:
                pass
        phases = set(str(x) for x in (rule.get("phases") or []))
        if phases and str(artifact.get("from_phase") or "") in phases:
            reasons.append("phase=" + str(artifact.get("from_phase") or ""))
        routing = set(str(x) for x in (rule.get("routing_outcomes") or []))
        if routing and str(artifact.get("routing_outcome") or "") in routing:
            reasons.append("routing_outcome=" + str(artifact.get("routing_outcome") or ""))
        categories = set(str(x) for x in (rule.get("domains") or []))
        artifact_domains = {str(x) for x in (artifact.get("domains") or [])}
        if categories and categories.intersection(artifact_domains):
            reasons.append("domain=" + ",".join(sorted(categories.intersection(artifact_domains))))
        if reasons:
            blockers.append("heartgate_coherence required by transition policy: " + "; ".join(reasons))

    def _validate_phase_exit_invariants(self, artifact: Mapping[str, Any], blockers: list[str]) -> None:
        """Phase 1 / Item 1.2: enforce phase_exit_invariants from config.

        For the transition's `from_phase`, load `stages.<from_phase>.phase_exit_invariants`
        and check each required invariant by its kind:
        - `artifact_glob` — must match at least one file under UACP_ROOT;
        - `gate_ledger_entry` — must appear in state/gate-ledger/{run_id}.jsonl;
        - `graph_invariant` (D35) — runs the phase-scoped structural subset of the
          graph_projection engine for this transition (scope = `<from_phase>_exit`,
          e.g. `plan_exit`); any block-severity violation becomes a transition
          blocker. This is what makes a dropped intent / orphan / missing coverage
          fail at the boundary where its inputs first complete, instead of only at
          terminal closure.
        """
        from_phase = str(artifact.get("from_phase") or "")
        run_id = str(artifact.get("run_id") or "")
        if not isinstance(self.stages, Mapping):
            blockers.append("phase_exit_invariants: stages config must be a mapping")
            return
        stage = self.stages.get(from_phase) or {}
        if not isinstance(stage, Mapping):
            blockers.append(f"phase_exit_invariants: stage '{from_phase}' config must be a mapping")
            return
        invariants = stage.get("phase_exit_invariants") or []
        if not invariants:
            return
        for inv in invariants:
            if not isinstance(inv, Mapping):
                blockers.append("phase_exit_invariant must be a mapping")
                continue
            required = bool(inv.get("required"))
            if not required:
                continue
            glob_pattern = str(inv.get("artifact_glob") or "")
            ledger_gate = str(inv.get("gate_ledger_entry") or "")
            graph_scope = str(inv.get("graph_invariant") or "")
            if glob_pattern:
                if "{run_id}" in glob_pattern and not run_id:
                    blockers.append(f"phase_exit_invariant unmet: run_id required to resolve glob '{glob_pattern}'")
                    continue
                pat = glob_pattern.replace("{run_id}", run_id) if run_id else glob_pattern
                if not self._glob_matches_any(pat):
                    blockers.append(f"phase_exit_invariant unmet: no artifact matches '{pat}'")
            elif ledger_gate:
                if not run_id:
                    blockers.append(f"phase_exit_invariant unmet: run_id required to verify ledger entry '{ledger_gate}'")
                elif not self._ledger_contains_gate(run_id, ledger_gate):
                    blockers.append(f"phase_exit_invariant unmet: gate ledger missing entry '{ledger_gate}'")
            elif graph_scope:
                if not run_id:
                    blockers.append(f"phase_exit_invariant unmet: run_id required for graph_invariant '{graph_scope}'")
                    continue
                # D35: run the phase-scoped structural subset of graph_projection
                # for this transition. The engine never raises; block-severity
                # violations (dropped intent / orphan / phantom / missing coverage /
                # contradiction) gate the phase exit.
                from engines.graph_projection import validate_graph_invariants

                for v in validate_graph_invariants(self.uacp_root, run_id, graph_scope):
                    if v.severity == "block":
                        blockers.append(f"phase_exit_invariant unmet: {v.code}: {v.message}")

    def _validate_artifact_integrity(self, artifact: Mapping[str, Any], blockers: list[str]) -> None:
        """Hardening #6: run the artifact-integrity (SHA-256 watermark) check at
        EVERY transition, not only at terminal closure, so an out-of-band tamper of
        a recorded artifact is caught at the boundary instead of being swapped back
        before RESOLVE. No-op on runs with no watermark index (legacy / non-governed-
        writer runs). The engine never raises."""
        run_id = str(artifact.get("run_id") or "")
        if not run_id:
            return
        from engines.artifact_integrity import validate_artifact_integrity

        for v in validate_artifact_integrity(self.uacp_root, run_id):
            if v.severity == "block":
                blockers.append(f"{v.code}: {v.message}")

    def _validate_adaptive_proposal_package_gate(self, artifact: Mapping[str, Any], blockers: list[str]) -> None:
        """Enforce adaptive proposal package selection for PROPOSE->PLAN.

        The config declares the policy. The kernel enforces the hard minimum:
        when a transition moves from PROPOSE to PLAN and the adaptive gate is
        configured, a package-selection artifact must exist, parse, and cover
        universal core concerns plus selected module artifact references. This
        keeps YAML proposal envelopes from being treated as the whole proposal.
        """
        if str(artifact.get("from_phase") or "") != "propose" or str(artifact.get("to_phase") or "") != "plan":
            return
        gate = self.config.get("adaptive_proposal_package_gate") or {}
        if not isinstance(gate, Mapping):
            return
        run_id = str(artifact.get("run_id") or "")
        if not run_id:
            blockers.append("adaptive_proposal_package_gate requires run_id")
            return
        selection_rel = f"proposals/{run_id}-package-selection.yaml"
        package_rel = f"proposals/{run_id}"
        selection_path = self.governed_root / selection_rel
        package_path = self.governed_root / package_rel
        if not selection_path.exists():
            blockers.append(f"adaptive_proposal_package_gate: missing {selection_rel}")
            return
        if not package_path.exists() or not package_path.is_dir():
            blockers.append(f"adaptive_proposal_package_gate: missing package directory {package_rel}/")
        if yaml is None:
            blockers.append("adaptive_proposal_package_gate requires PyYAML")
            return
        try:
            selection = yaml.safe_load(selection_path.read_text(encoding="utf-8"))
        except Exception as exc:
            blockers.append(f"adaptive_proposal_package_gate: failed to parse {selection_rel}: {exc}")
            return
        if not isinstance(selection, Mapping):
            blockers.append(f"adaptive_proposal_package_gate: {selection_rel} must be a mapping")
            return
        if selection.get("kind") != "uacp.proposal_package_selection":
            blockers.append("adaptive_proposal_package_gate: package-selection kind must be uacp.proposal_package_selection")
        from engines.domain.gate_rules import PROPOSAL_REQUIRED_UNIVERSAL_CORE
        required_core = list(gate.get("required_universal_core") or []) or list(
            PROPOSAL_REQUIRED_UNIVERSAL_CORE
        )
        core = selection.get("universal_core") if isinstance(selection.get("universal_core"), Mapping) else {}
        for key in required_core:
            item = core.get(str(key)) if isinstance(core, Mapping) else None
            if not isinstance(item, Mapping):
                blockers.append(f"adaptive_proposal_package_gate: universal_core.{key} missing")
                continue
            status = str(item.get("status") or "")
            if status == "covered":
                artifact_path = str(item.get("artifact") or "")
                if not artifact_path or not self._artifact_path_exists(artifact_path):
                    blockers.append(f"adaptive_proposal_package_gate: universal_core.{key} artifact missing")
            elif status == "not_applicable":
                self._validate_package_na(selection_rel, f"universal_core.{key}", item, blockers)
            else:
                blockers.append(f"adaptive_proposal_package_gate: universal_core.{key} status must be covered|not_applicable")
        modules = selection.get("selected_modules") if isinstance(selection.get("selected_modules"), Mapping) else {}
        if not modules:
            blockers.append("adaptive_proposal_package_gate: selected_modules must not be empty")
        for name, item in modules.items() if isinstance(modules, Mapping) else []:
            if not isinstance(item, Mapping):
                blockers.append(f"adaptive_proposal_package_gate: selected_modules.{name} must be a mapping")
                continue
            if not item.get("reason"):
                blockers.append(f"adaptive_proposal_package_gate: selected_modules.{name} missing reason")
            artifact_path = str(item.get("artifact") or "")
            if not artifact_path or not self._artifact_path_exists(artifact_path):
                blockers.append(f"adaptive_proposal_package_gate: selected_modules.{name} artifact missing")
        na = selection.get("not_applicable") if isinstance(selection.get("not_applicable"), Mapping) else {}
        for name, item in na.items() if isinstance(na, Mapping) else []:
            self._validate_package_na(selection_rel, f"not_applicable.{name}", item, blockers)

    def _run_track(self, run_id: str) -> str:
        """Read a run's track from its manifest (state/runs/{run_id}.yaml).

        This is the ONLY seam by which Heartgate learns whether a run is on the
        goal-driven track. It is called from the goal-driven gates (the PROPOSE
        convergence-budget gate, the convergence cap, and the EXECUTE->VERIFY
        checkpoint relaxation). A standard-track transition DOES reach this read
        at those phase pairs, but it is a fail-safe, behavior-NEUTRAL read: it
        resolves to "standard" and every new behavior is strictly behind the
        ``== "goal-driven"`` branch, so the standard path stays byte-identical to
        before (the read returns "standard" and the gate proceeds exactly as it
        did, with no new blocker, warning, or side effect).

        Fail-safe: a missing/garbled manifest, or one that does not validate,
        resolves to ``"standard"`` (the default) — an autonomous-safety gate must
        not *itself* hard-fail a transition because the manifest could not be
        read; absent positive evidence of the goal-driven track, no new behavior
        fires. (The manifest's own existence/validity is enforced elsewhere.)
        """
        if not _is_safe_run_id(run_id):
            return "standard"
        try:
            from engines.io.loaders import load_manifest

            loaded = load_manifest(self.uacp_root, run_id)
            if loaded.error is not None or loaded.value is None:
                return "standard"
            model = loaded.value.model
            if model is not None:
                return str(getattr(model, "track", "standard") or "standard")
            # Tolerate a manifest the strict schema rejected: read the raw track.
            raw = loaded.value.raw
            return str(raw.get("track") or "standard") if isinstance(raw, Mapping) else "standard"
        except Exception:
            return "standard"

    def _goal_checkpoint_count(self, goal_id: str) -> int:
        """Count gate: CHECKPOINT ledger entries across the goal's whole run-chain.

        A goal can span a CHAIN of runs (Task 3): "roll back to a checkpoint" is
        realized as launching a new forward run under the same persistent goal.
        So the convergence cap counts CHECKPOINT entries across ALL runs sharing
        the ``goal_id``.

        Council M-1 (autonomous-safety): the chain is enumerated by scanning the
        RUN MANIFESTS on disk (``state/runs/*.yaml``), NOT the run registry. The
        manifest's ``goal_id`` is the AUTHORITATIVE binding — it is what the
        per-run goal-driven gates read (:meth:`_run_track` / :meth:`_run_goal_id`)
        and what the registry writer is cross-checked against. The registry, by
        contrast, is self-declared and need not be complete: an executor can spawn
        a forward run that never registers (or registers under a different
        ``goal_id``), which would let a registry-based count UNDERcount and reset
        the budget per run -> an unbounded loop. Counting by manifest closes both
        "didn't register" and "registered under a different goal_id": every run
        whose MANIFEST declares this ``goal_id`` contributes its CHECKPOINT
        entries, regardless of registry presence.

        Never raises: an unreadable manifest/ledger contributes zero rather than
        crashing the gate (a fail-safe count, like the rest of the goal-driven
        path). A manifest the strict schema rejects still has its raw ``goal_id``
        consulted, so a structurally-odd-but-bound run is still counted.
        """
        if not goal_id:
            return 0
        try:
            from engines.io.loaders import glob_in_workspace, load_manifest
        except Exception:
            return 0
        total = 0
        seen: set[str] = set()
        try:
            manifests = glob_in_workspace(self.uacp_root, "state/runs/*.yaml")
        except Exception:
            return 0
        for manifest_path in manifests:
            rid = manifest_path.stem  # filename sans .yaml is the run_id
            if not _is_safe_run_id(rid) or rid in seen:
                continue
            seen.add(rid)
            # Authoritative binding: this run is in the chain iff its MANIFEST
            # goal_id equals goal_id. Load tolerantly (never raise).
            try:
                loaded = load_manifest(self.uacp_root, rid)
            except Exception:
                continue
            if loaded.error is not None or loaded.value is None:
                continue
            model = loaded.value.model
            if model is not None:
                run_goal = str(getattr(model, "goal_id", "") or "")
            else:
                raw = loaded.value.raw
                run_goal = str(raw.get("goal_id") or "") if isinstance(raw, Mapping) else ""
            if run_goal != goal_id:
                continue
            ledger_path = self.governed_root / "state" / "gate-ledger" / f"{rid}.jsonl"
            if not ledger_path.exists():
                continue
            try:
                for line in ledger_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    if str(rec.get("gate") or "") == "CHECKPOINT":
                        total += 1
            except Exception:
                continue
        return total

    def _load_convergence_budget(self, run_id: str):
        """Load + validate the PROPOSE convergence-budget; returns ``(budget, error)``.

        Adapter (A2): the load/validate logic lives in
        :func:`engines.io.loaders.load_convergence_budget` (the Loaded contract);
        this returns the gate's ``(budget, error)`` tuple. The yaml-None guard
        stays here — core tolerates a missing PyYAML; the io layer hard-imports it.
        """
        if yaml is None:
            return None, "convergence_budget gate requires PyYAML"
        result = io_loaders.load_convergence_budget(self.uacp_root, run_id)
        return result.value, result.error

    def _triage_track(self, run_id: str) -> str:
        """Read the run's TRACK as decided by the TRIAGE artifact (authoritative).

        Council M-2: the manifest's ``track`` is set by the worker on its own
        manifest — a worker could self-select ``goal-driven`` to swap the
        deterministic PIV-artifact gate for the (relaxed) checkpoint-manifest
        gate. TRIAGE is where the track is *decided* (the mechanical
        specifiable-artifact test), so the TRIAGE artifact is the authority. This
        reads the ``track`` declared on the triage artifact at
        ``proposals/{run_id}-triage*.yaml`` (the same glob Heartgate's
        phase_exit_invariants use to locate it).

        Returns the triage ``track`` as a string, defaulting to ``"standard"``
        when the triage artifact is absent / unreadable / declares no track —
        i.e. a run is treated as goal-driven by TRIAGE ONLY on positive evidence.
        Never raises. (The FIRST matching triage artifact is consulted; the glob
        is normally singular.)
        """
        if not _is_safe_run_id(run_id):
            return "standard"
        try:
            from engines.io.loaders import glob_in_workspace
        except Exception:
            return "standard"
        try:
            matches = sorted(
                glob_in_workspace(self.uacp_root, f"proposals/{run_id}-triage*.yaml"),
                key=lambda p: p.name,
            )
        except Exception:
            return "standard"
        if yaml is None:
            return "standard"
        for path in matches:
            try:
                raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(raw, Mapping):
                return str(raw.get("track") or "standard") or "standard"
        return "standard"

    def _validate_convergence_budget_gate(self, artifact: Mapping[str, Any], blockers: list[str]) -> None:
        """PROPOSE->PLAN: a goal-driven run MUST declare a convergence budget,
        and its manifest track MUST match the TRIAGE decision.

        ADR-0016 R2: an autonomous goal-driven run (``claude -p``, cron) has no
        operator to sign off, so without a declared+enforced bound it loops
        forever. At PROPOSE->PLAN, when (and ONLY when) the run's track is
        ``goal-driven``, the PROPOSE convergence-budget artifact must exist and
        carry a positive ``max_checkpoints``. Standard runs skip this entirely —
        the track is read from the manifest behind the goal-driven branch, so
        the standard PROPOSE->PLAN path is unchanged.

        Council M-2 (un-forge the track): the manifest ``track`` is set by the
        worker, so a worker could self-select ``goal-driven`` to swap the
        deterministic PIV-artifact gate for the relaxed manifest gate. TRIAGE is
        the authority for the track decision. So when the manifest claims
        ``goal-driven``, the TRIAGE artifact's ``track`` (default ``standard``
        if absent) must ALSO be ``goal-driven`` — else fail CLOSED (a worker
        cannot self-relax the track). Still fully behind the goal-driven branch;
        the standard path is untouched.
        """
        if str(artifact.get("from_phase") or "") != "propose" or str(artifact.get("to_phase") or "") != "plan":
            return
        run_id = str(artifact.get("run_id") or "")
        # TRACK GATE: read the manifest only after the phase guard, and only act
        # on goal-driven. A standard run returns here before any budget logic.
        if self._run_track(run_id) != "goal-driven":
            return
        if not _is_safe_run_id(run_id):
            blockers.append("convergence_budget gate requires a valid run_id")
            return
        # Council M-2: the manifest track must match the TRIAGE decision. A
        # manifest that claims goal-driven over a triage artifact that did NOT
        # decide goal-driven is a self-relaxation -> fail closed.
        triage_track = self._triage_track(run_id)
        if triage_track != "goal-driven":
            blockers.append(
                f"track mismatch: run manifest declares track 'goal-driven' but the "
                f"TRIAGE artifact decided track '{triage_track}' "
                "(proposals/{run_id}-triage*.yaml is authoritative; a worker may not "
                "self-select the goal-driven track to relax the PIV-artifact gate)".replace(
                    "{run_id}", run_id
                )
            )
            return
        _budget, error = self._load_convergence_budget(run_id)
        if error is not None:
            blockers.append(error)

    def _load_checkpoint_manifest(self, run_id: str) -> list[Mapping[str, Any]]:
        """Read the run's gate: CHECKPOINT ledger records (raw, in ledger order).

        Adapter (A2): the ledger read lives in
        :func:`engines.io.loaders.load_checkpoint_manifest` (never raises). The
        run_id-safety guard stays here — an unsafe id yields no records.
        """
        if not _is_safe_run_id(run_id):
            return []
        return io_loaders.load_checkpoint_manifest(self.uacp_root, run_id)

    def _validate_goal_driven_checkpoint_gate(
        self, run_id: str, blockers: list[str]
    ) -> bool:
        """Validate a goal-driven run's in-EXECUTE checkpoint manifest (ADR-0016).

        Returns ``True`` iff the manifest is COHERENT — i.e. it may substitute for
        the deterministic PIV/findings-clearing artifacts at EXECUTE->VERIFY.
        "Coherent" means ALL of:

          * the manifest is non-empty (there is at least one ``gate: CHECKPOINT``
            record to substitute for the PIV/checkpoint artifacts);
          * EVERY record, once its ledger ENVELOPE is stripped (``gate``/``ts``
            and any non-payload key — ``run_id`` is itself a CheckpointEntry
            field and is kept), validates as a :class:`CheckpointEntry`
            (``extra="forbid"``) — a malformed/extra-field record is incoherent;
          * EVERY entry's ``evidence`` references a real governed-root-contained
            artifact (:meth:`_validate_checkpoint_entry` — the structural
            no-self-attestation / no-fabrication rule);
          * the total recorded checkpoint count does NOT exceed the convergence cap
            (checked post-loop with strict ``>`` against the already-recorded total
            — exactly ``max_checkpoints`` records PASSES; more BLOCKS);
          * the FINAL entry's verdict is ``keep`` — a dangling ``roll_back`` /
            ``restart`` means the run has not converged and must not promote.

        Any failure appends a blocker and returns ``False``. This method is only
        ever reached behind the goal-driven track gate in
        :meth:`_validate_adaptive_execute_evidence_gate`; it does not itself read
        the track.
        """
        from engines.domain.checkpoint import CheckpointEntry
        from pydantic import ValidationError

        records = self._load_checkpoint_manifest(run_id)
        if not records:
            blockers.append(
                "goal-driven execute->verify: checkpoint manifest is empty "
                "(no gate: CHECKPOINT records to substitute for the PIV/execution "
                "evidence — the run has produced no governed checkpoint)"
            )
            return False

        coherent = True
        entries: list[CheckpointEntry] = []
        goal_id_seen: str | None = None
        # The ledger envelope keys the writer stamps that are NOT CheckpointEntry
        # payload fields. ``run_id`` IS a CheckpointEntry field, so it is kept.
        payload_fields = set(CheckpointEntry.model_fields)
        for idx, rec in enumerate(records, start=1):
            cid = str(rec.get("checkpoint_id") or f"#{idx}")
            # Envelope-strip: keep only valid CheckpointEntry payload keys so the
            # extra="forbid" model validates the PAYLOAD, not the envelope.
            payload = {k: v for k, v in rec.items() if k in payload_fields}
            try:
                entry = CheckpointEntry(**payload)
            except ValidationError as exc:
                first = exc.errors()[0] if exc.errors() else {}
                detail = first.get("msg") or str(exc)
                loc = ".".join(str(p) for p in (first.get("loc") or [])) or "?"
                blockers.append(
                    f"goal-driven checkpoint manifest: checkpoint {cid} is malformed "
                    f"(CheckpointEntry validation failed at {loc}: {detail})"
                )
                coherent = False
                continue
            entries.append(entry)
            if goal_id_seen is None and entry.goal_id:
                goal_id_seen = entry.goal_id
            # Structural claim=>evidence (no self-attestation / no-fabrication).
            before = len(blockers)
            self._validate_checkpoint_entry(entry, blockers)
            if len(blockers) != before:
                coherent = False

        # Cap: block iff the total recorded checkpoint count for this goal EXCEEDS
        # max_checkpoints (strict >). A manifest with EXACTLY max_checkpoints
        # entries is at-budget and PASSES; max_checkpoints+1 BLOCKS.
        # This is the LIVE cap path (council MINOR+cleanup removed the dead
        # _validate_convergence_cap pre-append helper): a post-hoc check on an
        # already-recorded total, so it uses strict > (not >=) against the total
        # the manifest scan returns for this goal's whole run-chain.
        if goal_id_seen:
            budget, budget_error = self._load_convergence_budget(run_id)
            if budget_error is not None or budget is None:
                blockers.append(
                    budget_error or "convergence cap: goal-driven run requires a convergence_budget"
                )
                coherent = False
            else:
                count = self._goal_checkpoint_count(goal_id_seen)
                if count > budget.max_checkpoints:
                    blockers.append(
                        f"convergence_budget exhausted: goal '{goal_id_seen}' has {count} "
                        f"checkpoint(s), cap is max_checkpoints={budget.max_checkpoints}; "
                        "the manifest exceeds the convergence budget "
                        "(the run must converge or escalate, not loop)"
                    )
                    coherent = False

        # The manifest must converge on a keep: a dangling roll_back/restart final
        # verdict means the probe was discarded — there is nothing to promote.
        if entries and entries[-1].verdict != "keep":
            blockers.append(
                "goal-driven checkpoint manifest: final checkpoint verdict is "
                f"'{entries[-1].verdict}' (a dangling roll_back/restart has not "
                "converged on a keep — there is no result to promote to VERIFY)"
            )
            coherent = False

        return coherent

    def _validate_adaptive_plan_package_gate(self, artifact: Mapping[str, Any], blockers: list[str]) -> None:
        """Enforce adaptive PLAN package selection for PLAN->EXECUTE."""
        if str(artifact.get("from_phase") or "") != "plan" or str(artifact.get("to_phase") or "") != "execute":
            return
        gate = self.config.get("adaptive_plan_package_gate") or {}
        if not isinstance(gate, Mapping):
            return
        run_id = str(artifact.get("run_id") or "")
        if not run_id:
            blockers.append("adaptive_plan_package_gate requires run_id")
            return
        selection_rel = f"plans/{run_id}-plan-selection.yaml"
        package_rel = f"plans/{run_id}"
        scope_rel = f"plans/{run_id}-scope.yaml"
        selection_path = self.governed_root / selection_rel
        package_path = self.governed_root / package_rel
        scope_path = self.governed_root / scope_rel
        if not selection_path.exists():
            blockers.append(f"adaptive_plan_package_gate: missing {selection_rel}")
            return
        if not package_path.exists() or not package_path.is_dir():
            blockers.append(f"adaptive_plan_package_gate: missing plan package directory {package_rel}/")
        if not scope_path.exists():
            blockers.append(f"adaptive_plan_package_gate: missing scope artifact {scope_rel}")
        if yaml is None:
            blockers.append("adaptive_plan_package_gate requires PyYAML")
            return
        try:
            selection = yaml.safe_load(selection_path.read_text(encoding="utf-8"))
        except Exception as exc:
            blockers.append(f"adaptive_plan_package_gate: failed to parse {selection_rel}: {exc}")
            return
        if not isinstance(selection, Mapping):
            blockers.append(f"adaptive_plan_package_gate: {selection_rel} must be a mapping")
            return
        if selection.get("kind") != "uacp.plan_package_selection":
            blockers.append("adaptive_plan_package_gate: plan-selection kind must be uacp.plan_package_selection")
        if selection.get("phase") != "plan":
            blockers.append("adaptive_plan_package_gate: plan-selection phase must be plan")
        from engines.domain.gate_rules import PLAN_REQUIRED_UNIVERSAL_CORE
        required_core = list(gate.get("required_universal_core") or []) or list(
            PLAN_REQUIRED_UNIVERSAL_CORE
        )
        core = selection.get("universal_core") if isinstance(selection.get("universal_core"), Mapping) else {}
        for key in required_core:
            item = core.get(str(key)) if isinstance(core, Mapping) else None
            if not isinstance(item, Mapping):
                blockers.append(f"adaptive_plan_package_gate: universal_core.{key} missing")
                continue
            status = str(item.get("status") or "")
            if status == "covered":
                artifact_path = str(item.get("artifact") or "")
                if not artifact_path or not self._artifact_path_exists(artifact_path):
                    blockers.append(f"adaptive_plan_package_gate: universal_core.{key} artifact missing")
            elif status == "not_applicable":
                self._validate_plan_na(selection_rel, f"universal_core.{key}", item, blockers)
            else:
                blockers.append(f"adaptive_plan_package_gate: universal_core.{key} status must be covered|not_applicable")
        modules = selection.get("selected_modules") if isinstance(selection.get("selected_modules"), Mapping) else {}
        if not modules:
            blockers.append("adaptive_plan_package_gate: selected_modules must not be empty")
        for name, item in modules.items() if isinstance(modules, Mapping) else []:
            if not isinstance(item, Mapping):
                blockers.append(f"adaptive_plan_package_gate: selected_modules.{name} must be a mapping")
                continue
            if not item.get("reason"):
                blockers.append(f"adaptive_plan_package_gate: selected_modules.{name} missing reason")
            artifact_path = str(item.get("artifact") or "")
            if not artifact_path or not self._artifact_path_exists(artifact_path):
                blockers.append(f"adaptive_plan_package_gate: selected_modules.{name} artifact missing")
        na = selection.get("not_applicable") if isinstance(selection.get("not_applicable"), Mapping) else {}
        for name, item in na.items() if isinstance(na, Mapping) else []:
            self._validate_plan_na(selection_rel, f"not_applicable.{name}", item, blockers)
        readiness = selection.get("transition_readiness")
        if not isinstance(readiness, Mapping):
            blockers.append("adaptive_plan_package_gate: transition_readiness must be a mapping")
        elif readiness.get("status") not in {"ready_for_execute", "ready_with_conditions", "blocked"}:
            blockers.append("adaptive_plan_package_gate: transition_readiness.status is invalid")

    def _validate_plan_na(self, artifact: str, label: str, item: Any, blockers: list[str]) -> None:
        if not isinstance(item, Mapping):
            blockers.append(f"adaptive_plan_package_gate: {label} in {artifact} must be a mapping")
            return
        from engines.domain.gate_rules import PLAN_NOT_APPLICABLE_REQUIRED_FIELDS
        for field_name in PLAN_NOT_APPLICABLE_REQUIRED_FIELDS:
            if item.get(field_name) in (None, ""):
                blockers.append(f"adaptive_plan_package_gate: {label} missing {field_name}")

    def _validate_package_na(self, artifact: str, label: str, item: Any, blockers: list[str]) -> None:
        if not isinstance(item, Mapping):
            blockers.append(f"adaptive_proposal_package_gate: {label} in {artifact} must be a mapping")
            return
        from engines.domain.gate_rules import PROPOSAL_NOT_APPLICABLE_REQUIRED_FIELDS
        for field_name in PROPOSAL_NOT_APPLICABLE_REQUIRED_FIELDS:
            if item.get(field_name) in (None, ""):
                blockers.append(f"adaptive_proposal_package_gate: {label} missing {field_name}")


    def _load_yaml_under_root(self, rel_path: str, blockers: list[str], label: str) -> Mapping[str, Any] | None:
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


    def _offline_validate_artifacts(self, rel_paths: list[str], blockers: list[str], label: str) -> None:
        """Run the canonical artifact validator in-process for runtime gates.

        Heartgate performs transition-time checks; the offline validator owns the
        deeper artifact semantics. Importing and calling it here prevents drift
        where Heartgate only checks artifact presence while validator catches the
        real semantic false-pass.
        """
        validator_path = self.uacp_root / "scripts" / "validate_uacp_artifacts.py"
        if not validator_path.exists():
            blockers.append(f"{label}: validator script missing: scripts/validate_uacp_artifacts.py")
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
                    module.validate_phase_transition(path, obj, phase_config, issues, root=self.uacp_root)
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
                    module.validate_resolve_package_selection(path, obj, issues, root=self.uacp_root)
                elif kind == "uacp.resolve_closure":
                    module.validate_resolve_closure(path, obj, issues, root=self.uacp_root)
            for issue in issues:
                if str(issue).startswith("BLOCK"):
                    blockers.append(f"{label}: {issue}")
        except Exception as exc:
            blockers.append(f"{label}: validator execution failed: {type(exc).__name__}: {exc}")

    def _validate_adaptive_execute_evidence_gate(self, artifact: Mapping[str, Any], blockers: list[str]) -> None:
        if str(artifact.get("from_phase") or "") != "execute" or str(artifact.get("to_phase") or "") != "verify":
            return
        # F-T3-01 (SECURITY): fail CLOSED. The gate body reads nothing from the
        # config block beyond a former presence check (it enforces structure via
        # hardcoded relative artifact paths), so when the phase-guard matches we
        # ENFORCE regardless of whether adaptive_execute_evidence_gate is present.
        # An absent or non-mapping key must not silently disable this evidence gate.
        run_id = str(artifact.get("run_id") or "")
        if not run_id:
            blockers.append("adaptive_execute_evidence_gate requires run_id")
            return
        # ADR-0016 / Task 6b — PER-TRACK RELAXATION (track-gated; standard path
        # below is byte-identical). For a GOAL-DRIVEN run, the deterministic
        # PIV/findings-clearing evidence gate is SATISFIED by a COHERENT checkpoint
        # manifest IN LIEU OF the PIV/checkpoint artifacts: every CHECKPOINT entry
        # validates + has real evidence (no-fabrication still fires), no keep is
        # over the convergence cap (now LIVE), and the manifest converges on a
        # final keep. A coherent manifest -> the deterministic evidence demands are
        # met, so return before requesting the PIV/checkpoint artifacts. An
        # INCOHERENT/missing manifest appends its own blocker(s) and returns
        # (BLOCKED). The authority/containment/no-fabrication invariants are NOT
        # part of this method (Guardian + invariant_summary + the structural
        # evidence check enforce them) and continue to fire for goal-driven runs.
        # A STANDARD run falls straight through to the unchanged gate body below —
        # the track read is the ONLY new statement on its path and resolves
        # fail-safe to "standard".
        if self._run_track(run_id) == "goal-driven":
            self._validate_goal_driven_checkpoint_gate(run_id, blockers)
            return
        piv_rel = f"plans/{run_id}-piv.yaml"
        checkpoint_rel = f"executions/{run_id}-checkpoint-001.yaml"
        package_rel = f"executions/{run_id}"
        piv = self._load_yaml_under_root(piv_rel, blockers, "adaptive_execute_evidence_gate")
        if piv is not None:
            if piv.get("kind") != "uacp.phase_intent_verification_contract":
                blockers.append("adaptive_execute_evidence_gate: PIV contract kind must be uacp.phase_intent_verification_contract")
            if piv.get("run_id") != run_id:
                blockers.append("adaptive_execute_evidence_gate: PIV contract run_id mismatch")
        checkpoint = self._load_yaml_under_root(checkpoint_rel, blockers, "adaptive_execute_evidence_gate")
        if checkpoint is not None:
            if checkpoint.get("kind") != "uacp.execution_checkpoint":
                blockers.append("adaptive_execute_evidence_gate: checkpoint kind must be uacp.execution_checkpoint")
            readiness = checkpoint.get("next_phase_readiness") if isinstance(checkpoint.get("next_phase_readiness"), Mapping) else {}
            if readiness.get("target_phase") != "verify":
                blockers.append("adaptive_execute_evidence_gate: checkpoint target_phase must be verify")
            if readiness.get("status") not in {"ready", "ready_with_deferred_items"}:
                blockers.append("adaptive_execute_evidence_gate: checkpoint is not ready for verify")
        self._offline_validate_artifacts([piv_rel, checkpoint_rel], blockers, "adaptive_execute_evidence_gate")
        if not self._dir_under_root_exists(package_rel):
            blockers.append(f"adaptive_execute_evidence_gate: missing execution package directory {package_rel}/")

    def _validate_goal_driven_closure_gate(self, run_id: str, blockers: list[str]) -> bool:
        """Gate a goal-driven run's CLOSURE on manifest coherence (ADR-0016 O5).

        A goal-driven run's checkpoints are disposable probes until one SATISFIES
        the goal; that satisfying checkpoint is *promoted to result* and the run
        closes. This gate is what lets the run close: it requires the run's
        checkpoint manifest to be COHERENT *and* the final (promoted) checkpoint's
        evidence to be BOUND TO THE GOAL.

        "Manifest coherence at closure" is NOT a lower bar — it ADDS to the shared
        standard closure invariants (the computed engines, no-fabrication,
        containment), which continue to fire unchanged for goal-driven runs (this
        gate does not touch them). It layers these REQUIREMENTS on top:

          * the manifest is COHERENT per :meth:`_validate_goal_driven_checkpoint_gate`
            — every CHECKPOINT entry parses, each entry's ``evidence`` references a
            real governed-root-contained artifact (the no-self-attestation /
            no-fabrication / containment rule), no keep is over the convergence
            cap, AND the FINAL entry's verdict is ``keep`` (no dangling roll_back /
            restart — i.e. (a) final keep and (b) no dangling non-keep are the same
            convergence requirement, enforced there); AND
          * the FINAL (promoted) checkpoint's evidence is BOUND TO THE GOAL: its
            ``goal_id`` equals the run manifest's ``goal_id``. A final keep whose
            evidence belongs to a DIFFERENT goal is not a result for THIS goal and
            must not close the run. (The final entry's evidence EXISTENCE is already
            enforced by the coherence pass above; this adds the goal binding.)

        DRY: the coherence layer is the SAME Task-6 helper used at EXECUTE->VERIFY
        (:meth:`_validate_goal_driven_checkpoint_gate`); this gate reuses it rather
        than re-deriving "coherent", then layers only the goal-binding requirement
        the closure boundary adds. Returns ``True`` iff coherent AND goal-bound;
        any failure appends a blocker and returns ``False``.
        """
        coherent = self._validate_goal_driven_checkpoint_gate(run_id, blockers)

        # The promoted result is the FINAL checkpoint. Its evidence must be bound
        # to the run's goal — a final keep recorded under a different goal_id is
        # not a result for THIS run's goal. (Existence/containment of that evidence
        # is enforced by the coherence pass above; this adds the goal binding.)
        final = self._final_checkpoint_entry(run_id)
        run_goal_id = self._run_goal_id(run_id)
        if final is not None and run_goal_id:
            final_goal_id = str(getattr(final, "goal_id", "") or "")
            if final_goal_id != run_goal_id:
                blockers.append(
                    "goal-driven closure: final checkpoint evidence is not bound to "
                    f"the run's goal (final checkpoint goal_id '{final_goal_id}' != run "
                    f"goal_id '{run_goal_id}' — the promoted result must satisfy THIS "
                    "run's goal)"
                )
                return False
        return coherent

    def _final_checkpoint_entry(self, run_id: str):
        """Parse the LAST gate: CHECKPOINT manifest record into a CheckpointEntry.

        Returns the final entry (or ``None`` if the manifest is empty / the final
        record does not validate). Reuses :meth:`_load_checkpoint_manifest` (the
        same raw-record reader the coherence gate uses) and the same envelope-strip
        rule, so the "final entry" this sees is exactly the one the coherence gate
        validated. Never raises.
        """
        from engines.domain.checkpoint import CheckpointEntry
        from pydantic import ValidationError

        records = self._load_checkpoint_manifest(run_id)
        if not records:
            return None
        payload_fields = set(CheckpointEntry.model_fields)
        payload = {k: v for k, v in records[-1].items() if k in payload_fields}
        try:
            return CheckpointEntry(**payload)
        except ValidationError:
            return None

    def _run_goal_id(self, run_id: str) -> str:
        """Read a run's goal_id from its manifest (state/runs/{run_id}.yaml).

        Mirrors :meth:`_run_track`'s fail-safe manifest read: a missing/garbled/
        invalid manifest resolves to ``""`` (no positive goal binding) rather than
        raising. Used by the goal-driven closure gate to bind the promoted final
        checkpoint to the run's goal.
        """
        if not _is_safe_run_id(run_id):
            return ""
        try:
            from engines.io.loaders import load_manifest

            loaded = load_manifest(self.uacp_root, run_id)
            if loaded.error is not None or loaded.value is None:
                return ""
            model = loaded.value.model
            if model is not None:
                return str(getattr(model, "goal_id", "") or "")
            raw = loaded.value.raw
            return str(raw.get("goal_id") or "") if isinstance(raw, Mapping) else ""
        except Exception:
            return ""

    def _validate_adaptive_verify_evidence_gate(self, artifact: Mapping[str, Any], blockers: list[str]) -> None:
        if str(artifact.get("from_phase") or "") != "verify" or str(artifact.get("to_phase") or "") != "resolve":
            return
        # F-T3-01 (SECURITY): fail CLOSED — see _validate_adaptive_execute_evidence_gate.
        # An absent or non-mapping adaptive_verify_evidence_gate key must not disable enforcement.
        run_id = str(artifact.get("run_id") or "")
        if not run_id:
            blockers.append("adaptive_verify_evidence_gate requires run_id")
            return
        # ADR-0016 O5 / Task 7 — PER-TRACK CLOSURE (track-gated; the standard path
        # below is byte-identical). For a GOAL-DRIVEN run, the deterministic
        # verify-selection / resolve-readiness evidence gate is SATISFIED by a
        # COHERENT checkpoint manifest whose final (promoted) checkpoint is bound
        # to the run's goal — the manifest substitutes for the verify-selection /
        # resolve-readiness artifacts at CLOSURE exactly as it does at EXECUTE->
        # VERIFY. This ADDS manifest coherence on top of the shared standard
        # closure invariants; it does NOT relax them — the computed closure engines
        # (validate_closure), the invariant/cluster/warning checks in
        # validate_transition, and the structural no-fabrication / containment
        # rules all continue to fire unchanged for goal-driven runs. A coherent,
        # goal-bound manifest -> the deterministic verify-evidence demands are met,
        # so return before requesting the verify-selection / readiness artifacts.
        # An INCOHERENT / unbound / missing manifest appends its own blocker(s) and
        # returns (BLOCKED). A STANDARD run falls straight through to the unchanged
        # gate body below — the track read is the ONLY new statement on its path
        # and resolves fail-safe to "standard".
        if self._run_track(run_id) == "goal-driven":
            self._validate_goal_driven_closure_gate(run_id, blockers)
            return
        selection_rel = f"verification/{run_id}-verify-selection.yaml"
        readiness_rel = f"verification/{run_id}-resolve-readiness.yaml"
        package_rel = f"verification/{run_id}"
        selection = self._load_yaml_under_root(selection_rel, blockers, "adaptive_verify_evidence_gate")
        if selection is not None:
            if selection.get("kind") != "uacp.verification_package":
                blockers.append("adaptive_verify_evidence_gate: verify-selection kind must be uacp.verification_package")
            if selection.get("run_id") != run_id:
                blockers.append("adaptive_verify_evidence_gate: verify-selection run_id mismatch")
        readiness = self._load_yaml_under_root(readiness_rel, blockers, "adaptive_verify_evidence_gate")
        if readiness is not None:
            if readiness.get("kind") != "uacp.verify_resolve_readiness":
                blockers.append("adaptive_verify_evidence_gate: resolve-readiness kind must be uacp.verify_resolve_readiness")
            if readiness.get("run_id") != run_id:
                blockers.append("adaptive_verify_evidence_gate: resolve-readiness run_id mismatch")
            if readiness.get("ready_for_resolve") is not True:
                blockers.append("adaptive_verify_evidence_gate: ready_for_resolve must be true")
            if readiness.get("verification_package") != selection_rel:
                blockers.append("adaptive_verify_evidence_gate: readiness must bind to verify-selection artifact")
            for blocker in readiness.get("blockers") or []:
                if isinstance(blocker, Mapping) and blocker.get("state") == "open":
                    blockers.append("adaptive_verify_evidence_gate: open blocker in resolve readiness")
        piv_assessment_rel = f"verification/{run_id}-piv-assessment.yaml"
        artifacts = [selection_rel, readiness_rel]
        if (self.governed_root / piv_assessment_rel).exists():
            artifacts.append(piv_assessment_rel)
        self._offline_validate_artifacts(artifacts, blockers, "adaptive_verify_evidence_gate")
        if not self._dir_under_root_exists(package_rel):
            blockers.append(f"adaptive_verify_evidence_gate: missing verification package directory {package_rel}/")

    def _validate_adaptive_resolve_closure_gate(self, artifact: Mapping[str, Any], blockers: list[str]) -> None:
        if str(artifact.get("from_phase") or "") != "resolve":
            return
        # F-T3-01 (SECURITY): fail CLOSED — see _validate_adaptive_execute_evidence_gate.
        # An absent or non-mapping adaptive_resolve_closure_gate key must not disable enforcement.
        run_id = str(artifact.get("run_id") or "")
        if not run_id:
            blockers.append("adaptive_resolve_closure_gate requires run_id")
            return
        selection_rel = f"resolutions/{run_id}-resolve-selection.yaml"
        closure_rel = f"resolutions/{run_id}-closure.yaml"
        readiness_rel = f"verification/{run_id}-resolve-readiness.yaml"
        package_rel = f"resolutions/{run_id}"
        selection = self._load_yaml_under_root(selection_rel, blockers, "adaptive_resolve_closure_gate")
        if selection is not None:
            if selection.get("kind") != "uacp.resolve_package":
                blockers.append("adaptive_resolve_closure_gate: resolve-selection kind must be uacp.resolve_package")
            if selection.get("run_id") != run_id:
                blockers.append("adaptive_resolve_closure_gate: resolve-selection run_id mismatch")
            if selection.get("verify_resolve_readiness") != readiness_rel:
                blockers.append("adaptive_resolve_closure_gate: resolve-selection must bind run readiness")
        closure = self._load_yaml_under_root(closure_rel, blockers, "adaptive_resolve_closure_gate")
        if closure is not None:
            if closure.get("kind") != "uacp.resolve_closure":
                blockers.append("adaptive_resolve_closure_gate: closure kind must be uacp.resolve_closure")
            if closure.get("run_id") != run_id:
                blockers.append("adaptive_resolve_closure_gate: closure run_id mismatch")
            if closure.get("resolve_package") != selection_rel:
                blockers.append("adaptive_resolve_closure_gate: closure must bind resolve package")
            decision = closure.get("final_decision") if isinstance(closure.get("final_decision"), Mapping) else {}
            if decision.get("status") not in {"resolved", "resolved_with_warnings"}:
                blockers.append("adaptive_resolve_closure_gate: closure final_decision is not resolved")
        readiness = self._load_yaml_under_root(readiness_rel, blockers, "adaptive_resolve_closure_gate")
        if readiness is not None and readiness.get("ready_for_resolve") is not True:
            blockers.append("adaptive_resolve_closure_gate: VERIFY readiness is not ready")
        self._offline_validate_artifacts([readiness_rel, selection_rel, closure_rel], blockers, "adaptive_resolve_closure_gate")
        if not self._dir_under_root_exists(package_rel):
            blockers.append(f"adaptive_resolve_closure_gate: missing resolve package directory {package_rel}/")

    def _ppv_rule(self) -> Mapping[str, Any]:
        """Resolve the ppv_rule.

        Slice 4b T4c-2: the rule grammar (ledger_required, the ppv_* check ids,
        ledger_required_fields, max_attempts, second_failure_action) is codified
        in engines.domain.gate_rules. The block is read from the loaded
        phase-transitions config WHEN PRESENT (production behavior, unchanged);
        when ABSENT it falls back to the code default whose ``ledger_required``
        is True (enforce-by-default / fail-closed: a PPV pass record is required
        on every transition). No operator-tunable knob this wave.

        A test fixture may opt OUT by supplying ``ppv_rule: {ledger_required:
        false}``: present-with-falsy-ledger_required is read as the loaded value,
        so the reader's ``not ppv_rule.get("ledger_required")`` short-circuits the
        gate exactly as the pre-T4c-2 absent block did.
        """
        if "ppv_rule" in self.config:
            return self.config.get("ppv_rule") or {}
        from engines.domain.gate_rules import ppv_rule_default

        return ppv_rule_default()

    def _validate_ppv_record(self, artifact: Mapping[str, Any], blockers: list[str]) -> None:
        """Phase 1 / Item 1.4: require a PPV pass record in the ledger before
        Heartgate accepts a transition for which ppv_rule applies.

        (PPV = the legacy post-phase-verification ledger rule; distinct from the
        newer Phase Intent Verification contract.)

        Tech-F1 remediation: sanitize run_id before constructing the ledger
        path (reject path-traversal characters and resolve under
        state/gate-ledger/ only). Skeptic F5 remediation: tolerate malformed
        ppv_rule fields with explicit blockers instead of crashing.

        Global review R1 (SKEP-G-002): generalize the per-check pass
        evidence pattern Phase 3 R1 introduced for PLAN_VALIDATION.
        ppv_rule declares `ledger_required_fields: [ppv_attempt, result,
        checks]`; when present, the kernel verifies each declared
        ppv_check_id appears in the ledger record's `checks` list AND
        has explicit per-check pass evidence (mapping-form or sibling
        `check_results: {ppv_id: pass}`).
        """
        ppv_rule = self._ppv_rule()
        if not isinstance(ppv_rule, Mapping) or not ppv_rule.get("ledger_required"):
            return
        run_id = str(artifact.get("run_id") or "")
        if not run_id:
            blockers.append("ppv_rule requires run_id to verify ledger record")
            return
        if not _is_safe_run_id(run_id):
            blockers.append("ppv_rule: unsafe run_id rejected for ledger lookup")
            return
        ledger_path = self.governed_root / "state" / "gate-ledger" / f"{run_id}.jsonl"
        if not ledger_path.exists():
            blockers.append(f"ppv_rule unmet: no gate ledger at {ledger_path.relative_to(self.governed_root)}")
            return
        from_phase = str(artifact.get("from_phase") or "")
        # Precompute declared ppv_ids when ppv_rule.checks is present.
        declared_check_ids: set[str] = set()
        for c in (ppv_rule.get("checks") or []):
            if isinstance(c, Mapping):
                cid = str(c.get("id") or "").strip()
                if cid:
                    declared_check_ids.add(cid)
        ledger_required_fields = [str(f) for f in (ppv_rule.get("ledger_required_fields") or []) if isinstance(f, str)]
        passing_attempts: list[int] = []
        failing_attempts: list[int] = []
        passing_record_defects: list[str] = []
        try:
            for lineno, raw_line in enumerate(ledger_path.read_text(encoding="utf-8").splitlines(), start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception as exc:
                    # Phase 3 (pc_p2_minor): fail-closed on corrupted ledger.
                    blockers.append(f"ppv_rule: gate ledger line {lineno} unparseable: {type(exc).__name__}: {exc}")
                    return
                if str(rec.get("gate") or "") != "PPV":
                    continue
                if from_phase and str(rec.get("phase") or "") != from_phase:
                    continue
                try:
                    attempt = int(rec.get("ppv_attempt") or 0)
                except (TypeError, ValueError):
                    blockers.append(f"ppv_rule: gate ledger line {lineno} has non-integer ppv_attempt")
                    return
                result = str(rec.get("result") or "")
                if result == "pass":
                    # SKEP-G-002: when ppv_rule declares checks + required fields,
                    # this pass record must carry per-check evidence. If it doesn't,
                    # it's treated as a per-record defect and not counted as
                    # passing (multi-record DoS resistance mirrors PLAN_VALIDATION).
                    body: Mapping[str, Any] = rec["record"] if isinstance(rec.get("record"), Mapping) else rec
                    defect: str | None = None
                    if ledger_required_fields:
                        missing = [f for f in ledger_required_fields if f not in body and f not in rec]
                        if missing:
                            defect = f"line {lineno}: missing required fields {missing}"
                    if defect is None and declared_check_ids:
                        checks_in_rec = body.get("checks") if isinstance(body.get("checks"), list) else rec.get("checks")
                        if not isinstance(checks_in_rec, list):
                            defect = f"line {lineno}: 'checks' must be a list (got {type(checks_in_rec).__name__})"
                        else:
                            sibling = body.get("check_results") if isinstance(body.get("check_results"), Mapping) else rec.get("check_results")
                            recorded_ids: set[str] = set()
                            ids_with_pass: set[str] = set()
                            for entry in checks_in_rec:
                                if isinstance(entry, str):
                                    cid = entry.strip()
                                    if cid:
                                        recorded_ids.add(cid)
                                        if isinstance(sibling, Mapping) and str(sibling.get(cid) or "") == "pass":
                                            ids_with_pass.add(cid)
                                elif isinstance(entry, Mapping):
                                    cid = str(entry.get("id") or "").strip()
                                    if cid:
                                        recorded_ids.add(cid)
                                        if str(entry.get("result") or "") == "pass":
                                            ids_with_pass.add(cid)
                            missing_ids = declared_check_ids - recorded_ids
                            extra_ids = recorded_ids - declared_check_ids
                            unproven = declared_check_ids - ids_with_pass
                            if missing_ids:
                                defect = f"line {lineno}: missing required ppv_ids {sorted(missing_ids)}"
                            elif extra_ids:
                                defect = f"line {lineno}: unknown ppv_ids {sorted(extra_ids)}"
                            elif unproven:
                                defect = f"line {lineno}: missing per-check pass evidence for {sorted(unproven)}"
                    if defect:
                        passing_record_defects.append(defect)
                        continue
                    passing_attempts.append(attempt)
                elif result in {"warn", "block", "fail"}:
                    failing_attempts.append(attempt)
        except Exception as exc:
            blockers.append(f"ppv_rule ledger read failed: {type(exc).__name__}: {exc}")
            return
        raw_max = ppv_rule.get("max_attempts")
        if raw_max is None:
            raw_max = 2
        try:
            max_attempts = int(raw_max)
        except (TypeError, ValueError):
            blockers.append("ppv_rule.max_attempts must be a positive integer")
            return
        if max_attempts <= 0:
            blockers.append("ppv_rule.max_attempts must be >= 1")
            return
        # Skeptic F2 remediation: second-failure block is the default action.
        # Only an explicit known relaxation value bypasses it.
        action = str(ppv_rule.get("second_failure_action") or "block_unconditional")
        if action not in {"block_unconditional", "warn"}:
            blockers.append(f"ppv_rule.second_failure_action unknown value '{action}'")
            return
        if len(failing_attempts) >= max_attempts and action == "block_unconditional":
            blockers.append(
                f"ppv_rule: {len(failing_attempts)} failed PPV attempts for phase '{from_phase}' — second-failure unconditional block"
            )
            return
        if not passing_attempts:
            detail = f" (per-record defects: {passing_record_defects})" if passing_record_defects else ""
            blockers.append(f"ppv_rule unmet: no PPV pass record in ledger for phase '{from_phase}'{detail}")

    def _glob_matches_any(self, pattern: str) -> bool:
        """Phase 1 remediation (skeptic F3): reject symlinks and out-of-root
        matches. A glob match must resolve to a real file under UACP_ROOT and
        not be a symlink whose target is outside the root.
        """
        import glob as _glob
        try:
            root = self.governed_root.resolve()
            matches = _glob.glob(str(self.governed_root / pattern), recursive=True)
            for raw in matches:
                p = Path(raw)
                if p.is_symlink():
                    # Resolve and re-check that the target is inside UACP_ROOT.
                    try:
                        resolved = p.resolve(strict=True)
                    except Exception:
                        continue
                    if root != resolved and root not in resolved.parents:
                        continue
                    # symlink to in-root real file is acceptable
                else:
                    try:
                        resolved = p.resolve(strict=True)
                    except Exception:
                        continue
                if not resolved.is_file():
                    continue
                if root != resolved and root not in resolved.parents:
                    continue
                return True
            return False
        except Exception:
            return False

    def _ledger_contains_gate(self, run_id: str, gate: str) -> bool:
        if not _is_safe_run_id(run_id):
            return False
        ledger_path = self.governed_root / "state" / "gate-ledger" / f"{run_id}.jsonl"
        if not ledger_path.exists():
            return False
        try:
            for line in ledger_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                # Phase 3 (pc_p2_minor): a corrupted line in the ledger is
                # treated as fail-closed; callers should re-derive coverage
                # rather than silently skip suspicious lines.
                try:
                    rec = json.loads(line)
                except Exception:
                    return False
                if str(rec.get("gate") or "") == gate:
                    return True
        except Exception:
            return False
        return False

    def _validate_intent_doc(self, artifact: Mapping[str, Any], blockers: list[str]) -> None:
        """Phase 2.3: TRIAGE->PROPOSE requires proposals/{run_id}-intent.md
        with the four required sections.
        """
        schema = (self.artifact_schemas.get("intent") or {})
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

    def _validate_scope_artifact(self, artifact: Mapping[str, Any], blockers: list[str], warnings: list[str]) -> None:
        """Phase 2.1: PLAN->EXECUTE requires plans/{run_id}-scope.yaml.
        Validates required fields, cross-checks write_paths against Layer B
        allowed_tools (pc_p1_gov_2).
        """
        schema = (self.artifact_schemas.get("scope") or {})
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
        for field_name in (schema.get("required_fields") or []):
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
                "scope.write_paths is empty (write authority cannot be inferred from absence; either declare at least one path or set 'no_writes_intended: true')"
            )
            return
        execute_stage = (self.stages.get("execute") or {})
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
                    f"scope.write_paths cross-check: '{wp_str}' is not reachable by any execute-phase allowed_tool"
                )

    def _self_patch_authorizes_path(self, scope: Mapping[str, Any], write_path: str, blockers: list[str]) -> bool:
        """Narrow bootstrap escape hatch for UACP self-repair paths.

        This does not make terminal/patch a general governed writer. It only lets
        Heartgate accept specific UACP self-patch paths when the scope carries an
        explicit authority block with owner, rollback, and verification duties.
        """
        auth = scope.get("self_patch_write_authority")
        if not isinstance(auth, Mapping) or not bool(auth.get("enabled")):
            return False
        for field_name in ("reason", "authority_artifact", "owner", "rollback_path", "verification_obligations"):
            if auth.get(field_name) in (None, "", []):
                blockers.append(f"self_patch_write_authority missing {field_name}")
                return False
        obligations = auth.get("verification_obligations")
        if not isinstance(obligations, list) or not all(isinstance(item, str) and item.strip() for item in obligations):
            blockers.append("self_patch_write_authority.verification_obligations must be a non-empty list of strings")
            return False
        allowed = auth.get("allowed_prefixes") or ["skills/devops/uacp/", "scripts/", "runtime-adapters/"]
        if not isinstance(allowed, list):
            blockers.append("self_patch_write_authority.allowed_prefixes must be a list")
            return False
        safe_prefixes = {"skills/devops/uacp/", "scripts/", "runtime-adapters/"}
        cleaned = [str(prefix) for prefix in allowed if isinstance(prefix, str) and prefix in safe_prefixes]
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
                cleaned = [str(p) for p in prefixes if isinstance(p, str) and str(p).strip() not in forbidden_prefixes]
            elif isinstance(prefixes, str) and prefixes.strip() not in forbidden_prefixes:
                cleaned = [prefixes]
            else:
                cleaned = []
            if cleaned:
                result[tool] = cleaned
        return result

    def _validate_evidence_dispositions(self, artifact: Mapping[str, Any], blockers: list[str]) -> None:
        """Phase 2.2: VERIFY->RESOLVE requires verified-facts + assumptions
        pair files for each required cluster. Pending assumptions without
        owner/next_phase_obligation block.
        """
        schema = (self.artifact_schemas.get("evidence_disposition") or {})
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
            return bool(e.get("artifact_path")) and bool(e.get("owner")) and bool(e.get("rationale"))
        handled_valid = isinstance(handled_chain, list) and any(_valid_handled(c) for c in handled_chain)
        exc_valid = isinstance(accepted_exc, list) and any(_valid_exception(e) for e in accepted_exc)
        has_escape_hatch = handled_valid or exc_valid
        if len(cluster_summary) == 0:
            if not has_escape_hatch:
                blockers.append("evidence_disposition: cluster_summary is empty at VERIFY->RESOLVE (must declare at least one cluster or non-empty handled_findings_chain/accepted_exceptions)")
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
            blockers.append("evidence_disposition: all clusters are not_applicable/deferred and no handled_findings_chain or accepted_exceptions declared (silent skip not allowed)")
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
            cross = (self.artifact_schemas.get("cross_checks") or {})
            minc = (cross.get("evidence_disposition_minimum_content") or {})
            facts_req = str(minc.get("verified_facts_required_header_substring") or "")
            assump_req = str(minc.get("assumptions_required_header_substring") or "")
            for tmpl, label, required_substring in (
                (facts_tmpl, "verified-facts", facts_req),
                (assumptions_tmpl, "assumptions", assump_req),
            ):
                rel = tmpl.replace("{run_id}", run_id).replace("{cluster}", cluster_id)
                p = self.governed_root / rel
                if not p.exists():
                    blockers.append(f"evidence_disposition: missing {label} for cluster '{cluster_id}': {rel}")
                    continue
                if required_substring:
                    try:
                        body = p.read_text(encoding="utf-8")
                    except Exception:
                        body = ""
                    if required_substring not in body:
                        blockers.append(
                            f"evidence_disposition: {label} file for cluster '{cluster_id}' is empty or missing required header '{required_substring}': {rel}"
                        )
            # Inspect assumptions for unowned 'pending' rows.
            assumptions_rel = assumptions_tmpl.replace("{run_id}", run_id).replace("{cluster}", cluster_id)
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
                        f"evidence_disposition: cluster '{cluster_id}' assumptions table has unexpected column count ({len(cells)} != 4)"
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
                        f"evidence_disposition: cluster '{cluster_id}' assumptions table has unexpected column count ({len(cells)} != 4)"
                    )
                    column_count_warned = True
                continue
            disposition = cells[1].lower()
            owner = cells[2]
            next_obl = cells[3]
            if disposition == "pending" and (not owner or not next_obl):
                blockers.append(
                    f"evidence_disposition: cluster '{cluster_id}' has unowned 'pending' assumption: {cells[0][:60]}"
                )
        # If the file had table-like rows but no canonical header was ever seen,
        # the table is structurally malformed for the disposition contract.
        if saw_pipe_row and state == 0 and not column_count_warned:
            blockers.append(
                f"evidence_disposition: cluster '{cluster_id}' assumptions table missing canonical header '| Assumption | Disposition | Owner | Next-phase obligation |'"
            )

    def _plan_validation_gate_rule(self) -> Mapping[str, Any]:
        """Resolve the plan_validation_gate rule.

        Slice 4b T4c-2: the rule grammar (required_ledger_gate_for_transition,
        ledger_gate_name, ledger_required_fields, ledger_required_phase, and the
        pv_* check ids) is codified in engines.domain.gate_rules. The block is
        read from the loaded phase-transitions config WHEN PRESENT (production
        behavior, unchanged); when ABSENT it falls back to the code default
        (enforce-by-default / fail-closed). No operator-tunable knob this wave —
        the grammar is non-tunable.

        A test fixture may opt OUT by supplying an empty mapping for the block
        (preserving prior test laxity): an explicit ``{}`` is read as present and
        yields no ``required_ledger_gate_for_transition``, so the reader's
        ``if not required_for: return`` short-circuits the gate exactly as before.
        """
        if "plan_validation_gate" in self.config:
            return self.config.get("plan_validation_gate") or {}
        from engines.domain.gate_rules import plan_validation_gate_default

        return plan_validation_gate_default()

    def _validate_plan_validation_gate(self, artifact: Mapping[str, Any], blockers: list[str], warnings: list[str] | None = None) -> None:
        """Phase 3.1: a PLAN_VALIDATION ledger entry with result=pass is
        required for PLAN->EXECUTE. The entry must be tagged phase=plan and
        carry a `checks:` list naming every pv_id declared in
        config/phase-transitions.yaml plan_validation_gate.checks.

        Phase 3 R1 hardening (SKEP-001 / GOV-004): the kernel does not just
        verify gate presence; it enforces the ledger schema so a single-bit
        "PLAN_VALIDATION: pass" assertion is no longer enough.
        """
        rule = self._plan_validation_gate_rule()
        if not isinstance(rule, Mapping):
            return
        required_for = str(rule.get("required_ledger_gate_for_transition") or "")
        if not required_for:
            return
        from_phase = str(artifact.get("from_phase") or "")
        to_phase = str(artifact.get("to_phase") or "")
        if f"{from_phase}->{to_phase}" != required_for:
            return
        run_id = str(artifact.get("run_id") or "")
        if not _is_safe_run_id(run_id):
            blockers.append("plan_validation_gate: unsafe or missing run_id")
            return
        gate_name = str(rule.get("ledger_gate_name") or "PLAN_VALIDATION")
        # Pre-compute the set of pv_ids the ledger record must cover.
        declared_check_ids: set[str] = set()
        for c in (rule.get("checks") or []):
            if isinstance(c, Mapping):
                cid = str(c.get("id") or "").strip()
                if cid:
                    declared_check_ids.add(cid)
        # Required-field policy for the ledger record (mirrors ppv_rule.ledger_required_fields).
        ledger_required_fields = [str(f) for f in (rule.get("ledger_required_fields") or ["phase", "checks", "result"]) if isinstance(f, str)]
        required_phase = str(rule.get("ledger_required_phase") or "plan")
        ledger_path = self.governed_root / "state" / "gate-ledger" / f"{run_id}.jsonl"
        if not ledger_path.exists():
            blockers.append(f"plan_validation_gate: missing {gate_name} ledger entry (no ledger file at {ledger_path.relative_to(self.governed_root)})")
            return
        try:
            raw = ledger_path.read_text(encoding="utf-8")
        except Exception as exc:
            blockers.append(f"plan_validation_gate: ledger unreadable: {type(exc).__name__}")
            return
        # Phase 3 R2 (SKEP-R1-007): scan ALL PLAN_VALIDATION pass records and
        # accept if ANY satisfies the contract. First-defect-wins semantics
        # turned the ledger into a DoS surface — any caller could append a
        # bad PLAN_VALIDATION record to block the gate forever. Per-record
        # defects now accumulate as warnings on the transition; only the
        # absence of ANY valid record blocks.
        candidate_defects: list[str] = []
        found_pass = False
        for line_no, line in enumerate(raw.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception as exc:
                # Corrupt lines still block: ledger integrity is foundational.
                blockers.append(f"plan_validation_gate: gate ledger line {line_no} unparseable: {type(exc).__name__}: {exc}")
                return
            if str(rec.get("gate") or "") != gate_name:
                continue
            if str(rec.get("result") or "") != "pass":
                continue
            # Reject entries from the wrong phase (must be plan).
            rec_phase = str(rec.get("phase") or "")
            if not rec_phase and isinstance(rec.get("record"), Mapping):
                rec_phase = str(rec["record"].get("phase") or "")
            if rec_phase != required_phase:
                candidate_defects.append(f"line {line_no}: phase '{rec_phase}' != required '{required_phase}'")
                continue
            body: Mapping[str, Any] = rec["record"] if isinstance(rec.get("record"), Mapping) else rec
            missing_fields = [f for f in ledger_required_fields if f not in body and f not in rec]
            if missing_fields:
                candidate_defects.append(f"line {line_no}: missing required fields {missing_fields}")
                continue
            checks_in_rec = body.get("checks") if isinstance(body.get("checks"), list) else rec.get("checks")
            if not isinstance(checks_in_rec, list):
                candidate_defects.append(f"line {line_no}: 'checks' must be a list (got {type(checks_in_rec).__name__})")
                continue
            sibling_results = body.get("check_results") if isinstance(body.get("check_results"), Mapping) else rec.get("check_results")
            if sibling_results is not None and not isinstance(sibling_results, Mapping):
                candidate_defects.append(f"line {line_no}: 'check_results' must be a mapping")
                continue
            recorded_ids: set[str] = set()
            ids_with_pass_evidence: set[str] = set()
            per_check_defects: list[str] = []
            for entry in checks_in_rec:
                if isinstance(entry, str):
                    cid = entry.strip()
                    if cid:
                        recorded_ids.add(cid)
                        # String-form: per-check pass evidence must come from sibling check_results.
                        if isinstance(sibling_results, Mapping) and str(sibling_results.get(cid) or "") == "pass":
                            ids_with_pass_evidence.add(cid)
                elif isinstance(entry, Mapping):
                    cid = str(entry.get("id") or "").strip()
                    if cid:
                        recorded_ids.add(cid)
                        per_check_result = str(entry.get("result") or "")
                        if per_check_result == "pass":
                            ids_with_pass_evidence.add(cid)
                        elif per_check_result and per_check_result != "pass":
                            per_check_defects.append(f"check '{cid}' has non-pass result")
            if per_check_defects:
                candidate_defects.append(f"line {line_no}: " + "; ".join(per_check_defects))
                continue
            missing_ids = declared_check_ids - recorded_ids
            if missing_ids:
                candidate_defects.append(f"line {line_no}: missing required pv_ids {sorted(missing_ids)}")
                continue
            # SKEP-R1-006: reject extra/unknown pv_ids.
            extra_ids = recorded_ids - declared_check_ids
            if extra_ids:
                candidate_defects.append(f"line {line_no}: carries unknown pv_ids {sorted(extra_ids)}")
                continue
            # SKEP-R1-003: each declared pv_id must have explicit per-check pass evidence.
            unproven = declared_check_ids - ids_with_pass_evidence
            if unproven:
                candidate_defects.append(f"line {line_no}: missing per-check pass evidence for {sorted(unproven)}")
                continue
            # This record satisfies the full contract.
            found_pass = True
            break
        if not found_pass:
            detail = f" (per-record defects: {candidate_defects})" if candidate_defects else ""
            blockers.append(f"plan_validation_gate: no '{gate_name}' pass record in ledger for run '{run_id}'{detail}")
        elif candidate_defects and warnings is not None:
            warnings.append(f"plan_validation_gate: earlier PLAN_VALIDATION records were rejected before a clean one was accepted: {candidate_defects}")

    @staticmethod
    def _canon_write_path(p: Any) -> str:
        """SKEP-003 / TECH-002 remediation: canonicalize a write_path entry
        into a POSIX-segment-normalized form ending with '/'. Strips leading
        './' and '/', collapses repeated separators, rejects '..' segments.
        Returns empty string when the entry is unusable.
        """
        from pathlib import PurePosixPath
        s = str(p).strip()
        if not s:
            return ""
        # Reject absolute paths and parent-escape; both are policy violations.
        if s.startswith("/") or s in {".", ".."}:
            return ""
        try:
            pp = PurePosixPath(s)
        except Exception:
            return ""
        parts = [seg for seg in pp.parts if seg not in (".",)]
        if any(seg == ".." for seg in parts):
            return ""
        norm = "/".join(parts)
        if not norm:
            return ""
        return norm + "/"

    @classmethod
    def _paths_overlap(cls, a_raw: Any, b_raw: Any) -> bool:
        """SKEP-003: two write_paths overlap iff one is an ancestor of the
        other after canonicalization. Bare-prefix tricks ('plans' vs
        'plans-other') no longer match; './plans/' and 'plans/' canonicalize
        to the same value.
        """
        a = cls._canon_write_path(a_raw)
        b = cls._canon_write_path(b_raw)
        if not a or not b:
            return False
        return a == b or a.startswith(b) or b.startswith(a)

    def _run_registry_rule(self) -> Mapping[str, Any]:
        """Resolve the run_registry_rule.

        Slice 4b T4c-1: the rule grammar (registry_path, required_for_transition,
        writer_tool) is codified in engines.domain.gate_rules. The block is read
        from the loaded phase-transitions config WHEN PRESENT (production
        behavior, unchanged); when ABSENT it falls back to the code default whose
        operator-tunable ``enforcement`` mode comes from config/uacp.toml
        [heartgate.run_registry]. A fixture may opt out via an empty mapping.
        """
        if "run_registry_rule" in self.config:
            return self.config.get("run_registry_rule") or {}
        from engines.domain.gate_rules import run_registry_rule_default

        enforcement = None
        try:
            cfg_raw = get_config(self.uacp_root).model_dump()
            knob = (cfg_raw.get("heartgate") or {}).get("run_registry") or {}
            if isinstance(knob, Mapping):
                value = knob.get("enforcement")
                enforcement = value if isinstance(value, str) else None
        except Exception:
            enforcement = None
        return run_registry_rule_default(enforcement=enforcement)

    def _validate_run_registry_overlap(self, artifact: Mapping[str, Any], blockers: list[str], warnings: list[str]) -> None:
        """Phase 3.2: detect write-path overlap with other active runs.

        Reads state/run-registry.yaml; for each entry in active_runs whose
        run_id != this artifact's run_id, compute path intersection. Any
        overlap with the active scope.write_paths blocks PLAN->EXECUTE.

        Phase 3 R1 hardening: malformed registry entries now block
        (SKEP-010), path normalization uses PurePosixPath segment match
        (SKEP-003), and the required transition is read from config
        (TECH-003).
        """
        rule = self._run_registry_rule()
        if not isinstance(rule, Mapping) or not rule:
            return
        from_phase = str(artifact.get("from_phase") or "")
        to_phase = str(artifact.get("to_phase") or "")
        required_for = str(rule.get("required_for_transition") or "plan->execute")
        if f"{from_phase}->{to_phase}" != required_for:
            return
        run_id = str(artifact.get("run_id") or "")
        if not _is_safe_run_id(run_id):
            return
        registry_rel = str(rule.get("registry_path") or "state/run-registry.yaml")
        registry_path = self.governed_root / registry_rel
        if not registry_path.exists():
            # No registry yet — emit a warning so it is observable but do not
            # block; runs that pre-date the registry must not be blocked
            # retroactively. Once at least one run has registered, overlap
            # detection is active for all subsequent transitions.
            warnings.append("run_registry: state/run-registry.yaml not yet present")
            return
        if yaml is None:
            blockers.append("run_registry: PyYAML required to validate registry")
            return
        try:
            data = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            blockers.append(f"run_registry: registry unparseable: {type(exc).__name__}")
            return
        if not isinstance(data, Mapping):
            blockers.append("run_registry: top-level value must be a YAML mapping")
            return
        active = data.get("active_runs", [])
        if active is None:
            active = []
        if not isinstance(active, list):
            blockers.append("run_registry: 'active_runs' must be a list")
            return
        # Load the active run's scope to extract its write_paths.
        scope_path = self.governed_root / "plans" / f"{run_id}-scope.yaml"
        if not scope_path.exists():
            return  # scope_artifact validator handles missing-scope blockers
        try:
            scope = yaml.safe_load(scope_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            blockers.append(f"run_registry: scope unparseable for overlap check: {type(exc).__name__}")
            return
        my_writes = scope.get("write_paths") or []
        if not isinstance(my_writes, list):
            blockers.append("run_registry: scope.write_paths must be a list for overlap check")
            return
        for idx, entry in enumerate(active):
            if not isinstance(entry, Mapping):
                blockers.append(f"run_registry: active_runs[{idx}] must be a mapping")
                continue
            other_id = str(entry.get("run_id") or "")
            if other_id == run_id:
                continue
            if not other_id or not _is_safe_run_id(other_id):
                blockers.append(f"run_registry: active_runs[{idx}].run_id missing or unsafe")
                continue
            other_writes = entry.get("write_paths") or []
            if not isinstance(other_writes, list):
                blockers.append(f"run_registry: active_runs[{idx}].write_paths must be a list")
                continue
            for a in my_writes:
                for b in other_writes:
                    if self._paths_overlap(a, b):
                        ac = self._canon_write_path(a) or str(a)
                        bc = self._canon_write_path(b) or str(b)
                        blockers.append(
                            f"run_registry: write_paths overlap with active run '{other_id}' on '{ac}' / '{bc}'"
                        )

    def _validate_lessons_artifact(self, artifact: Mapping[str, Any], blockers: list[str]) -> None:
        """Phase 2.4: VERIFY->RESOLVE requires resolutions/{run_id}-lessons.yaml
        with structured schema (run_id + lessons list).
        """
        schema = (self.artifact_schemas.get("lessons") or {})
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
        for field_name in (schema.get("required_fields") or []):
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
            if not (item.get("id") and item.get("accepted_by") and item.get("owner") and item.get("rationale") and item.get("next_phase_acceptance")):
                continue
            run_id = str(artifact.get("run_id") or "")
            if not artifact_path.startswith(("verification/", "resolutions/")):
                continue
            if run_id and not artifact_path.startswith((f"verification/{run_id}", f"resolutions/{run_id}")):
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
        return bool(item.get("id") and item.get("cluster_id") and item.get("owner") and item.get("condition") and item.get("accepted_by") and item.get("next_phase_acceptance"))

    def _warnings_owned(self, warnings: Any) -> bool:
        for item in warnings:
            if not isinstance(item, Mapping):
                return False
            if not (item.get("owner") and item.get("residual_risk")):
                return False
        return True
