"""Adaptive package / evidence / closure gates (A3.2 extraction from the god-class).

The five per-transition adaptive gates the Heartgate hub runs from
``validate_transition`` (PROPOSE->PLAN package selection, PLAN->EXECUTE package
selection, and the EXECUTE/VERIFY/RESOLVE evidence + closure gates). Carved out of
the ``Heartgate`` god-class (design/graph-engine nodes 30/31, seam #4) as free
functions that receive the gate instance (``hg``) for the sibling helpers and
state they read (``hg.config`` / ``hg.governed_root`` / ``hg._load_yaml_under_root``
/ ``hg._offline_validate_artifacts`` / ``hg._run_track`` / ...). The hub keeps thin
delegating methods so the orchestrator AND the tests that drive each gate directly
are unaffected.

Behaviour-preserving: each function body is AST-identical to the original method
(only ``self`` -> ``hg``). The ~70% copy-paste across the two package gates
(distinct blocker-message prefixes + per-gate extra checks) is NOT yet unified —
that DRY refactor changes governance behaviour at the margins (asserted blocker
strings), so it is deferred to a dedicated TDD increment now that the gates are
co-located here.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..heartgate import Heartgate

try:
    import yaml
except ImportError:  # pragma: no cover - Hermes ships with PyYAML in normal use.
    yaml = None  # type: ignore[assignment]


def _scope_concern_is_keyed(hg: Heartgate, artifact_rel: str) -> bool:
    """True iff the scope concern's artifact declares a non-empty keyed
    ``scope.in_scope:[{id,statement}]`` — the D43 coverage source (the scope_item
    nodes the graph projection reads). A markdown / unstructured scope returns False.
    """
    if not artifact_rel:
        return False
    doc = hg._load_yaml_under_root(artifact_rel, [], "scope module")
    if not isinstance(doc, Mapping):
        return False
    scope = doc.get("scope")
    in_scope = scope.get("in_scope") if isinstance(scope, Mapping) else None
    if not isinstance(in_scope, list) or not in_scope:
        return False
    return all(
        isinstance(i, Mapping) and i.get("id") and i.get("statement") is not None for i in in_scope
    )


def validate_adaptive_proposal_package_gate(
    hg: Heartgate, artifact: Mapping[str, Any], blockers: list[str]
) -> None:
    """Enforce adaptive proposal package selection for PROPOSE->PLAN.

    The config declares the policy. The kernel enforces the hard minimum:
    when a transition moves from PROPOSE to PLAN and the adaptive gate is
    configured, a package-selection artifact must exist, parse, and cover
    universal core concerns plus selected module artifact references. This
    keeps YAML proposal envelopes from being treated as the whole proposal.
    """
    if (
        str(artifact.get("from_phase") or "") != "propose"
        or str(artifact.get("to_phase") or "") != "plan"
    ):
        return
    gate = hg.config.get("adaptive_proposal_package_gate") or {}
    if not isinstance(gate, Mapping):
        return
    run_id = str(artifact.get("run_id") or "")
    if not run_id:
        blockers.append("adaptive_proposal_package_gate requires run_id")
        return
    selection_rel = f"proposals/{run_id}-package-selection.yaml"
    package_rel = f"proposals/{run_id}"
    selection_path = hg.governed_root / selection_rel
    package_path = hg.governed_root / package_rel
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
        blockers.append(
            "adaptive_proposal_package_gate: package-selection kind must be "
            "uacp.proposal_package_selection"
        )
    from engines.domain.gate_rules import PROPOSAL_REQUIRED_UNIVERSAL_CORE

    required_core = list(gate.get("required_universal_core") or []) or list(
        PROPOSAL_REQUIRED_UNIVERSAL_CORE
    )
    core = (
        selection.get("universal_core")
        if isinstance(selection.get("universal_core"), Mapping)
        else {}
    )
    for key in required_core:
        item = core.get(str(key)) if isinstance(core, Mapping) else None
        if not isinstance(item, Mapping):
            blockers.append(f"adaptive_proposal_package_gate: universal_core.{key} missing")
            continue
        status = str(item.get("status") or "")
        if status == "covered":
            artifact_path = str(item.get("artifact") or "")
            if not artifact_path or not hg._artifact_path_exists(artifact_path):
                blockers.append(
                    f"adaptive_proposal_package_gate: universal_core.{key} artifact missing"
                )
        elif status == "not_applicable":
            hg._validate_package_na(selection_rel, f"universal_core.{key}", item, blockers)
        else:
            blockers.append(
                f"adaptive_proposal_package_gate: universal_core.{key} status must be "
                "covered|not_applicable"
            )
    # D43 (Option C) — the scope concern must be COVERED by a keyed scope module
    # (scope.in_scope:[{id,statement}]), not markdown / not_applicable, so the
    # coverage graph has scope_items to verify (GP_UNCOVERED_INTENT at plan_exit /
    # closure). Only governed package-selection runs reach this gate, so bare /
    # mechanical runs are unaffected. This is what makes intent coverage mandatory
    # rather than skippable for the package-selection representation.
    scope_concern = core.get("scope") if isinstance(core, Mapping) else None
    scope_artifact_rel = (
        str(scope_concern.get("artifact") or "") if isinstance(scope_concern, Mapping) else ""
    )
    if not (isinstance(scope_concern, Mapping) and str(scope_concern.get("status")) == "covered"):
        blockers.append(
            "adaptive_proposal_package_gate: scope must be 'covered' by a keyed scope module "
            "(scope.in_scope:[{id,statement}]); D43 coverage requires structured intents"
        )
    elif not _scope_concern_is_keyed(hg, scope_artifact_rel):
        blockers.append(
            "adaptive_proposal_package_gate: scope artifact must declare a non-empty keyed "
            "scope.in_scope:[{id,statement}] (D43)"
        )
    elif scope_artifact_rel not in hg._registered_artifact_rels(run_id):
        # D43 Option B — the keyed scope module must also be REGISTERED in the run
        # manifest (manifest.artifacts), not merely present on disk: graph projection
        # reads only registered artifacts, so an unregistered scope module yields no
        # scope_item nodes and the forced plan_exit coverage gate (GP_UNCOVERED_INTENT)
        # would have nothing to enforce. Requiring registration is what makes intent
        # coverage BIND for the package-selection representation, not just the keyed
        # uacp.proposal entity-write path (which auto-registers).
        blockers.append(
            "adaptive_proposal_package_gate: keyed scope module "
            f"'{scope_artifact_rel}' must be registered in the run manifest "
            "(uacp_run_registry_update / register-artifact) so coverage binds (D43 Option B)"
        )
    modules = (
        selection.get("selected_modules")
        if isinstance(selection.get("selected_modules"), Mapping)
        else {}
    )
    if not modules:
        blockers.append("adaptive_proposal_package_gate: selected_modules must not be empty")
    for name, item in modules.items() if isinstance(modules, Mapping) else []:
        if not isinstance(item, Mapping):
            blockers.append(
                f"adaptive_proposal_package_gate: selected_modules.{name} must be a mapping"
            )
            continue
        if not item.get("reason"):
            blockers.append(
                f"adaptive_proposal_package_gate: selected_modules.{name} missing reason"
            )
        artifact_path = str(item.get("artifact") or "")
        if not artifact_path or not hg._artifact_path_exists(artifact_path):
            blockers.append(
                f"adaptive_proposal_package_gate: selected_modules.{name} artifact missing"
            )
    na = (
        selection.get("not_applicable")
        if isinstance(selection.get("not_applicable"), Mapping)
        else {}
    )
    for name, item in na.items() if isinstance(na, Mapping) else []:
        hg._validate_package_na(selection_rel, f"not_applicable.{name}", item, blockers)


def validate_adaptive_plan_package_gate(
    hg: Heartgate, artifact: Mapping[str, Any], blockers: list[str]
) -> None:
    """Enforce adaptive PLAN package selection for PLAN->EXECUTE."""
    if (
        str(artifact.get("from_phase") or "") != "plan"
        or str(artifact.get("to_phase") or "") != "execute"
    ):
        return
    gate = hg.config.get("adaptive_plan_package_gate") or {}
    if not isinstance(gate, Mapping):
        return
    run_id = str(artifact.get("run_id") or "")
    if not run_id:
        blockers.append("adaptive_plan_package_gate requires run_id")
        return
    selection_rel = f"plans/{run_id}-plan-selection.yaml"
    package_rel = f"plans/{run_id}"
    scope_rel = f"plans/{run_id}-scope.yaml"
    selection_path = hg.governed_root / selection_rel
    package_path = hg.governed_root / package_rel
    scope_path = hg.governed_root / scope_rel
    if not selection_path.exists():
        blockers.append(f"adaptive_plan_package_gate: missing {selection_rel}")
        return
    if not package_path.exists() or not package_path.is_dir():
        blockers.append(
            f"adaptive_plan_package_gate: missing plan package directory {package_rel}/"
        )
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
        blockers.append(
            "adaptive_plan_package_gate: plan-selection kind must be uacp.plan_package_selection"
        )
    if selection.get("phase") != "plan":
        blockers.append("adaptive_plan_package_gate: plan-selection phase must be plan")
    from engines.domain.gate_rules import PLAN_REQUIRED_UNIVERSAL_CORE

    required_core = list(gate.get("required_universal_core") or []) or list(
        PLAN_REQUIRED_UNIVERSAL_CORE
    )
    core = (
        selection.get("universal_core")
        if isinstance(selection.get("universal_core"), Mapping)
        else {}
    )
    for key in required_core:
        item = core.get(str(key)) if isinstance(core, Mapping) else None
        if not isinstance(item, Mapping):
            blockers.append(f"adaptive_plan_package_gate: universal_core.{key} missing")
            continue
        status = str(item.get("status") or "")
        if status == "covered":
            artifact_path = str(item.get("artifact") or "")
            if not artifact_path or not hg._artifact_path_exists(artifact_path):
                blockers.append(
                    f"adaptive_plan_package_gate: universal_core.{key} artifact missing"
                )
        elif status == "not_applicable":
            hg._validate_plan_na(selection_rel, f"universal_core.{key}", item, blockers)
        else:
            blockers.append(
                f"adaptive_plan_package_gate: universal_core.{key} status must be "
                "covered|not_applicable"
            )
    modules = (
        selection.get("selected_modules")
        if isinstance(selection.get("selected_modules"), Mapping)
        else {}
    )
    if not modules:
        blockers.append("adaptive_plan_package_gate: selected_modules must not be empty")
    for name, item in modules.items() if isinstance(modules, Mapping) else []:
        if not isinstance(item, Mapping):
            blockers.append(
                f"adaptive_plan_package_gate: selected_modules.{name} must be a mapping"
            )
            continue
        if not item.get("reason"):
            blockers.append(f"adaptive_plan_package_gate: selected_modules.{name} missing reason")
        artifact_path = str(item.get("artifact") or "")
        if not artifact_path or not hg._artifact_path_exists(artifact_path):
            blockers.append(f"adaptive_plan_package_gate: selected_modules.{name} artifact missing")
    na = (
        selection.get("not_applicable")
        if isinstance(selection.get("not_applicable"), Mapping)
        else {}
    )
    for name, item in na.items() if isinstance(na, Mapping) else []:
        hg._validate_plan_na(selection_rel, f"not_applicable.{name}", item, blockers)
    readiness = selection.get("transition_readiness")
    if not isinstance(readiness, Mapping):
        blockers.append("adaptive_plan_package_gate: transition_readiness must be a mapping")
    elif readiness.get("status") not in {"ready_for_execute", "ready_with_conditions", "blocked"}:
        blockers.append("adaptive_plan_package_gate: transition_readiness.status is invalid")


def validate_adaptive_execute_evidence_gate(
    hg: Heartgate, artifact: Mapping[str, Any], blockers: list[str]
) -> None:
    if (
        str(artifact.get("from_phase") or "") != "execute"
        or str(artifact.get("to_phase") or "") != "verify"
    ):
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
    if hg._run_track(run_id) == "goal-driven":
        hg._validate_goal_driven_checkpoint_gate(run_id, blockers)
        return
    piv_rel = f"plans/{run_id}-piv.yaml"
    checkpoint_rel = f"executions/{run_id}-checkpoint-001.yaml"
    package_rel = f"executions/{run_id}"
    piv = hg._load_yaml_under_root(piv_rel, blockers, "adaptive_execute_evidence_gate")
    if piv is not None:
        if piv.get("kind") != "uacp.phase_intent_verification_contract":
            blockers.append(
                "adaptive_execute_evidence_gate: PIV contract kind must be "
                "uacp.phase_intent_verification_contract"
            )
        if piv.get("run_id") != run_id:
            blockers.append("adaptive_execute_evidence_gate: PIV contract run_id mismatch")
    checkpoint = hg._load_yaml_under_root(
        checkpoint_rel, blockers, "adaptive_execute_evidence_gate"
    )
    if checkpoint is not None:
        if checkpoint.get("kind") != "uacp.execution_checkpoint":
            blockers.append(
                "adaptive_execute_evidence_gate: checkpoint kind must be uacp.execution_checkpoint"
            )
        readiness = (
            checkpoint.get("next_phase_readiness")
            if isinstance(checkpoint.get("next_phase_readiness"), Mapping)
            else {}
        )
        if readiness.get("target_phase") != "verify":
            blockers.append(
                "adaptive_execute_evidence_gate: checkpoint target_phase must be verify"
            )
        if readiness.get("status") not in {"ready", "ready_with_deferred_items"}:
            blockers.append("adaptive_execute_evidence_gate: checkpoint is not ready for verify")
    hg._offline_validate_artifacts(
        [piv_rel, checkpoint_rel], blockers, "adaptive_execute_evidence_gate"
    )
    if not hg._dir_under_root_exists(package_rel):
        blockers.append(
            f"adaptive_execute_evidence_gate: missing execution package directory {package_rel}/"
        )


def validate_adaptive_verify_evidence_gate(
    hg: Heartgate, artifact: Mapping[str, Any], blockers: list[str]
) -> None:
    if (
        str(artifact.get("from_phase") or "") != "verify"
        or str(artifact.get("to_phase") or "") != "resolve"
    ):
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
    if hg._run_track(run_id) == "goal-driven":
        hg._validate_goal_driven_closure_gate(run_id, blockers)
        return
    selection_rel = f"verification/{run_id}-verify-selection.yaml"
    readiness_rel = f"verification/{run_id}-resolve-readiness.yaml"
    package_rel = f"verification/{run_id}"
    selection = hg._load_yaml_under_root(selection_rel, blockers, "adaptive_verify_evidence_gate")
    if selection is not None:
        if selection.get("kind") != "uacp.verification_package":
            blockers.append(
                "adaptive_verify_evidence_gate: verify-selection kind must be "
                "uacp.verification_package"
            )
        if selection.get("run_id") != run_id:
            blockers.append("adaptive_verify_evidence_gate: verify-selection run_id mismatch")
    readiness = hg._load_yaml_under_root(readiness_rel, blockers, "adaptive_verify_evidence_gate")
    if readiness is not None:
        if readiness.get("kind") != "uacp.verify_resolve_readiness":
            blockers.append(
                "adaptive_verify_evidence_gate: resolve-readiness kind must be "
                "uacp.verify_resolve_readiness"
            )
        if readiness.get("run_id") != run_id:
            blockers.append("adaptive_verify_evidence_gate: resolve-readiness run_id mismatch")
        if readiness.get("ready_for_resolve") is not True:
            blockers.append("adaptive_verify_evidence_gate: ready_for_resolve must be true")
        if readiness.get("verification_package") != selection_rel:
            blockers.append(
                "adaptive_verify_evidence_gate: readiness must bind to verify-selection artifact"
            )
        for blocker in readiness.get("blockers") or []:
            if isinstance(blocker, Mapping) and blocker.get("state") == "open":
                blockers.append("adaptive_verify_evidence_gate: open blocker in resolve readiness")
    piv_assessment_rel = f"verification/{run_id}-piv-assessment.yaml"
    artifacts = [selection_rel, readiness_rel]
    if (hg.governed_root / piv_assessment_rel).exists():
        artifacts.append(piv_assessment_rel)
    hg._offline_validate_artifacts(artifacts, blockers, "adaptive_verify_evidence_gate")
    if not hg._dir_under_root_exists(package_rel):
        blockers.append(
            f"adaptive_verify_evidence_gate: missing verification package directory {package_rel}/"
        )


def validate_adaptive_resolve_closure_gate(
    hg: Heartgate, artifact: Mapping[str, Any], blockers: list[str]
) -> None:
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
    selection = hg._load_yaml_under_root(selection_rel, blockers, "adaptive_resolve_closure_gate")
    if selection is not None:
        if selection.get("kind") != "uacp.resolve_package":
            blockers.append(
                "adaptive_resolve_closure_gate: resolve-selection kind must be uacp.resolve_package"
            )
        if selection.get("run_id") != run_id:
            blockers.append("adaptive_resolve_closure_gate: resolve-selection run_id mismatch")
        if selection.get("verify_resolve_readiness") != readiness_rel:
            blockers.append(
                "adaptive_resolve_closure_gate: resolve-selection must bind run readiness"
            )
    closure = hg._load_yaml_under_root(closure_rel, blockers, "adaptive_resolve_closure_gate")
    if closure is not None:
        if closure.get("kind") != "uacp.resolve_closure":
            blockers.append(
                "adaptive_resolve_closure_gate: closure kind must be uacp.resolve_closure"
            )
        if closure.get("run_id") != run_id:
            blockers.append("adaptive_resolve_closure_gate: closure run_id mismatch")
        if closure.get("resolve_package") != selection_rel:
            blockers.append("adaptive_resolve_closure_gate: closure must bind resolve package")
        decision = (
            closure.get("final_decision")
            if isinstance(closure.get("final_decision"), Mapping)
            else {}
        )
        if decision.get("status") not in {"resolved", "resolved_with_warnings"}:
            blockers.append("adaptive_resolve_closure_gate: closure final_decision is not resolved")
    readiness = hg._load_yaml_under_root(readiness_rel, blockers, "adaptive_resolve_closure_gate")
    if readiness is not None and readiness.get("ready_for_resolve") is not True:
        blockers.append("adaptive_resolve_closure_gate: VERIFY readiness is not ready")
    hg._offline_validate_artifacts(
        [readiness_rel, selection_rel, closure_rel], blockers, "adaptive_resolve_closure_gate"
    )
    if not hg._dir_under_root_exists(package_rel):
        blockers.append(
            f"adaptive_resolve_closure_gate: missing resolve package directory {package_rel}/"
        )
