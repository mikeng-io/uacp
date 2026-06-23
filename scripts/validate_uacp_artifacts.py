#!/usr/bin/env python3
"""Lightweight UACP artifact validator for manual drills.

This is intentionally not a full schema engine. It checks the fields that current
UACP lifecycle/council artifacts rely on so manual drills do not silently drift.
"""
from __future__ import annotations

import argparse
import sys
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any, get_args

# Bootstrap: make ``config.base_dir`` importable whether this module is loaded
# dynamically by Heartgate (core.py adds uacp-core/scripts to sys.path) OR run
# standalone via ``main()``. The kernel's config resolver lives under
# ``skills/uacp-core/scripts`` relative to the repo root (= parents[1] of this
# file's ``scripts/`` dir).
import sys as _sys
from pathlib import Path as _P

_CORE = _P(__file__).resolve().parents[1] / "skills" / "uacp-core" / "scripts"
if str(_CORE) not in _sys.path:
    _sys.path.insert(0, str(_CORE))
from config import base_dir  # noqa: E402
from engines.domain import (  # noqa: E402
    CURRENT_POINTER_REQUIRED_FIELDS,
    ClusterState,
    EvidenceCluster,
    council_synthesis_required_fields,
    phase_transition_required_fields,
    phase_transition_terminal_kind_values,
)
from pydantic import ValidationError as _ValidationError  # noqa: E402

try:
    import yaml
except Exception as exc:  # pragma: no cover
    print(f"BLOCK yaml import failed: {exc}")
    sys.exit(2)

VALID_FINDING_STATES = {"open", "resolved", "accepted_risk", "not_applicable", "deferred"}
VALID_TRANSITION_DECISIONS = {"pass", "warn", "block"}
VALID_COUNCIL_VERDICTS = {"pass", "warn", "concerns", "fail", "pass_with_deferred_items", "pass_with_concerns", "proceed_to_plan_with_conditions", "completed_with_mixed_validity", "PASS", "WARN", "CONCERNS", "FAIL"}
# Derived from ClusterState in engines.domain.evidence_cluster (Slice 4a — no longer a divergent copy).
VALID_CLUSTER_STATES: set[str] = set(get_args(ClusterState))
VALID_CHECKPOINT_TYPES = {"before_side_effect", "after_work_unit", "pre_verify_handoff", "deviation", "remediation"}
VALID_NEXT_PHASE_READINESS = {"ready", "ready_with_deferred_items", "blocked"}
VALID_PIV_CHECKPOINTS = {"before_first_side_effect", "after_each_work_unit", "before_verify_handoff"}

VALID_EXECUTE_RUNTIME_SURFACES = {
    "hermes_profile_worker",
    "delegate_task",
    "external_runtime",
    "tool_adapter",
    "evidence_service",
    "human_checkpoint",
}
VALID_FINDING_CLASSIFICATIONS = {"blocker", "concern", "invariant_failure", "negative_finding", "material_warning"}
VALID_HANDLING_CLASSIFICATIONS = {"remediated", "expanded", "justified", "deferred", "accepted_warning", "rejected_with_reason"}
VALID_HEARTGATE_VALIDATIONS = {"pass", "warn", "block"}
HARD_FOLLOWUP_HANDLINGS = {"remediated", "expanded", "justified"}
CARRY_FORWARD_HANDLINGS = {"deferred", "accepted_warning", "rejected_with_reason"}
MATERIAL_FINDING_CLASSIFICATIONS = {"blocker", "concern", "invariant_failure", "negative_finding", "material_warning"}
MAX_FOLLOWUP_DEPTH_DEFAULT = 1


def load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text())
    except Exception as exc:
        raise ValueError(f"YAML parse failed for {path}: {exc}") from exc


def require_map(obj: Any, path: Path) -> dict:
    if not isinstance(obj, dict):
        raise ValueError(f"{path}: expected YAML mapping at top level")
    return obj



def scalar_status(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("status") or value.get("verdict") or value.get("state")
    return value

def listish(value: Any) -> Any:
    if isinstance(value, dict):
        return list(value.keys())
    return value

def check_required(name: str, obj: dict, required: list[str], issues: list[str]) -> None:
    for field in required:
        if field not in obj:
            issues.append(f"BLOCK {name}: missing required field {field}")


def iter_findings(obj: Any):
    if isinstance(obj, dict):
        for key, val in obj.items():
            if key == "findings" and isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        yield item
            else:
                yield from iter_findings(val)
    elif isinstance(obj, list):
        for item in obj:
            yield from iter_findings(item)


def validate_finding_states(path: Path, obj: Any, issues: list[str]) -> None:
    for finding in iter_findings(obj):
        state = finding.get("state") or finding.get("disposition")
        if state and state not in VALID_FINDING_STATES:
            issues.append(
                f"BLOCK {path}: unsupported finding state/disposition {state!r}; "
                f"expected one of {sorted(VALID_FINDING_STATES)}"
            )


def validate_transition_invariant_summary(path: Path, obj: dict, issues: list[str]) -> None:
    summary = obj.get("invariant_summary")
    if summary is None:
        return
    if not isinstance(summary, list):
        issues.append(f"BLOCK {path}: invariant_summary must be a list")
        return
    for item in summary:
        if not isinstance(item, dict):
            issues.append(f"BLOCK {path}: invariant_summary entries must be mappings")
            continue
        status = item.get("status")
        if status not in {"pass", "block"}:
            issues.append(
                f"BLOCK {path}: invariant_summary {item.get('id', '<unknown>')} status {status!r}; "
                "non-waivable invariants must be pass|block"
            )


def validate_transition_warning_deferred_shape(path: Path, obj: dict, issues: list[str]) -> None:
    warnings = obj.get("warnings") or []
    if not isinstance(warnings, list):
        issues.append(f"BLOCK {path}: warnings must be a list")
    else:
        for idx, item in enumerate(warnings):
            if not isinstance(item, dict):
                issues.append(f"BLOCK {path}: warnings[{idx}] must be a mapping")
                continue
            for field in ("owner", "residual_risk", "next_phase_acceptance"):
                if not item.get(field):
                    issues.append(f"BLOCK {path}: warnings[{idx}] missing {field}")
    deferred = obj.get("deferred_items") or []
    if not isinstance(deferred, list):
        issues.append(f"BLOCK {path}: deferred_items must be a list")
    else:
        for idx, item in enumerate(deferred):
            if not isinstance(item, dict):
                issues.append(f"BLOCK {path}: deferred_items[{idx}] must be a mapping")
                continue
            for field in ("id", "cluster_id", "owner", "condition", "accepted_by"):
                if not item.get(field):
                    issues.append(f"BLOCK {path}: deferred_items[{idx}] missing {field}")


def validate_handled_findings_chain(path: Path, obj: dict, issues: list[str]) -> None:
    chain = obj.get("handled_findings_chain")
    source_negative = obj.get("source_negative_findings_present")
    if source_negative is not None and not isinstance(source_negative, bool):
        issues.append(f"BLOCK {path}: source_negative_findings_present must be boolean when present")
    if source_negative is True and chain in (None, "", []):
        issues.append(f"BLOCK {path}: source_negative_findings_present=true requires handled_findings_chain")
        return
    if chain in (None, ""):
        return
    if not isinstance(chain, list):
        issues.append(f"BLOCK {path}: handled_findings_chain must be a list")
        return
    if chain and source_negative is not True:
        issues.append(f"BLOCK {path}: handled_findings_chain present requires source_negative_findings_present=true")
    required = [
        "original_finding_id", "finding_classification", "handling_classification",
        "handling_artifact_path", "followup_required", "owner",
        "residual_risk", "heartgate_validation",
    ]
    for idx, item in enumerate(chain):
        if not isinstance(item, dict):
            issues.append(f"BLOCK {path}: handled_findings_chain[{idx}] must be a mapping")
            continue
        for field in required:
            if field not in item or item.get(field) in (None, ""):
                issues.append(f"BLOCK {path}: handled_findings_chain[{idx}] missing {field}")
        finding = item.get("finding_classification")
        if finding and finding not in VALID_FINDING_CLASSIFICATIONS:
            issues.append(f"BLOCK {path}: handled_findings_chain[{idx}] invalid finding_classification {finding!r}")
        handling = item.get("handling_classification")
        if handling and handling not in VALID_HANDLING_CLASSIFICATIONS:
            issues.append(f"BLOCK {path}: handled_findings_chain[{idx}] invalid handling_classification {handling!r}")
        validation = item.get("heartgate_validation")
        if validation and validation not in VALID_HEARTGATE_VALIDATIONS:
            issues.append(f"BLOCK {path}: handled_findings_chain[{idx}] invalid heartgate_validation {validation!r}")
        depth = item.get("followup_depth", 0)
        try:
            depth_int = int(depth)
        except Exception:
            issues.append(f"BLOCK {path}: handled_findings_chain[{idx}] followup_depth must be integer")
            depth_int = 0
        if depth_int > MAX_FOLLOWUP_DEPTH_DEFAULT:
            issues.append(f"BLOCK {path}: handled_findings_chain[{idx}] followup_depth exceeds max {MAX_FOLLOWUP_DEPTH_DEFAULT}")
        if handling in HARD_FOLLOWUP_HANDLINGS and item.get("followup_required") is not True and not item.get("accepted_exception_artifact"):
            issues.append(f"BLOCK {path}: handled_findings_chain[{idx}] {handling} requires followup_required=true or accepted_exception_artifact")
        if item.get("followup_required") is True and not item.get("followup_council_synthesis_artifact"):
            issues.append(f"BLOCK {path}: handled_findings_chain[{idx}] followup_required=true requires followup_council_synthesis_artifact")
        if handling in CARRY_FORWARD_HANDLINGS:
            for field in ("owner", "residual_risk", "next_phase_obligation"):
                if not item.get(field):
                    issues.append(f"BLOCK {path}: handled_findings_chain[{idx}] {handling} missing {field}")
            if handling in {"accepted_warning", "rejected_with_reason"} and not item.get("accepted_exception_artifact"):
                issues.append(f"BLOCK {path}: handled_findings_chain[{idx}] {handling} requires accepted_exception_artifact")
        if finding in {"blocker", "invariant_failure"} and handling in CARRY_FORWARD_HANDLINGS and validation != "block":
            issues.append(f"BLOCK {path}: handled_findings_chain[{idx}] {finding} cannot carry forward without heartgate_validation=block")


def validate_phase_transition(path: Path, obj: dict, config: dict, issues: list[str], *, root: Path | None = None) -> None:
    schema = config.get("artifact_schema")
    # Slice 5 W2 (closes T4d-2) + BLOCKER fix: artifact_schema.required_fields and
    # fields.terminal_kind.values are codified in engines.domain
    # (enforce-by-default). The W2 slim removed only the required_fields KEY and the
    # terminal_kind.values KEY from config/phase-transitions.yaml but LEFT the
    # artifact_schema BLOCK present (unconsumed doctrine: kind, fields, conventions).
    # So fall back on KEY PRESENCE, not block presence: when the loaded block OMITS
    # a specific key (production, after the slim), use the code default (ENFORCE);
    # when the key is PRESENT (test fixture opt-out stub), its value wins (an
    # explicit empty list opts that check OFF, exactly as before).
    if isinstance(schema, Mapping) and "required_fields" in schema:
        required = schema.get("required_fields", [])
    else:
        required = phase_transition_required_fields()
    fields = schema.get("fields") if isinstance(schema, Mapping) else None
    terminal_kind = fields.get("terminal_kind") if isinstance(fields, Mapping) else None
    if isinstance(terminal_kind, Mapping) and "values" in terminal_kind:
        values = terminal_kind.get("values", [])
    else:
        values = phase_transition_terminal_kind_values()
    check_required(str(path), obj, required, issues)
    decision = obj.get("decision")
    if decision and decision not in VALID_TRANSITION_DECISIONS:
        issues.append(f"BLOCK {path}: invalid decision {decision!r}")
    terminal = obj.get("terminal_kind")
    if terminal and values and terminal not in values:
        issues.append(f"BLOCK {path}: terminal_kind {terminal!r} not in {values}")
    validate_transition_invariant_summary(path, obj, issues)
    validate_transition_warning_deferred_shape(path, obj, issues)
    validate_handled_findings_chain(path, obj, issues)
    validate_heartgate_coherence(path, obj, issues, root=root)
    validate_heartgate_coherence_requirement(path, obj, config, issues)
    validate_adaptive_transition_linked_artifacts(path, obj, issues, root=root)
    accepted_pairs: set[tuple[str, str]] = set()
    for idx, item in enumerate(obj.get("accepted_exceptions") if isinstance(obj.get("accepted_exceptions"), list) else []):
        if not isinstance(item, dict):
            issues.append(f"BLOCK {path}: accepted_exceptions[{idx}] must be a mapping")
            continue
        for field in ("id", "cluster_id", "artifact_path", "rationale", "owner", "accepted_by", "next_phase_acceptance"):
            if item.get(field) in (None, ""):
                issues.append(f"BLOCK {path}: accepted_exceptions[{idx}] missing {field}")
        if item.get("artifact_path") and item.get("cluster_id"):
            accepted_pairs.add((str(item.get("artifact_path")), str(item.get("cluster_id"))))
        artifact_path = str(item.get("artifact_path") or "")
        if artifact_path and not artifact_path.startswith(("verification/", "resolutions/")):
            issues.append(f"BLOCK {path}: accepted_exceptions[{idx}] artifact_path must be verification/ or resolutions/ evidence")
        if artifact_path and obj.get("run_id") and not _artifact_run_bound(artifact_path, str(obj.get("run_id"))):
            issues.append(f"BLOCK {path}: accepted_exceptions[{idx}] artifact_path must be run-bound: {artifact_path}")
        if root is not None and item.get("artifact_path") and not _artifact_exists(root, item.get("artifact_path")):
            issues.append(f"BLOCK {path}: accepted_exceptions[{idx}] artifact_path not found")
    for idx, cluster in enumerate(obj.get("cluster_summary") if isinstance(obj.get("cluster_summary"), list) else []):
        if isinstance(cluster, dict) and cluster.get("state") == "warn":
            pair = (str(cluster.get("artifact_path") or ""), str(cluster.get("cluster_id") or ""))
            if pair not in accepted_pairs:
                issues.append(f"BLOCK {path}: cluster_summary[{idx}] warns without matching accepted_exception artifact_path+cluster_id")


def validate_adaptive_transition_linked_artifacts(path: Path, obj: dict, issues: list[str], *, root: Path | None = None) -> None:
    if root is None:
        return
    gov = base_dir(root)  # governed namespace root (.uacp/); artifacts live here
    run_id = str(obj.get("run_id") or "")
    if not run_id:
        return
    from_phase = str(obj.get("from_phase") or "")
    to_phase = str(obj.get("to_phase") or "")
    if from_phase == "execute" and to_phase == "verify":
        for rel, validator in [
            (f"plans/{run_id}-piv.yaml", validate_piv_contract),
            (f"executions/{run_id}-checkpoint-001.yaml", validate_execution_checkpoint),
        ]:
            artifact = _load_yaml_artifact(root, rel)
            if artifact is None:
                issues.append(f"BLOCK {path}: linked EXECUTE gate artifact missing or unreadable: {rel}")
            else:
                validator(gov / rel, artifact, issues, root=root)
    if from_phase == "verify" and to_phase == "resolve":
        for rel, validator in [
            (f"verification/{run_id}-verify-selection.yaml", validate_verify_package_selection),
            (f"verification/{run_id}-resolve-readiness.yaml", validate_verify_resolve_readiness),
        ]:
            artifact = _load_yaml_artifact(root, rel)
            if artifact is None:
                issues.append(f"BLOCK {path}: linked VERIFY gate artifact missing or unreadable: {rel}")
            else:
                validator(gov / rel, artifact, issues, root=root)
        piv_rel = f"verification/{run_id}-piv-assessment.yaml"
        if (gov / f"plans/{run_id}-piv.yaml").exists() or (gov / piv_rel).exists():
            artifact = _load_yaml_artifact(root, piv_rel)
            if artifact is None:
                issues.append(f"BLOCK {path}: linked VERIFY PIV assessment missing or unreadable: {piv_rel}")
            else:
                validate_piv_assessment(gov / piv_rel, artifact, issues, root=root)
    if from_phase == "resolve":
        for rel, validator in [
            (f"verification/{run_id}-resolve-readiness.yaml", validate_verify_resolve_readiness),
            (f"resolutions/{run_id}-resolve-selection.yaml", validate_resolve_package_selection),
            (f"resolutions/{run_id}-closure.yaml", validate_resolve_closure),
        ]:
            artifact = _load_yaml_artifact(root, rel)
            if artifact is None:
                issues.append(f"BLOCK {path}: linked RESOLVE gate artifact missing or unreadable: {rel}")
            else:
                validator(gov / rel, artifact, issues, root=root)


def validate_heartgate_coherence_requirement(path: Path, obj: dict, config: dict, issues: list[str]) -> None:
    rule = config.get("heartgate_coherence_required_when") or {}
    if not rule or obj.get("heartgate_coherence") not in (None, ""):
        return
    reasons: list[str] = []
    min_granularity = rule.get("min_composite_granularity")
    if min_granularity is not None:
        try:
            if int(obj.get("composite_granularity") or 0) >= int(min_granularity):
                reasons.append(f"composite_granularity>={min_granularity}")
        except Exception:
            pass
    phases = {str(x) for x in (rule.get("phases") or [])}
    if phases and str(obj.get("from_phase") or "") in phases:
        reasons.append("phase=" + str(obj.get("from_phase") or ""))
    routing = {str(x) for x in (rule.get("routing_outcomes") or [])}
    if routing and str(obj.get("routing_outcome") or "") in routing:
        reasons.append("routing_outcome=" + str(obj.get("routing_outcome") or ""))
    domains = {str(x) for x in (rule.get("domains") or [])}
    artifact_domains = {str(x) for x in (obj.get("domains") or [])}
    overlap = domains.intersection(artifact_domains)
    if overlap:
        reasons.append("domain=" + ",".join(sorted(overlap)))
    if reasons:
        issues.append(f"BLOCK {path}: heartgate_coherence required by transition policy: {'; '.join(reasons)}")


def validate_council_synthesis(path: Path, obj: dict, config: dict, issues: list[str]) -> None:
    schema = config.get("council_synthesis_schema")
    # Slice 5 W2 (closes T4d-2) + BLOCKER fix: council_synthesis_schema.required_fields
    # is codified in engines.domain.council_synthesis_required_fields()
    # (enforce-by-default). The W2 slim removed only the required_fields KEY but LEFT
    # the council_synthesis_schema BLOCK present, so fall back on KEY PRESENCE, not
    # block presence: absent key -> code default (ENFORCE); present key -> its
    # value wins (explicit empty list opts OFF).
    if isinstance(schema, Mapping) and "required_fields" in schema:
        required = schema.get("required_fields", [])
    else:
        required = council_synthesis_required_fields()
    aliases = {
        "council_id": obj.get("council_id") or obj.get("artifact_id") or obj.get("review_id"),
        "tier": obj.get("tier") or obj.get("council_tier"),
        "roles": obj.get("roles") or obj.get("expert_roles"),
        "dispatch_surfaces": obj.get("dispatch_surfaces") or obj.get("dispatch_surface"),
        "verdict": obj.get("verdict") or obj.get("overall_verdict") or obj.get("status"),
        "artifact_paths": obj.get("artifact_paths") or obj.get("reviewed_artifacts") or obj.get("inspected_paths"),
        "inspected_paths": obj.get("inspected_paths") or obj.get("reviewed_artifacts"),
        "phase_local_granularity": obj.get("phase_local_granularity"),
        "mode": obj.get("mode"),
    }
    legacy_shape = any(key in obj for key in ("council_tier", "reviewed_artifacts", "overall_verdict", "expert_roles", "review_id", "synthesis_id", "acceptance", "concerns")) or obj.get("schema_version") == "0.1"
    for field in required:
        if field not in obj and aliases.get(field) in (None, "", []):
            if not legacy_shape:
                issues.append(f"BLOCK {path}: missing required field {field}")
    if not legacy_shape and "dispatch_surfaces" not in obj and aliases.get("dispatch_surfaces") in (None, "", []):
        issues.append(f"BLOCK {path}: council synthesis lacks dispatch_surfaces")
    verdict = scalar_status(aliases.get("verdict"))
    if verdict and verdict not in VALID_COUNCIL_VERDICTS and not legacy_shape:
        issues.append(f"BLOCK {path}: invalid council verdict {verdict!r}")
    inspected = listish(aliases.get("inspected_paths"))
    if inspected is not None and not isinstance(inspected, list):
        level = "WARN" if legacy_shape else "BLOCK"
        issues.append(f"{level} {path}: inspected_paths must be a list")
    if inspected == []:
        issues.append(f"BLOCK {path}: inspected_paths must not be empty for council synthesis")
    depth = obj.get("followup_depth")
    if depth is not None:
        try:
            if int(depth) > MAX_FOLLOWUP_DEPTH_DEFAULT:
                issues.append(f"BLOCK {path}: followup_depth exceeds max {MAX_FOLLOWUP_DEPTH_DEFAULT}")
        except Exception:
            issues.append(f"BLOCK {path}: followup_depth must be integer")
    validate_finding_states(path, obj, issues)


def validate_triage(path: Path, obj: dict, issues: list[str]) -> None:
    required = [
        "kind", "triage_id", "request_summary", "authority", "factor_scores",
        "granularity_level", "routing_outcome", "next_step",
    ]
    check_required(str(path), obj, required, issues)
    routing = obj.get("routing_outcome")
    if routing and routing not in {"direct", "lightweight", "standard_uacp", "full_governance", "block_or_clarify"}:
        issues.append(f"BLOCK {path}: invalid routing_outcome {routing!r}")
    authority = obj.get("authority") if isinstance(obj.get("authority"), dict) else {}
    if authority.get("status") not in {"pass", "warn", "block"}:
        issues.append(f"BLOCK {path}: authority.status must be pass|warn|block")
    track = obj.get("track", "standard")
    if track not in {"standard", "goal-driven"}:
        issues.append(f"BLOCK {path}: invalid track {track!r} (must be standard|goal-driven)")


def validate_proposal(path: Path, obj: dict, issues: list[str]) -> None:
    required = [
        "kind", "proposal_id", "run_id", "phase", "triage_artifact", "title",
        "objective", "scope", "declared_side_effects", "authority", "human_involvement",
    ]
    check_required(str(path), obj, required, issues)
    if obj.get("phase") != "propose":
        issues.append(f"BLOCK {path}: proposal phase must be 'propose'")
    authority = obj.get("authority") if isinstance(obj.get("authority"), dict) else {}
    if authority.get("status") not in {"pass", "warn", "block"}:
        issues.append(f"BLOCK {path}: authority.status must be pass|warn|block")
    scope = obj.get("scope") if isinstance(obj.get("scope"), dict) else {}
    if "in_scope" not in scope or "out_of_scope" not in scope:
        issues.append(f"BLOCK {path}: scope must include in_scope and out_of_scope")
    else:
        # D43: in_scope items must be KEYED {id, statement} — these are the projection's scope_item
        # nodes that work_units cover via derives_from (GP_UNCOVERED/GP_ORPHAN). Bare strings (the
        # pre-D43 form) no longer satisfy coverage.
        for i, item in enumerate(scope.get("in_scope") or []):
            if not (isinstance(item, dict) and item.get("id") and item.get("statement")):
                issues.append(
                    f"BLOCK {path}: scope.in_scope[{i}] must be a keyed object with id + statement"
                )


def validate_heartgate_coherence(path: Path, obj: dict, issues: list[str], *, root: Path | None = None) -> None:
    coherence = obj.get("heartgate_coherence")
    if coherence in (None, ""):
        return
    if not isinstance(coherence, dict):
        issues.append(f"BLOCK {path}: heartgate_coherence must be a mapping")
        return
    status = coherence.get("status")
    if status not in {"pass", "warn", "block"}:
        issues.append(f"BLOCK {path}: heartgate_coherence.status must be pass|warn|block")
    artifact_path = coherence.get("artifact_path")
    if not artifact_path:
        issues.append(f"BLOCK {path}: heartgate_coherence requires artifact_path")
    elif root is not None:
        gov = base_dir(root)  # artifacts are base-relative under .uacp/
        candidate = Path(str(artifact_path))
        if not candidate.is_absolute():
            candidate = gov / candidate
        try:
            resolved = candidate.resolve()
            if resolved != gov and gov not in resolved.parents:
                issues.append(f"BLOCK {path}: heartgate_coherence artifact_path escapes UACP_ROOT")
            elif not resolved.exists():
                issues.append(f"BLOCK {path}: heartgate_coherence artifact_path not found: {artifact_path}")
        except Exception as exc:
            issues.append(f"BLOCK {path}: heartgate_coherence artifact_path invalid: {exc}")
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
        issues.append(f"BLOCK {path}: heartgate_coherence.lenses must be a list")
        return
    missing = sorted(required_lenses - {str(item) for item in lenses})
    if missing:
        issues.append(f"BLOCK {path}: heartgate_coherence missing lens(es): {', '.join(missing)}")


def validate_gate_selection(path: Path, obj: dict, issues: list[str]) -> None:
    required = [
        "selection_id", "run_id", "phase", "domains", "artifact_types",
        "risk_level", "granularity_level", "invariant_checks",
        "selected_clusters", "transition_requirements", "reasoning",
    ]
    check_required(str(path), obj, required, issues)
    for item in obj.get("invariant_checks", []) or []:
        if isinstance(item, dict):
            status = item.get("status")
            if status not in {"pass", "block"}:
                issues.append(f"BLOCK {path}: invariant_checks status must be pass|block, got {status!r}")
    for item in obj.get("selected_clusters", []) or []:
        if isinstance(item, dict):
            state = item.get("state", "required")
            if state not in {"required", "optional", "generated", "not_applicable"}:
                issues.append(f"BLOCK {path}: selected cluster state {state!r} is invalid")


def validate_execute_task(path: Path, obj: dict, issues: list[str]) -> None:
    required = ["schema_version", "kind", "id", "title", "uacp", "objective", "scope", "runtime", "side_effects", "verification", "completion"]
    check_required(str(path), obj, required, issues)
    runtime = obj.get("runtime", {}) if isinstance(obj.get("runtime"), dict) else {}
    surface = runtime.get("surface")
    if surface and surface not in VALID_EXECUTE_RUNTIME_SURFACES:
        issues.append(f"BLOCK {path}: runtime.surface {surface!r} is invalid")
    scope = obj.get("scope", {}) if isinstance(obj.get("scope"), dict) else {}
    if "allowed_files" not in scope or "forbidden_files" not in scope:
        issues.append(f"BLOCK {path}: scope must declare allowed_files and forbidden_files")
    side_effects = obj.get("side_effects", {}) if isinstance(obj.get("side_effects"), dict) else {}
    if "declared" not in side_effects or "reversibility" not in side_effects:
        issues.append(f"BLOCK {path}: side_effects must declare declared and reversibility")


def validate_evidence_cluster(path: Path, obj: dict, issues: list[str]) -> None:
    # Required-field and state-enum validation delegated to the EvidenceCluster
    # Pydantic model (codified from config/evidence-clusters.yaml, Slice 4a).
    # Error messages are translated to preserve the existing BLOCK string format.
    try:
        EvidenceCluster.model_validate(obj)
    except _ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(x) for x in err["loc"]) if err["loc"] else "?"
            etype = err["type"]
            if etype in ("missing",):
                issues.append(f"BLOCK {path}: missing required field {loc}")
            elif etype in ("literal_error",) and loc == "state":
                state_val = obj.get("state")
                issues.append(f"BLOCK {path}: evidence cluster state {state_val!r} is invalid")
            elif etype in ("literal_error",) and loc == "phase":
                phase_val = obj.get("phase")
                issues.append(f"BLOCK {path}: evidence cluster phase {phase_val!r} is invalid")
            else:
                issues.append(f"BLOCK {path}: evidence cluster validation error at {loc}: {err['msg']}")

def validate_evidence_registry(root: Path, issues: list[str]) -> None:
    path = root / "config" / "evidence-clusters.yaml"
    data = require_map(load_yaml(path), path)
    registry = data.get("evidence_domain_registry")
    if registry:
        status = registry.get("implementation_status")
        if status != "not_runtime_active":
            issues.append(
                f"WARN {path}: evidence_domain_registry implementation_status is {status!r}; "
                "ensure runtime selector exists before claiming active implementation"
            )
        if "verification_rule" not in registry:
            issues.append(f"WARN {path}: evidence_domain_registry lacks verification_rule")


def _validate_na_item(path: Path, label: str, item: Any, issues: list[str]) -> None:
    if not isinstance(item, dict):
        issues.append(f"BLOCK {path}: {label} must be a mapping")
        return
    for field in ("reason", "accepted_by", "owner", "residual_risk", "revisit_phase"):
        if item.get(field) in (None, ""):
            issues.append(f"BLOCK {path}: {label} missing {field}")


def _artifact_exists(root: Path, artifact: Any) -> bool:
    if artifact in (None, ""):
        return False
    gov = base_dir(root)  # artifact paths are base-relative under .uacp/
    candidate = Path(str(artifact))
    if not candidate.is_absolute():
        candidate = gov / candidate
    try:
        resolved = candidate.resolve()
        gov_resolved = gov.resolve()
        return (resolved == gov_resolved or gov_resolved in resolved.parents) and resolved.exists()
    except Exception:
        return False


def _artifact_run_bound(artifact: str, run_id: str) -> bool:
    if not artifact or not run_id:
        return False
    prefixes = (
        f"proposals/{run_id}",
        f"plans/{run_id}",
        f"executions/{run_id}",
        f"verification/{run_id}",
        f"resolutions/{run_id}",
    )
    return artifact.startswith(prefixes)


def _read_artifact_text(root: Path | None, artifact: Any) -> str | None:
    if root is None or artifact in (None, ""):
        return None
    gov = base_dir(root)  # artifact paths are base-relative under .uacp/
    candidate = Path(str(artifact))
    if not candidate.is_absolute():
        candidate = gov / candidate
    try:
        resolved = candidate.resolve()
        gov_resolved = gov.resolve()
        if not (resolved == gov_resolved or gov_resolved in resolved.parents):
            return None
        if not resolved.exists() or not resolved.is_file():
            return None
        return resolved.read_text(encoding="utf-8")
    except Exception:
        return None


def _validate_semantic_markdown(path: Path, field: str, artifact: Any, text: str | None, issues: list[str], required_terms: list[str]) -> None:
    """Validate that package artifacts are semantic context, not placeholders.

    UACP package Markdown is not optional decoration. It is the semantic substrate
    future agents use to reconstruct why the run exists, how it works, the
    rational intent, and the decision boundary. YAML remains the lifecycle
    envelope; Markdown must carry recoverable meaning.
    """
    artifact_s = str(artifact or "")
    if not artifact_s.endswith(".md"):
        issues.append(f"BLOCK {path}: {field} artifact must be Markdown semantic context, got {artifact_s}")
        return
    if text is None:
        issues.append(f"BLOCK {path}: {field} artifact unreadable: {artifact_s}")
        return
    stripped = text.strip()
    if len(stripped) < 240:
        issues.append(f"BLOCK {path}: {field} artifact too thin for semantic recovery: {artifact_s}")
    if "#" not in stripped[:200]:
        issues.append(f"BLOCK {path}: {field} artifact lacks Markdown heading structure: {artifact_s}")
    lowered = stripped.lower()
    missing = [term for term in required_terms if term not in lowered]
    if missing:
        issues.append(f"BLOCK {path}: {field} artifact lacks semantic term(s) {missing}: {artifact_s}")


def _validate_package_directory(root: Path | None, path: Path, phase: str, run_id: Any, issues: list[str]) -> Path | None:
    """Require canonical semantic package directory and index for selected packages."""
    if root is None or not run_id:
        return None
    root_name = {"propose": "proposals", "plan": "plans", "execute": "executions", "verify": "verification", "resolve": "resolutions"}.get(phase, f"{phase}s")
    package_rel = Path(root_name) / str(run_id)
    package_dir = base_dir(root) / package_rel
    if not package_dir.is_dir():
        issues.append(f"BLOCK {path}: {phase} package directory not found: {package_rel}/")
        return None
    index = package_dir / "00-index.md"
    if not index.exists():
        issues.append(f"BLOCK {path}: {phase} package index not found: {package_rel}/00-index.md")
    else:
        index_terms = {"propose": ["why", "how"], "plan": ["plan", "how"], "execute": ["intent", "evidence"]}.get(phase, ["intent", "evidence"])
        _validate_semantic_markdown(path, f"{phase}_package_index", str(package_rel / "00-index.md"), index.read_text(encoding="utf-8"), issues, index_terms)
    return package_dir


def _artifact_under_package(root: Path | None, package_dir: Path | None, artifact: Any) -> bool:
    if root is None or package_dir is None or artifact in (None, ""):
        return False
    candidate = Path(str(artifact))
    if not candidate.is_absolute():
        candidate = base_dir(root) / candidate
    try:
        resolved = candidate.resolve()
        package_resolved = package_dir.resolve()
        return resolved == package_resolved or package_resolved in resolved.parents
    except Exception:
        return False


def validate_proposal_package_selection(path: Path, obj: dict, issues: list[str], *, root: Path | None = None) -> None:
    if obj.get("phase") != "propose":
        issues.append(f"BLOCK {path}: package selection phase must be 'propose'")
    if not obj.get("run_id"):
        issues.append(f"BLOCK {path}: package selection missing run_id")
    if not isinstance(obj.get("work_heart"), dict):
        issues.append(f"BLOCK {path}: package selection requires work_heart mapping")
    package_dir = _validate_package_directory(root, path, "propose", obj.get("run_id"), issues)
    required_core = ["intent", "authority", "scope", "containment", "risk", "verification", "transition", "artifact_map"]
    raw_core = obj.get("universal_core")
    core = raw_core if isinstance(raw_core, dict) else {}
    for key in required_core:
        item = core.get(key)
        if not isinstance(item, dict):
            issues.append(f"BLOCK {path}: universal_core.{key} missing or not a mapping")
            continue
        status = item.get("status")
        if status == "covered":
            artifact = item.get("artifact")
            if not artifact:
                issues.append(f"BLOCK {path}: universal_core.{key} missing artifact")
            elif root is not None and not _artifact_exists(root, artifact):
                issues.append(f"BLOCK {path}: universal_core.{key} artifact not found: {artifact}")
            elif root is not None:
                proposal_terms = {
                    "intent": ["why", "intent", "decision"],
                    "authority": ["authority"],
                    "scope": ["scope"],
                    "containment": ["contain"],
                    "risk": ["risk"],
                    "verification": ["verification"],
                    "transition": ["transition"],
                    "artifact_map": ["artifact"],
                }
                _validate_semantic_markdown(path, f"universal_core.{key}", artifact, _read_artifact_text(root, artifact), issues, proposal_terms.get(str(key), []))
                if not _artifact_under_package(root, package_dir, artifact):
                    issues.append(f"BLOCK {path}: universal_core.{key} artifact must live under proposals/{obj.get('run_id')}/: {artifact}")
        elif status == "not_applicable":
            _validate_na_item(path, f"universal_core.{key}", item, issues)
        else:
            issues.append(f"BLOCK {path}: universal_core.{key} status must be covered|not_applicable")
    raw_modules = obj.get("selected_modules")
    modules = raw_modules if isinstance(raw_modules, dict) else {}
    if not modules:
        issues.append(f"BLOCK {path}: package selection selected_modules must not be empty")
    for name, item in modules.items():
        if not isinstance(item, dict):
            issues.append(f"BLOCK {path}: selected_modules.{name} must be a mapping")
            continue
        if not item.get("reason"):
            issues.append(f"BLOCK {path}: selected_modules.{name} missing reason")
        artifact = item.get("artifact")
        if not artifact:
            issues.append(f"BLOCK {path}: selected_modules.{name} missing artifact")
        elif root is not None and not _artifact_exists(root, artifact):
            issues.append(f"BLOCK {path}: selected_modules.{name} artifact not found: {artifact}")
        elif root is not None and not _artifact_under_package(root, package_dir, artifact):
            issues.append(f"BLOCK {path}: selected_modules.{name} artifact must live under proposals/{obj.get('run_id')}/: {artifact}")
    raw_na = obj.get("not_applicable")
    na = raw_na if isinstance(raw_na, dict) else {}
    for name, item in na.items():
        _validate_na_item(path, f"not_applicable.{name}", item, issues)
    readiness = obj.get("plan_readiness")
    if readiness is not None:
        if not isinstance(readiness, dict):
            issues.append(f"BLOCK {path}: plan_readiness must be a mapping")
        elif readiness.get("status") not in {"ready_for_plan", "ready_for_plan_with_conditions", "blocked", "blocked_until_council_pass"}:
            issues.append(f"BLOCK {path}: plan_readiness.status is invalid")


def validate_plan_package_selection(path: Path, obj: dict, issues: list[str], *, root: Path | None = None) -> None:
    if obj.get("phase") != "plan":
        issues.append(f"BLOCK {path}: plan package selection phase must be 'plan'")
    if not obj.get("run_id"):
        issues.append(f"BLOCK {path}: plan package selection missing run_id")
    run_id = obj.get("run_id")
    if not isinstance(obj.get("work_heart"), dict):
        issues.append(f"BLOCK {path}: plan package selection requires work_heart mapping")
    package_dir = _validate_package_directory(root, path, "plan", run_id, issues)
    if root is not None and run_id:
        scope_artifact = base_dir(root) / "plans" / f"{run_id}-scope.yaml"
        if not scope_artifact.exists():
            issues.append(f"BLOCK {path}: plan scope artifact not found: plans/{run_id}-scope.yaml")
    required_core = [
        "work_breakdown",
        "dependencies",
        "authority_and_side_effects",
        "tool_runtime_selection",
        "artifact_write_surfaces",
        "verification_strategy",
        "rollback_recovery",
        "council_review_topology",
        "transition_readiness",
    ]
    raw_core = obj.get("universal_core")
    core = raw_core if isinstance(raw_core, dict) else {}
    for key in required_core:
        item = core.get(key)
        if not isinstance(item, dict):
            issues.append(f"BLOCK {path}: universal_core.{key} missing or not a mapping")
            continue
        status = item.get("status")
        if status == "covered":
            artifact = item.get("artifact")
            if not artifact:
                issues.append(f"BLOCK {path}: universal_core.{key} missing artifact")
            elif root is not None and not _artifact_exists(root, artifact):
                issues.append(f"BLOCK {path}: universal_core.{key} artifact not found: {artifact}")
            elif root is not None:
                plan_terms = {
                    "work_breakdown": ["work"],
                    "dependencies": ["dependencies"],
                    "authority_and_side_effects": ["authority", "side effect"],
                    "tool_runtime_selection": ["tool", "runtime"],
                    "artifact_write_surfaces": ["artifact", "write"],
                    "verification_strategy": ["verification"],
                    "rollback_recovery": ["rollback"],
                    "council_review_topology": ["review"],
                    "transition_readiness": ["transition"],
                }
                _validate_semantic_markdown(path, f"universal_core.{key}", artifact, _read_artifact_text(root, artifact), issues, plan_terms.get(str(key), []))
                if not _artifact_under_package(root, package_dir, artifact):
                    issues.append(f"BLOCK {path}: universal_core.{key} artifact must live under plans/{run_id}/: {artifact}")
        elif status == "not_applicable":
            _validate_na_item(path, f"universal_core.{key}", item, issues)
        else:
            issues.append(f"BLOCK {path}: universal_core.{key} status must be covered|not_applicable")
    raw_modules = obj.get("selected_modules")
    modules = raw_modules if isinstance(raw_modules, dict) else {}
    if not modules:
        issues.append(f"BLOCK {path}: plan package selection selected_modules must not be empty")
    for name, item in modules.items():
        if not isinstance(item, dict):
            issues.append(f"BLOCK {path}: selected_modules.{name} must be a mapping")
            continue
        if not item.get("reason"):
            issues.append(f"BLOCK {path}: selected_modules.{name} missing reason")
        artifact = item.get("artifact")
        if not artifact:
            issues.append(f"BLOCK {path}: selected_modules.{name} missing artifact")
        elif root is not None and not _artifact_exists(root, artifact):
            issues.append(f"BLOCK {path}: selected_modules.{name} artifact not found: {artifact}")
        elif root is not None and not _artifact_under_package(root, package_dir, artifact):
            issues.append(f"BLOCK {path}: selected_modules.{name} artifact must live under plans/{run_id}/: {artifact}")
    raw_na = obj.get("not_applicable")
    na = raw_na if isinstance(raw_na, dict) else {}
    for name, item in na.items():
        _validate_na_item(path, f"not_applicable.{name}", item, issues)
        if isinstance(item, dict) and item.get("revisit_trigger") in (None, ""):
            issues.append(f"BLOCK {path}: not_applicable.{name} missing revisit_trigger")
    readiness = obj.get("transition_readiness")
    if not isinstance(readiness, dict):
        issues.append(f"BLOCK {path}: transition_readiness must be a mapping")
    elif readiness.get("status") not in {"ready_for_execute", "ready_with_conditions", "blocked"}:
        issues.append(f"BLOCK {path}: transition_readiness.status is invalid")



def validate_piv_contract(path: Path, obj: dict, issues: list[str], *, root: Path | None = None) -> None:
    required = ["kind", "phase", "run_id", "applies_to_phase", "phase_intent", "work_units", "evidence_obligations", "checkpoint_policy", "intent_drift_conditions", "next_phase_handoff"]
    check_required(str(path), obj, required, issues)
    if obj.get("phase") != "plan":
        issues.append(f"BLOCK {path}: PIV contract phase must be 'plan'")
    if obj.get("applies_to_phase") != "execute":
        issues.append(f"BLOCK {path}: PIV contract applies_to_phase must be 'execute'")
    if not isinstance(obj.get("phase_intent"), dict) or not obj.get("phase_intent", {}).get("summary"):
        issues.append(f"BLOCK {path}: PIV contract requires phase_intent.summary")
    work_units = obj.get("work_units") if isinstance(obj.get("work_units"), list) else []
    if not work_units:
        issues.append(f"BLOCK {path}: PIV contract requires non-empty work_units")
    unit_ids: set[str] = set()
    for idx, unit in enumerate(work_units):
        if not isinstance(unit, dict):
            issues.append(f"BLOCK {path}: work_units[{idx}] must be a mapping")
            continue
        unit_id = str(unit.get("id") or "")
        if not unit_id:
            issues.append(f"BLOCK {path}: work_units[{idx}] missing id")
        else:
            unit_ids.add(unit_id)
        for field in ("intent", "expected_outputs"):
            if unit.get(field) in (None, "", []):
                issues.append(f"BLOCK {path}: work_units[{idx}] missing {field}")
        # D43: every work_unit must declare coverage (derives_from -> scope_item ids). This is the
        # referential coverage invariant (kept here, NOT in the shape schema) — it guarantees the
        # projection's coverage layer is adopted so GP_UNCOVERED/GP_ORPHAN bind; the projection's
        # GP_PHANTOM_EDGE resolves that each referenced scope_item id actually exists.
        if not (isinstance(unit.get("derives_from"), list) and unit.get("derives_from")):
            issues.append(
                f"BLOCK {path}: work_units[{idx}] missing derives_from (>=1 scope_item id)"
            )
    obligations = obj.get("evidence_obligations") if isinstance(obj.get("evidence_obligations"), list) else []
    if not obligations:
        issues.append(f"BLOCK {path}: PIV contract requires non-empty evidence_obligations")
    obligation_ids: set[str] = set()
    for idx, obligation in enumerate(obligations):
        if not isinstance(obligation, dict):
            issues.append(f"BLOCK {path}: evidence_obligations[{idx}] must be a mapping")
            continue
        oid = str(obligation.get("id") or "")
        if not oid:
            issues.append(f"BLOCK {path}: evidence_obligations[{idx}] missing id")
        else:
            obligation_ids.add(oid)
        unit_id = str(obligation.get("work_unit_id") or "")
        if unit_id and unit_id not in unit_ids:
            issues.append(f"BLOCK {path}: evidence_obligations[{idx}] references unknown work_unit_id {unit_id!r}")
        for field in ("evidence_type", "required", "sufficiency"):
            if field not in obligation or obligation.get(field) in (None, ""):
                issues.append(f"BLOCK {path}: evidence_obligations[{idx}] missing {field}")
    checkpoint_policy = obj.get("checkpoint_policy") if isinstance(obj.get("checkpoint_policy"), dict) else {}
    required_checkpoints = checkpoint_policy.get("required_checkpoints") if isinstance(checkpoint_policy.get("required_checkpoints"), list) else []
    if not required_checkpoints:
        issues.append(f"BLOCK {path}: PIV contract checkpoint_policy.required_checkpoints must not be empty")
    for item in required_checkpoints:
        if str(item) not in VALID_PIV_CHECKPOINTS:
            issues.append(f"BLOCK {path}: PIV contract checkpoint_policy contains invalid checkpoint {item!r}")
    if "max_uncheckpointed_units" in checkpoint_policy:
        try:
            if int(checkpoint_policy.get("max_uncheckpointed_units")) < 0:
                issues.append(f"BLOCK {path}: PIV contract checkpoint_policy.max_uncheckpointed_units must be >= 0")
        except Exception:
            issues.append(f"BLOCK {path}: PIV contract checkpoint_policy.max_uncheckpointed_units must be an integer")
    handoff = obj.get("next_phase_handoff") if isinstance(obj.get("next_phase_handoff"), dict) else {}
    if not handoff.get("required_artifacts") or not handoff.get("pass_condition"):
        issues.append(f"BLOCK {path}: PIV contract next_phase_handoff requires required_artifacts and pass_condition")


def _load_piv_contract(root: Path | None, artifact: Any) -> dict | None:
    if root is None or artifact in (None, ""):
        return None
    gov = base_dir(root)  # artifact paths are base-relative under .uacp/
    candidate = Path(str(artifact))
    if not candidate.is_absolute():
        candidate = gov / candidate
    try:
        resolved = candidate.resolve()
        gov_resolved = gov.resolve()
        if not (resolved == gov_resolved or gov_resolved in resolved.parents) or not resolved.exists():
            return None
        data = yaml.safe_load(resolved.read_text())
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def validate_execution_checkpoint(path: Path, obj: dict, issues: list[str], *, root: Path | None = None) -> None:
    required = ["kind", "phase", "run_id", "checkpoint_id", "piv_contract", "checkpoint_type", "work_unit_id", "work_performed", "decisions", "evidence", "intent_drift", "invariants", "next_phase_readiness"]
    check_required(str(path), obj, required, issues)
    if obj.get("phase") != "execute":
        issues.append(f"BLOCK {path}: execution checkpoint phase must be 'execute'")
    run_id = obj.get("run_id")
    package_dir = _validate_package_directory(root, path, "execute", run_id, issues)
    piv_ref = obj.get("piv_contract")
    if root is not None and not _artifact_exists(root, piv_ref):
        issues.append(f"BLOCK {path}: execution checkpoint piv_contract not found: {piv_ref}")
    piv = _load_piv_contract(root, piv_ref)
    work_unit_ids: set[str] = set()
    required_obligations: set[str] = set()
    all_obligations: set[str] = set()
    if piv is None:
        issues.append(f"BLOCK {path}: piv_contract is unreadable or malformed: {piv_ref}")
    else:
        if piv.get("kind") != "uacp.phase_intent_verification_contract":
            issues.append(f"BLOCK {path}: piv_contract kind must be uacp.phase_intent_verification_contract")
        work_unit_ids = {str(unit.get("id")) for unit in (piv.get("work_units") or []) if isinstance(unit, dict) and unit.get("id")}
        all_obligations = {str(item.get("id")) for item in (piv.get("evidence_obligations") or []) if isinstance(item, dict) and item.get("id")}
        required_obligations = {str(item.get("id")) for item in (piv.get("evidence_obligations") or []) if isinstance(item, dict) and item.get("required") is True and item.get("id")}
    checkpoint_type = str(obj.get("checkpoint_type") or "")
    if checkpoint_type not in VALID_CHECKPOINT_TYPES:
        issues.append(f"BLOCK {path}: checkpoint_type {checkpoint_type!r} is invalid")
    work_unit_id = str(obj.get("work_unit_id") or "")
    if work_unit_ids and work_unit_id not in work_unit_ids:
        issues.append(f"BLOCK {path}: checkpoint work_unit_id {work_unit_id!r} is not declared in PIV")
    work = obj.get("work_performed") if isinstance(obj.get("work_performed"), dict) else {}
    if not work.get("summary") or not work.get("produced_outputs"):
        issues.append(f"BLOCK {path}: work_performed requires summary and produced_outputs")
    evidence = obj.get("evidence") if isinstance(obj.get("evidence"), list) else []
    if not evidence:
        issues.append(f"BLOCK {path}: execution checkpoint evidence must not be empty")
    seen_required: set[str] = set()
    required_pass: set[str] = set()
    required_warn_or_deferred: set[str] = set()
    for idx, item in enumerate(evidence):
        if not isinstance(item, dict):
            issues.append(f"BLOCK {path}: evidence[{idx}] must be a mapping")
            continue
        oid = str(item.get("obligation_id") or "")
        if all_obligations and oid and oid not in all_obligations:
            issues.append(f"BLOCK {path}: evidence[{idx}] references unknown PIV obligation_id {oid!r}")
        if oid in required_obligations and item.get("result") in {"pass", "warn", "deferred"}:
            seen_required.add(oid)
            if item.get("result") == "pass":
                required_pass.add(oid)
            elif item.get("result") in {"warn", "deferred"}:
                required_warn_or_deferred.add(oid)
                for field in ("owner", "residual_risk", "next_action"):
                    if item.get(field) in (None, ""):
                        issues.append(f"BLOCK {path}: evidence[{idx}] result={item.get('result')} for required obligation requires {field}")
        if item.get("result") not in {"pass", "warn", "block", "deferred"}:
            issues.append(f"BLOCK {path}: evidence[{idx}].result must be pass|warn|block|deferred")
        if item.get("result") == "pass":
            artifact = item.get("artifact")
            if artifact in (None, ""):
                issues.append(f"BLOCK {path}: evidence[{idx}] result=pass requires artifact")
            elif root is not None:
                if not _artifact_exists(root, artifact):
                    issues.append(f"BLOCK {path}: evidence[{idx}] artifact not found: {artifact}")
                elif obj.get("run_id") and not _artifact_run_bound(str(artifact), str(obj.get("run_id"))):
                    issues.append(f"BLOCK {path}: evidence[{idx}] artifact must be run-bound: {artifact}")
        if item.get("summary") in (None, ""):
            issues.append(f"BLOCK {path}: evidence[{idx}] missing summary")
    readiness = obj.get("next_phase_readiness") if isinstance(obj.get("next_phase_readiness"), dict) else {}
    readiness_status = readiness.get("status")
    if readiness_status not in VALID_NEXT_PHASE_READINESS:
        issues.append(f"BLOCK {path}: next_phase_readiness.status must be one of {sorted(VALID_NEXT_PHASE_READINESS)}")
    if readiness.get("target_phase") != "verify":
        issues.append(f"BLOCK {path}: next_phase_readiness.target_phase must be 'verify'")
    missing = sorted(required_obligations - seen_required)
    if readiness_status == "ready" and missing:
        issues.append(f"BLOCK {path}: next_phase_readiness=ready but required PIV evidence obligations are missing: {missing}")
    if readiness_status == "ready":
        not_pass = sorted(required_obligations - required_pass)
        if not_pass:
            issues.append(f"BLOCK {path}: next_phase_readiness=ready requires required PIV evidence result=pass: {not_pass}")
    if readiness_status == "ready_with_deferred_items" and required_warn_or_deferred and not readiness.get("deferred_items"):
        issues.append(f"BLOCK {path}: ready_with_deferred_items requires next_phase_readiness.deferred_items for warn/deferred required evidence")
    drift = obj.get("intent_drift") if isinstance(obj.get("intent_drift"), dict) else {}
    deviations = drift.get("deviations") if isinstance(drift.get("deviations"), list) else []
    detected = drift.get("detected")
    if not isinstance(detected, bool):
        issues.append(f"BLOCK {path}: intent_drift.detected must be boolean")
    if detected is False and deviations:
        issues.append(f"BLOCK {path}: intent_drift.detected=false conflicts with non-empty deviations")
    if detected is True:
        if not deviations:
            issues.append(f"BLOCK {path}: intent_drift.detected=true requires deviations")
        for idx, deviation in enumerate(deviations):
            if not isinstance(deviation, dict):
                issues.append(f"BLOCK {path}: intent_drift.deviations[{idx}] must be a mapping")
                continue
            if deviation.get("disposition") not in {"accepted", "replanned", "blocked", "deferred"}:
                issues.append(f"BLOCK {path}: intent_drift.deviations[{idx}] requires disposition accepted|replanned|blocked|deferred")
            for field in ("id", "description", "owner"):
                if deviation.get(field) in (None, ""):
                    issues.append(f"BLOCK {path}: intent_drift.deviations[{idx}] missing {field}")
    invariants = obj.get("invariants") if isinstance(obj.get("invariants"), dict) else {}
    for field in ("authority_preserved", "write_boundary_preserved", "rollback_preserved", "privacy_boundary_preserved"):
        if field not in invariants:
            issues.append(f"BLOCK {path}: invariants missing {field}")
    if package_dir is not None:
        semantic_artifacts = {
            "work_narrative": ("work-narrative.md", ["intent", "work", "why"]),
            "decision_log": ("decision-log.md", ["decision", "rationale"]),
            "evidence_map": ("evidence-map.md", ["evidence", "verification"]),
            "intent_drift_and_deviations": ("intent-drift-and-deviations.md", ["intent", "drift", "disposition"]),
            "verify_handoff": ("verify-handoff.md", ["verify", "handoff", "readiness"]),
        }
        for label, (name, terms) in semantic_artifacts.items():
            rel = Path("executions") / str(run_id) / name
            artifact = package_dir / name
            _validate_semantic_markdown(path, label, str(rel), artifact.read_text(encoding="utf-8") if artifact.exists() else None, issues, terms)


def validate_piv_assessment(path: Path, obj: dict, issues: list[str], *, root: Path | None = None) -> None:
    required = ["kind", "phase", "run_id", "piv_contract", "assessments", "overall_status"]
    check_required(str(path), obj, required, issues)
    if obj.get("phase") != "verify":
        issues.append(f"BLOCK {path}: PIV assessment phase must be 'verify'")
    piv = _load_piv_contract(root, obj.get("piv_contract"))
    if piv is None:
        issues.append(f"BLOCK {path}: PIV assessment piv_contract unreadable or missing")
        required_obligations: set[str] = set()
    else:
        required_obligations = {str(item.get("id")) for item in (piv.get("evidence_obligations") or []) if isinstance(item, dict) and item.get("id")}
    assessments = obj.get("assessments") if isinstance(obj.get("assessments"), list) else []
    seen: set[str] = set()
    if not assessments:
        issues.append(f"BLOCK {path}: PIV assessment requires non-empty assessments")
    for idx, item in enumerate(assessments):
        if not isinstance(item, dict):
            issues.append(f"BLOCK {path}: assessments[{idx}] must be a mapping")
            continue
        oid = str(item.get("obligation_id") or "")
        if oid:
            if oid in seen:
                issues.append(f"BLOCK {path}: duplicate PIV obligation assessment {oid!r}")
            seen.add(oid)
        if required_obligations and oid not in required_obligations:
            issues.append(f"BLOCK {path}: assessments[{idx}] unknown obligation_id {oid!r}")
        if item.get("state") not in {"pass", "warn", "block", "deferred"}:
            issues.append(f"BLOCK {path}: assessments[{idx}].state must be pass|warn|block|deferred")
        if not item.get("evidence_refs"):
            issues.append(f"BLOCK {path}: assessments[{idx}] missing evidence_refs")
        if item.get("state") in {"warn", "block", "deferred"}:
            for field in ("owner", "next_action", "result_reason"):
                if item.get(field) in (None, ""):
                    issues.append(f"BLOCK {path}: assessments[{idx}] state={item.get('state')} missing {field}")
    missing = sorted(required_obligations - seen)
    if missing:
        issues.append(f"BLOCK {path}: PIV assessment missing obligation(s): {missing}")
    if obj.get("overall_status") == "pass" and any(isinstance(i, dict) and i.get("state") == "block" for i in assessments):
        issues.append(f"BLOCK {path}: PIV assessment overall_status=pass with blocked obligation")


def validate_verify_package_selection(path: Path, obj: dict, issues: list[str], *, root: Path | None = None) -> None:
    required = ["kind", "phase", "run_id", "verified_facts", "assumptions", "deferred_items", "warnings", "blockers", "findings_dispositions", "resolve_readiness", "semantic_package"]
    check_required(str(path), obj, required, issues)
    if obj.get("phase") != "verify":
        issues.append(f"BLOCK {path}: verify package phase must be 'verify'")
    run_id = obj.get("run_id")
    package_dir = _validate_package_directory(root, path, "verify", run_id, issues)
    sem = obj.get("semantic_package") if isinstance(obj.get("semantic_package"), dict) else {}
    concerns = {
        "piv_assessment": ("piv-assessment.md", ["piv", "assessment"]),
        "verified_facts": ("verified-facts.md", ["fact", "evidence"]),
        "assumptions_and_deferred_items": ("assumptions-and-deferred-items.md", ["assumption", "deferred", "owner"]),
        "findings_and_dispositions": ("findings-and-dispositions.md", ["finding", "disposition"]),
        "council_review": ("council-review.md", ["council", "review"]),
        "resolve_readiness": ("resolve-readiness.md", ["resolve", "readiness"]),
    }
    for label, (default_name, terms) in concerns.items():
        artifact = sem.get(label) or (str(Path("verification") / str(run_id) / default_name) if run_id else "")
        _validate_semantic_markdown(path, label, artifact, _read_artifact_text(root, artifact), issues, terms)
        if package_dir is not None and not _artifact_under_package(root, package_dir, artifact):
            issues.append(f"BLOCK {path}: {label} artifact must live under verification/{run_id}/: {artifact}")
    facts = obj.get("verified_facts") if isinstance(obj.get("verified_facts"), list) else []
    if not facts:
        issues.append(f"BLOCK {path}: verified_facts must not be empty")
    for idx, fact in enumerate(facts):
        if not isinstance(fact, dict):
            issues.append(f"BLOCK {path}: verified_facts[{idx}] must be a mapping")
            continue
        for field in ("fact_id", "claim", "source_evidence", "source_path", "source_locator", "validation_method", "owner", "review_status"):
            if fact.get(field) in (None, ""):
                issues.append(f"BLOCK {path}: verified_facts[{idx}] missing {field}")
        if root is not None and fact.get("source_path") and not _artifact_exists(root, fact.get("source_path")):
            issues.append(f"BLOCK {path}: verified_facts[{idx}] source_path not found: {fact.get('source_path')}")
    assumptions = obj.get("assumptions") if isinstance(obj.get("assumptions"), list) else []
    for idx, assumption in enumerate(assumptions):
        if not isinstance(assumption, dict):
            issues.append(f"BLOCK {path}: assumptions[{idx}] must be a mapping")
            continue
        if assumption.get("disposition") not in {"accepted_risk", "deferred", "pending", "not_applicable"}:
            issues.append(f"BLOCK {path}: assumptions[{idx}].disposition is invalid")
        for field in ("assumption_id", "claim", "owner", "accepted_by", "residual_risk", "next_phase_obligation"):
            if assumption.get(field) in (None, ""):
                issues.append(f"BLOCK {path}: assumptions[{idx}] missing {field}")
    deferred = obj.get("deferred_items") if isinstance(obj.get("deferred_items"), list) else []
    for idx, item in enumerate(deferred):
        if not isinstance(item, dict):
            issues.append(f"BLOCK {path}: deferred_items[{idx}] must be a mapping")
            continue
        for field in ("item_id", "description", "reason_deferred", "owner", "revisit_trigger", "next_phase_obligation", "target_phase", "accepted_by"):
            if item.get(field) in (None, ""):
                issues.append(f"BLOCK {path}: deferred_items[{idx}] missing {field}")
    blockers = obj.get("blockers") if isinstance(obj.get("blockers"), list) else []
    for idx, blocker in enumerate(blockers):
        if not isinstance(blocker, dict):
            issues.append(f"BLOCK {path}: blockers[{idx}] must be a mapping")
            continue
        if blocker.get("state") not in {"open", "resolved", "accepted_risk", "deferred"}:
            issues.append(f"BLOCK {path}: blockers[{idx}].state is invalid")
        for field in ("blocker_id", "message", "owner", "resolution_path"):
            if blocker.get(field) in (None, ""):
                issues.append(f"BLOCK {path}: blockers[{idx}] missing {field}")
        if blocker.get("state") in {"accepted_risk", "deferred"}:
            for field in ("accepted_by", "residual_risk", "next_phase_obligation"):
                if blocker.get(field) in (None, ""):
                    issues.append(f"BLOCK {path}: blockers[{idx}] state={blocker.get('state')} missing {field}")
        if blocker.get("state") == "open" and obj.get("resolve_readiness", {}).get("ready_for_resolve") is True:
            issues.append(f"BLOCK {path}: ready_for_resolve=true with open blocker {blocker.get('blocker_id')}")
    for idx, finding in enumerate(obj.get("findings_dispositions") if isinstance(obj.get("findings_dispositions"), list) else []):
        if not isinstance(finding, dict):
            issues.append(f"BLOCK {path}: findings_dispositions[{idx}] must be a mapping")
            continue
        for field in ("finding_id", "classification", "disposition", "owner", "evidence_ref"):
            if finding.get(field) in (None, ""):
                issues.append(f"BLOCK {path}: findings_dispositions[{idx}] missing {field}")


def validate_verify_resolve_readiness(path: Path, obj: dict, issues: list[str], *, root: Path | None = None) -> None:
    required = ["kind", "phase", "run_id", "ready_for_resolve", "overall_status", "verification_package", "verified_facts_summary", "piv_summary", "evidence_cluster_summary", "residual_risks", "open_assumptions", "deferred_items", "blockers", "heartgate_coherence_status", "self_approval_guard", "decision_rationale", "accepted_by"]
    check_required(str(path), obj, required, issues)
    if obj.get("phase") != "verify":
        issues.append(f"BLOCK {path}: verify resolve readiness phase must be 'verify'")
    expected_pkg = f"verification/{obj.get('run_id')}-verify-selection.yaml" if obj.get("run_id") else None
    if expected_pkg and obj.get("verification_package") != expected_pkg:
        issues.append(f"BLOCK {path}: verification_package must be {expected_pkg}")
    package_obj = None
    if root is not None and not _artifact_exists(root, obj.get("verification_package")):
        issues.append(f"BLOCK {path}: verification_package not found: {obj.get('verification_package')}")
    elif root is not None and obj.get("verification_package"):
        try:
            pkg_path = base_dir(root) / str(obj.get("verification_package"))
            package_obj = yaml.safe_load(pkg_path.read_text())
            if not isinstance(package_obj, dict) or package_obj.get("kind") != "uacp.verification_package":
                issues.append(f"BLOCK {path}: verification_package must be kind uacp.verification_package")
            elif package_obj.get("run_id") != obj.get("run_id"):
                issues.append(f"BLOCK {path}: verification_package run_id does not match readiness run_id")
        except Exception as exc:
            issues.append(f"BLOCK {path}: verification_package unreadable: {exc}")
    blockers = obj.get("blockers") if isinstance(obj.get("blockers"), list) else []
    open_blockers = [b for b in blockers if isinstance(b, dict) and b.get("state") == "open"]
    if obj.get("ready_for_resolve") is True and open_blockers:
        issues.append(f"BLOCK {path}: ready_for_resolve=true with open blockers")
    if obj.get("overall_status") == "pass" and open_blockers:
        issues.append(f"BLOCK {path}: overall_status=pass with open blockers")
    clusters = obj.get("evidence_cluster_summary") if isinstance(obj.get("evidence_cluster_summary"), list) else []
    if obj.get("ready_for_resolve") is True and not any(isinstance(c, dict) and c.get("state") in {"pass", "warn"} for c in clusters):
        issues.append(f"BLOCK {path}: ready_for_resolve=true requires at least one evidence_cluster_summary item with state pass|warn")
    for idx, cluster in enumerate(clusters):
        if not isinstance(cluster, dict):
            issues.append(f"BLOCK {path}: evidence_cluster_summary[{idx}] must be a mapping")
            continue
        if cluster.get("state") not in VALID_CLUSTER_STATES:
            issues.append(f"BLOCK {path}: evidence_cluster_summary[{idx}].state is invalid")
        artifact_path = cluster.get("artifact_path")
        if artifact_path in (None, ""):
            issues.append(f"BLOCK {path}: evidence_cluster_summary[{idx}] missing artifact_path")
        elif root is not None and not _artifact_exists(root, artifact_path):
            issues.append(f"BLOCK {path}: evidence_cluster_summary[{idx}] artifact_path not found")
        elif obj.get("run_id") and not str(artifact_path).startswith(f"verification/{obj.get('run_id')}"):
            issues.append(f"BLOCK {path}: evidence_cluster_summary[{idx}] artifact_path must be bound to run_id")
    if package_obj and isinstance(package_obj, dict):
        fact_ids = {str(f.get("fact_id")) for f in (package_obj.get("verified_facts") or []) if isinstance(f, dict) and f.get("fact_id")}
        for idx, fact_id in enumerate(obj.get("verified_facts_summary") if isinstance(obj.get("verified_facts_summary"), list) else []):
            if str(fact_id) not in fact_ids:
                issues.append(f"BLOCK {path}: verified_facts_summary[{idx}] not found in verification package: {fact_id}")
    piv_summary = obj.get("piv_summary") if isinstance(obj.get("piv_summary"), dict) else {}
    expected_piv = f"verification/{obj.get('run_id')}-piv-assessment.yaml" if obj.get("run_id") else None
    if expected_piv and piv_summary.get("artifact") != expected_piv:
        issues.append(f"BLOCK {path}: piv_summary.artifact must be {expected_piv}")
    if piv_summary.get("status") not in {"pass", "warn", "block", "deferred", "not_applicable"}:
        issues.append(f"BLOCK {path}: piv_summary.status is invalid")
    if root is not None and expected_piv and (base_dir(root) / f"plans/{obj.get('run_id')}-piv.yaml").exists() and not _artifact_exists(root, expected_piv):
        issues.append(f"BLOCK {path}: PIV assessment required when plan PIV exists: {expected_piv}")
    if root is not None and piv_summary.get("artifact") and _artifact_exists(root, piv_summary.get("artifact")):
        try:
            pa = yaml.safe_load((base_dir(root) / str(piv_summary.get("artifact"))).read_text())
            if not isinstance(pa, dict) or pa.get("kind") != "uacp.piv_assessment":
                issues.append(f"BLOCK {path}: piv_summary.artifact must be kind uacp.piv_assessment")
            elif pa.get("run_id") != obj.get("run_id"):
                issues.append(f"BLOCK {path}: piv_summary artifact run_id does not match readiness run_id")
        except Exception as exc:
            issues.append(f"BLOCK {path}: piv_summary artifact unreadable: {exc}")
    for idx, blocker in enumerate(blockers):
        if not isinstance(blocker, dict):
            issues.append(f"BLOCK {path}: blockers[{idx}] must be a mapping")
            continue
        if blocker.get("state") not in {"open", "resolved", "accepted_risk", "deferred"}:
            issues.append(f"BLOCK {path}: blockers[{idx}].state is invalid")
        if blocker.get("state") in {"accepted_risk", "deferred"}:
            for field in ("accepted_by", "residual_risk", "next_phase_obligation", "owner"):
                if blocker.get(field) in (None, ""):
                    issues.append(f"BLOCK {path}: blockers[{idx}] state={blocker.get('state')} missing {field}")
    for idx, assumption in enumerate(obj.get("open_assumptions") if isinstance(obj.get("open_assumptions"), list) else []):
        if not isinstance(assumption, dict):
            issues.append(f"BLOCK {path}: open_assumptions[{idx}] must be a mapping")
            continue
        for field in ("assumption_id", "owner", "accepted_by", "next_phase_obligation", "residual_risk"):
            if assumption.get(field) in (None, ""):
                issues.append(f"BLOCK {path}: open_assumptions[{idx}] missing {field}")
    for idx, item in enumerate(obj.get("deferred_items") if isinstance(obj.get("deferred_items"), list) else []):
        if not isinstance(item, dict):
            issues.append(f"BLOCK {path}: deferred_items[{idx}] must be a mapping")
            continue
        for field in ("item_id", "owner", "accepted_by", "next_phase_obligation", "revisit_trigger"):
            if item.get(field) in (None, ""):
                issues.append(f"BLOCK {path}: deferred_items[{idx}] missing {field}")
    coherence = obj.get("heartgate_coherence_status") if isinstance(obj.get("heartgate_coherence_status"), dict) else {}
    if coherence.get("required") is True:
        if coherence.get("status") not in {"pass", "warn"}:
            issues.append(f"BLOCK {path}: required heartgate coherence must be pass|warn")
        if root is not None and not _artifact_exists(root, coherence.get("artifact_path")):
            issues.append(f"BLOCK {path}: required heartgate coherence artifact not found")
        elif root is not None and coherence.get("artifact_path"):
            candidate = Path(str(coherence.get("artifact_path")))
            if not candidate.is_absolute():
                candidate = base_dir(root) / candidate
            try:
                data = yaml.safe_load(candidate.read_text())
                if isinstance(data, dict) and data.get("run_id") != obj.get("run_id"):
                    issues.append(f"BLOCK {path}: heartgate coherence artifact run_id does not match readiness run_id")
                lenses = set(data.get("lenses") or []) if isinstance(data, dict) else set()
                required_lenses = {"doctrine_coherence", "cross_artifact_consistency", "runtime_state_alignment", "warning_and_deferred_item_honesty", "authority_plane_integrity", "next_phase_readiness"}
                missing_lenses = sorted(required_lenses - lenses)
                if missing_lenses:
                    issues.append(f"BLOCK {path}: heartgate coherence artifact missing lens(es): {missing_lenses}")
            except Exception as exc:
                issues.append(f"BLOCK {path}: heartgate coherence artifact unreadable: {exc}")
    guard = obj.get("self_approval_guard") if isinstance(obj.get("self_approval_guard"), dict) else {}
    if guard.get("status") not in {"pass", "block"}:
        issues.append(f"BLOCK {path}: self_approval_guard.status must be pass|block")
    if guard.get("verify_self_remediated_material_findings") is True and guard.get("independent_reverification") is not True:
        issues.append(f"BLOCK {path}: VERIFY self-remediation requires independent_reverification=true")
    if obj.get("ready_for_resolve") is True and guard.get("status") != "pass":
        issues.append(f"BLOCK {path}: ready_for_resolve=true requires self_approval_guard.status=pass")


def _load_yaml_artifact(root: Path | None, artifact: object) -> dict | None:
    if root is None or not artifact:
        return None
    gov = base_dir(root)  # artifact paths are base-relative under .uacp/
    candidate = Path(str(artifact))
    try:
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (gov / candidate).resolve()
        gov_resolved = gov.resolve()
        if resolved != gov_resolved and gov_resolved not in resolved.parents:
            return None
        if not resolved.exists() or not resolved.is_file():
            return None
        data = yaml.safe_load(resolved.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def validate_resolve_package_selection(path: Path, obj: dict, issues: list[str], *, root: Path | None = None) -> None:
    required = ["kind", "phase", "run_id", "verify_resolve_readiness", "semantic_package", "final_decision", "residual_risks", "deferred_items", "lesson_dispositions", "operator_handoff"]
    check_required(str(path), obj, required, issues)
    if obj.get("phase") != "resolve":
        issues.append(f"BLOCK {path}: resolve package phase must be 'resolve'")
    run_id = obj.get("run_id")
    package_dir = _validate_package_directory(root, path, "resolve", run_id, issues)
    expected_readiness = f"verification/{run_id}-resolve-readiness.yaml" if run_id else None
    if expected_readiness and obj.get("verify_resolve_readiness") != expected_readiness:
        issues.append(f"BLOCK {path}: verify_resolve_readiness must be {expected_readiness}")
    readiness = _load_yaml_artifact(root, obj.get("verify_resolve_readiness"))
    if readiness is None:
        issues.append(f"BLOCK {path}: verify_resolve_readiness unreadable or missing")
    else:
        if readiness.get("kind") != "uacp.verify_resolve_readiness":
            issues.append(f"BLOCK {path}: verify_resolve_readiness must be kind uacp.verify_resolve_readiness")
        if readiness.get("run_id") != run_id:
            issues.append(f"BLOCK {path}: verify_resolve_readiness run_id mismatch")
        if readiness.get("ready_for_resolve") is not True:
            issues.append(f"BLOCK {path}: VERIFY readiness is not ready_for_resolve=true")
        if any(isinstance(b, dict) and b.get("state") == "open" for b in readiness.get("blockers") or []):
            issues.append(f"BLOCK {path}: VERIFY readiness carries open blocker")
    sem = obj.get("semantic_package") if isinstance(obj.get("semantic_package"), dict) else {}
    concerns = {
        "closure_summary": ("closure-summary.md", ["closure", "summary"]),
        "final_decision": ("final-decision.md", ["final", "decision"]),
        "residual_risks": ("residual-risks.md", ["residual", "risk"]),
        "lessons_and_dispositions": ("lessons-and-dispositions.md", ["lesson", "disposition"]),
        "state_and_memory_disposition": ("state-and-memory-disposition.md", ["state", "memory", "skill"]),
        "operator_handoff": ("operator-handoff.md", ["conclusion", "risk", "next"]),
    }
    for label, (default_name, terms) in concerns.items():
        artifact = sem.get(label) or (str(Path("resolutions") / str(run_id) / default_name) if run_id else "")
        _validate_semantic_markdown(path, label, artifact, _read_artifact_text(root, artifact), issues, terms)
        if package_dir is not None and not _artifact_under_package(root, package_dir, artifact):
            issues.append(f"BLOCK {path}: {label} artifact must live under resolutions/{run_id}/: {artifact}")
    decision = obj.get("final_decision") if isinstance(obj.get("final_decision"), dict) else {}
    if decision.get("status") not in {"resolved", "resolved_with_warnings", "blocked"}:
        issues.append(f"BLOCK {path}: final_decision.status must be resolved|resolved_with_warnings|blocked")
    for field in ("decision", "rationale", "accepted_by", "evidence_pointer"):
        if decision.get(field) in (None, ""):
            issues.append(f"BLOCK {path}: final_decision missing {field}")
    if decision.get("status") in {"resolved", "resolved_with_warnings"} and readiness and readiness.get("ready_for_resolve") is not True:
        issues.append(f"BLOCK {path}: cannot resolve when VERIFY readiness is not ready")
    for idx, risk in enumerate(obj.get("residual_risks") if isinstance(obj.get("residual_risks"), list) else []):
        if not isinstance(risk, dict):
            issues.append(f"BLOCK {path}: residual_risks[{idx}] must be a mapping")
            continue
        for field in ("risk_id", "description", "owner", "accepted_by", "condition", "source"):
            if risk.get(field) in (None, ""):
                issues.append(f"BLOCK {path}: residual_risks[{idx}] missing {field}")
    for idx, item in enumerate(obj.get("deferred_items") if isinstance(obj.get("deferred_items"), list) else []):
        if not isinstance(item, dict):
            issues.append(f"BLOCK {path}: deferred_items[{idx}] must be a mapping")
            continue
        for field in ("item_id", "description", "owner", "accepted_by", "condition", "next_phase_obligation", "source"):
            if item.get(field) in (None, ""):
                issues.append(f"BLOCK {path}: deferred_items[{idx}] missing {field}")
    # If readiness had risks/deferred items, resolve must carry at least same identifiers or explicit none assertion is invalid.
    if readiness:
        ready_risks = {str(r.get("risk_id") or r.get("id") or r.get("description")) for r in (readiness.get("residual_risks") or []) if isinstance(r, dict)}
        carried_risks = {str(r.get("risk_id") or r.get("id") or r.get("description")) for r in (obj.get("residual_risks") or []) if isinstance(r, dict)}
        missing = sorted(x for x in ready_risks if x and x not in carried_risks)
        if missing:
            issues.append(f"BLOCK {path}: residual risks from VERIFY readiness not carried forward: {missing}")
        ready_deferred = {str(d.get("item_id") or d.get("id") or d.get("description")) for d in (readiness.get("deferred_items") or []) if isinstance(d, dict)}
        carried_deferred = {str(d.get("item_id") or d.get("id") or d.get("description")) for d in (obj.get("deferred_items") or []) if isinstance(d, dict)}
        missing_d = sorted(x for x in ready_deferred if x and x not in carried_deferred)
        if missing_d:
            issues.append(f"BLOCK {path}: deferred items from VERIFY readiness not carried forward: {missing_d}")
    lessons = obj.get("lesson_dispositions") if isinstance(obj.get("lesson_dispositions"), list) else []
    if not lessons:
        issues.append(f"BLOCK {path}: lesson_dispositions must not be empty; use no_action with rationale if none")
    for idx, lesson in enumerate(lessons):
        if not isinstance(lesson, dict):
            issues.append(f"BLOCK {path}: lesson_dispositions[{idx}] must be a mapping")
            continue
        if lesson.get("classification") not in {"memory", "skill", "docs", "knowledge", "no_action"}:
            issues.append(f"BLOCK {path}: lesson_dispositions[{idx}].classification is invalid")
        for field in ("lesson_id", "source_artifact", "rationale", "owner", "durability", "risk_if_persisted", "accepted_by", "disposition_basis"):
            if lesson.get(field) in (None, ""):
                issues.append(f"BLOCK {path}: lesson_dispositions[{idx}] missing {field}")
        if lesson.get("classification") in {"memory", "skill", "docs", "knowledge"} and lesson.get("target_artifact") in (None, ""):
            issues.append(f"BLOCK {path}: lesson_dispositions[{idx}] classification={lesson.get('classification')} missing target_artifact")
    handoff = obj.get("operator_handoff") if isinstance(obj.get("operator_handoff"), dict) else {}
    for field in ("conclusion", "decision", "risks", "next", "not_next", "evidence_pointer"):
        if handoff.get(field) in (None, ""):
            issues.append(f"BLOCK {path}: operator_handoff missing {field}")
    if handoff.get("raw_inventory") is True:
        issues.append(f"BLOCK {path}: operator_handoff must not be raw inventory")


def validate_resolve_closure(path: Path, obj: dict, issues: list[str], *, root: Path | None = None) -> None:
    required = ["kind", "phase", "run_id", "resolve_package", "verify_resolve_readiness", "final_decision", "closed_scope", "residual_risks", "deferred_items", "lesson_dispositions", "operator_handoff", "state_disposition"]
    check_required(str(path), obj, required, issues)
    if obj.get("phase") != "resolve":
        issues.append(f"BLOCK {path}: resolve closure phase must be 'resolve'")
    closed_scope = obj.get("closed_scope")
    if not isinstance(closed_scope, list) or not closed_scope:
        issues.append(f"BLOCK {path}: closed_scope must be a non-empty list")
    else:
        for idx, scope in enumerate(closed_scope):
            if not isinstance(scope, dict):
                issues.append(f"BLOCK {path}: closed_scope[{idx}] must be a mapping")
                continue
            for field in ("scope_id", "description", "source_artifact", "evidence_ref"):
                if scope.get(field) in (None, ""):
                    issues.append(f"BLOCK {path}: closed_scope[{idx}] missing {field}")
            if obj.get("run_id") and str(scope.get("source_artifact", "")).split("/")[0] not in {"verification", "resolutions", "plans", "proposals"}:
                issues.append(f"BLOCK {path}: closed_scope[{idx}] source_artifact must be a UACP artifact path")
            if root is not None and scope.get("source_artifact") and not _artifact_exists(root, scope.get("source_artifact")):
                issues.append(f"BLOCK {path}: closed_scope[{idx}] source_artifact not found")
    run_id = obj.get("run_id")
    expected_pkg = f"resolutions/{run_id}-resolve-selection.yaml" if run_id else None
    if expected_pkg and obj.get("resolve_package") != expected_pkg:
        issues.append(f"BLOCK {path}: resolve_package must be {expected_pkg}")
    pkg = _load_yaml_artifact(root, obj.get("resolve_package"))
    if pkg is None:
        issues.append(f"BLOCK {path}: resolve_package unreadable or missing")
    else:
        if pkg.get("kind") != "uacp.resolve_package":
            issues.append(f"BLOCK {path}: resolve_package must be kind uacp.resolve_package")
        if pkg.get("run_id") != run_id:
            issues.append(f"BLOCK {path}: resolve_package run_id mismatch")
    expected_readiness = f"verification/{run_id}-resolve-readiness.yaml" if run_id else None
    if expected_readiness and obj.get("verify_resolve_readiness") != expected_readiness:
        issues.append(f"BLOCK {path}: verify_resolve_readiness must be {expected_readiness}")
    readiness = _load_yaml_artifact(root, obj.get("verify_resolve_readiness"))
    if readiness is None:
        issues.append(f"BLOCK {path}: verify_resolve_readiness unreadable or missing")
    elif readiness.get("ready_for_resolve") is not True:
        issues.append(f"BLOCK {path}: cannot close when VERIFY readiness not ready")
    elif root is not None:
        nested: list[str] = []
        validate_verify_resolve_readiness(path, readiness, nested, root=root)
        for issue in nested:
            if str(issue).startswith("BLOCK"):
                issues.append(f"BLOCK {path}: verify_resolve_readiness invalid for closure: {issue}")
    decision = obj.get("final_decision") if isinstance(obj.get("final_decision"), dict) else {}
    if decision.get("status") not in {"resolved", "resolved_with_warnings", "blocked"}:
        issues.append(f"BLOCK {path}: final_decision.status invalid")
    if decision.get("status") == "blocked" and obj.get("state_disposition", {}).get("run_status") == "resolved":
        issues.append(f"BLOCK {path}: blocked closure cannot set run_status resolved")
    for field in ("decision", "rationale", "accepted_by", "evidence_pointer"):
        if decision.get(field) in (None, ""):
            issues.append(f"BLOCK {path}: final_decision missing {field}")
    state = obj.get("state_disposition") if isinstance(obj.get("state_disposition"), dict) else {}
    for field in ("run_status", "state_update", "registry_update", "memory_action"):
        if state.get(field) in (None, ""):
            issues.append(f"BLOCK {path}: state_disposition missing {field}")
    if state.get("run_status") not in {"resolved", "resolved_with_warnings", "blocked", "deferred"}:
        issues.append(f"BLOCK {path}: state_disposition.run_status invalid")
    if state.get("memory_action") not in {"none", "memory_added", "skill_updated", "docs_updated", "knowledge_recorded"}:
        issues.append(f"BLOCK {path}: state_disposition.memory_action invalid")
    sources = []
    if isinstance(readiness, dict):
        sources.append(("VERIFY readiness", readiness))
    if isinstance(pkg, dict):
        sources.append(("resolve package", pkg))
    closure_risks = {str(r.get("risk_id") or r.get("id") or r.get("description")) for r in (obj.get("residual_risks") or []) if isinstance(r, dict)}
    closure_deferred = {str(d.get("item_id") or d.get("id") or d.get("description")) for d in (obj.get("deferred_items") or []) if isinstance(d, dict)}
    for label, source in sources:
        source_risks = {str(r.get("risk_id") or r.get("id") or r.get("description")) for r in (source.get("residual_risks") or []) if isinstance(r, dict)}
        missing = sorted(x for x in source_risks if x and x not in closure_risks)
        if missing:
            issues.append(f"BLOCK {path}: residual risks from {label} not carried into closure: {missing}")
        source_deferred = {str(d.get("item_id") or d.get("id") or d.get("description")) for d in (source.get("deferred_items") or []) if isinstance(d, dict)}
        missing_d = sorted(x for x in source_deferred if x and x not in closure_deferred)
        if missing_d:
            issues.append(f"BLOCK {path}: deferred items from {label} not carried into closure: {missing_d}")
    handoff = obj.get("operator_handoff") if isinstance(obj.get("operator_handoff"), dict) else {}
    if handoff.get("raw_inventory") is True:
        issues.append(f"BLOCK {path}: operator_handoff must not be raw inventory")




def _path_bound_to_run_id(rel: object, run_id: str) -> bool:
    if not rel or not run_id:
        return False
    parts = Path(str(rel)).parts
    stem = Path(str(rel)).name
    candidates = {part for part in parts} | {stem}
    return any(part == run_id or part.startswith(run_id + "-") for part in candidates)


def validate_current_state(root: Path, issues: list[str]) -> None:
    path = base_dir(root) / "state/current.yaml"
    obj = require_map(load_yaml(path), path)
    required = ["kind", *CURRENT_POINTER_REQUIRED_FIELDS]
    check_required(str(path), obj, required, issues)
    if obj.get("kind") != "uacp.current_state":
        issues.append(f"BLOCK {path}: kind must be uacp.current_state")
    if obj.get("mutation_policy") != "uacp_state_required":
        issues.append(f"BLOCK {path}: mutation_policy must be uacp_state_required after bootstrap closure")
    if obj.get("bootstrap_closed") is not True:
        issues.append(f"BLOCK {path}: bootstrap_closed must be true")
    if obj.get("governed_mutation_active") is not True:
        issues.append(f"BLOCK {path}: governed_mutation_active must be true")
    active_run_id = str(obj.get("active_run_id") or "")
    for field in ("active_run_manifest", "current_transition_artifact", "kanban_binding_artifact"):
        rel = obj.get(field)
        if rel and not _artifact_exists(root, rel):
            issues.append(f"BLOCK {path}: {field} not found: {rel}")
        if active_run_id and rel and not _path_bound_to_run_id(rel, active_run_id):
            issues.append(f"BLOCK {path}: {field} must be bound to active_run_id {active_run_id}: {rel}")

def _load_heartgate_allowed_transitions(root: Path) -> list[str]:
    """Read ``[heartgate].allowed_transitions`` from ``config/uacp.toml``.

    Sourced from uacp.toml (config collapse) instead of the retired
    ``config/guardian-policy.yaml``. A missing/unparsable uacp.toml is not an
    error here: it yields an empty list so the consistency check is suppressed
    rather than crashing the in-process validator (Heartgate path)."""
    toml_path = root / "config" / "uacp.toml"
    if not toml_path.exists():
        return []
    try:
        with toml_path.open("rb") as fh:
            toml_cfg = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return []
    return list((toml_cfg.get("heartgate") or {}).get("allowed_transitions") or [])


def validate_configs(root: Path, issues: list[str]) -> dict:
    configs = {}
    for rel in [
        "config/phase-transitions.yaml",
        "config/evidence-clusters.yaml",
        "config/state.yaml",
    ]:
        path = root / rel
        configs[rel] = require_map(load_yaml(path), path)
    # heartgate.allowed_transitions now sourced from config/uacp.toml [heartgate]
    # (was config/guardian-policy.yaml, retired in the config-collapse refactor).
    configs["heartgate"] = {"allowed_transitions": _load_heartgate_allowed_transitions(root)}
    validate_evidence_registry(root, issues)
    validate_current_state(root, issues)
    return configs


def validate_transition_config_consistency(configs: dict, issues: list[str]) -> None:
    # NOTE (post-Slice-4b T4d-1): both WARN cross-checks below key off
    # phase-transitions.yaml `stages`, which `validate_configs` reads RAW (not via
    # load_phase_transitions, so the codified stages_default() is NOT injected here).
    # Production no longer ships a `stages` block (codified to engines/domain), so
    # `stages` is empty for prod and BOTH checks degrade to silence. This is fine:
    # the hard graph drift-guard is the repo-level agreement test
    # (tests/unit/uacp_core/test_phase_graph.py, phase_graph vs config/uacp.toml).
    # These WARNs now only fire for a project that still ships an inline `stages`.
    phase_cfg = configs.get("config/phase-transitions.yaml") or {}
    heartgate_cfg = configs.get("heartgate") or {}
    stages = phase_cfg.get("stages") or {}
    canonical = sorted(
        f"{stage}->{target}"
        for stage, body in stages.items()
        for target in (body.get("exits_to") or [])
    )
    allowed = sorted(str(item) for item in (heartgate_cfg.get("allowed_transitions") or []))
    if allowed and canonical and allowed != canonical:
        issues.append("WARN config/uacp.toml [heartgate]: allowed_transitions differs from config/phase-transitions.yaml stages")

    # Also cross-check against the canonical lifecycle graph in
    # engines/domain/phase_graph.py (the single source of truth). WARN-only and
    # best-effort: the in-process Heartgate path may run against a fixture config
    # using the state-machine `resolved` convention with no canonical reference,
    # so a difference (or an unavailable canonical module) must never BLOCK or
    # raise — it degrades to silence. Only the production config has the richer
    # lifecycle convention this graph mirrors; the repo-level agreement test
    # (tests/unit/uacp_core/test_phase_graph.py) is the hard guard.
    if stages:
        try:
            from engines.domain import lifecycle_edges
        except Exception:
            lifecycle_edges = None  # canonical module unavailable; degrade to silence
        graph = sorted(f"{src}->{dst}" for src, dst in lifecycle_edges()) if lifecycle_edges else []
        if graph and canonical and graph != sorted(set(canonical)):
            issues.append(
                "WARN config/phase-transitions.yaml stages: exits_to differs from "
                "the canonical phase graph (engines/domain/phase_graph.py)"
            )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="UACP_ROOT")
    ap.add_argument("artifacts", nargs="*", help="Artifacts to validate")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    gov = base_dir(root)  # governed namespace root (.uacp/); CLI artifact args are base-relative
    issues: list[str] = []
    try:
        configs = validate_configs(root, issues)
        validate_transition_config_consistency(configs, issues)
        phase_config = configs["config/phase-transitions.yaml"]
        for raw in args.artifacts:
            path = Path(raw)
            if not path.is_absolute():
                path = gov / path
            obj = require_map(load_yaml(path), path)
            kind = obj.get("kind", "")
            validate_finding_states(path, obj, issues)
            if kind == "uacp.phase_transition":
                validate_phase_transition(path, obj, phase_config, issues, root=root)
            elif kind == "uacp.council_synthesis" or "council_id" in obj:
                validate_council_synthesis(path, obj, phase_config, issues)
            elif kind == "uacp.gate_selection":
                validate_gate_selection(path, obj, issues)
            elif kind == "uacp.triage":
                validate_triage(path, obj, issues)
            elif kind == "uacp.proposal":
                validate_proposal(path, obj, issues)
            elif kind == "uacp.proposal_package_selection":
                validate_proposal_package_selection(path, obj, issues, root=root)
            elif kind == "uacp.plan_package_selection":
                validate_plan_package_selection(path, obj, issues, root=root)
            elif kind == "uacp.execute_task":
                validate_execute_task(path, obj, issues)
            elif kind == "uacp.phase_intent_verification_contract":
                validate_piv_contract(path, obj, issues, root=root)
            elif kind == "uacp.execution_checkpoint":
                validate_execution_checkpoint(path, obj, issues, root=root)
            elif kind == "uacp.piv_assessment":
                validate_piv_assessment(path, obj, issues, root=root)
            elif kind == "uacp.verification_package":
                validate_verify_package_selection(path, obj, issues, root=root)
            elif kind == "uacp.verify_resolve_readiness":
                validate_verify_resolve_readiness(path, obj, issues, root=root)
            elif kind == "uacp.resolve_package":
                validate_resolve_package_selection(path, obj, issues, root=root)
            elif kind == "uacp.resolve_closure":
                validate_resolve_closure(path, obj, issues, root=root)
            elif kind == "uacp.evidence_cluster":
                validate_evidence_cluster(path, obj, issues)
            elif isinstance(kind, str) and kind.startswith("uacp."):
                issues.append(f"BLOCK {path}: unknown UACP artifact kind: {kind}")
    except Exception as exc:
        print(f"BLOCK {exc}")
        return 2

    blocks = [i for i in issues if i.startswith("BLOCK")]
    warns = [i for i in issues if i.startswith("WARN")]
    for issue in issues:
        print(issue)
    if blocks:
        print(f"RESULT BLOCK blocks={len(blocks)} warns={len(warns)}")
        return 2
    if warns:
        print(f"RESULT WARN blocks=0 warns={len(warns)}")
        return 1
    print("RESULT PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
