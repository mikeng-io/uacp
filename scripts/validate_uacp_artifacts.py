#!/usr/bin/env python3
"""Lightweight UACP artifact validator for manual drills.

This is intentionally not a full schema engine. It checks the fields that current
UACP lifecycle/council artifacts rely on so manual drills do not silently drift.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception as exc:  # pragma: no cover
    print(f"BLOCK yaml import failed: {exc}")
    sys.exit(2)

VALID_FINDING_STATES = {"open", "resolved", "accepted_risk", "not_applicable", "deferred"}
VALID_TRANSITION_DECISIONS = {"pass", "warn", "block"}
VALID_COUNCIL_VERDICTS = {"pass", "warn", "concerns", "fail", "pass_with_deferred_items", "pass_with_concerns", "proceed_to_plan_with_conditions", "completed_with_mixed_validity", "PASS", "WARN", "CONCERNS", "FAIL"}
VALID_CLUSTER_STATES = {"pass", "warn", "block", "not_applicable", "deferred"}
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
    schema = config.get("artifact_schema", {})
    required = schema.get("required_fields", [])
    check_required(str(path), obj, required, issues)
    decision = obj.get("decision")
    if decision and decision not in VALID_TRANSITION_DECISIONS:
        issues.append(f"BLOCK {path}: invalid decision {decision!r}")
    terminal = obj.get("terminal_kind")
    values = schema.get("fields", {}).get("terminal_kind", {}).get("values", [])
    if terminal and values and terminal not in values:
        issues.append(f"BLOCK {path}: terminal_kind {terminal!r} not in {values}")
    validate_transition_invariant_summary(path, obj, issues)
    validate_transition_warning_deferred_shape(path, obj, issues)
    validate_handled_findings_chain(path, obj, issues)
    validate_heartgate_coherence(path, obj, issues, root=root)
    validate_heartgate_coherence_requirement(path, obj, config, issues)


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
    schema = config.get("council_synthesis_schema", {})
    required = schema.get("required_fields", [])
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
        candidate = Path(str(artifact_path))
        if not candidate.is_absolute():
            candidate = root / candidate
        try:
            resolved = candidate.resolve()
            if resolved != root and root not in resolved.parents:
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
    required = ["cluster_id", "phase", "family", "purpose", "state", "findings"]
    check_required(str(path), obj, required, issues)
    state = obj.get("state")
    if state and state not in VALID_CLUSTER_STATES:
        issues.append(f"BLOCK {path}: evidence cluster state {state!r} is invalid")

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


def validate_configs(root: Path, issues: list[str]) -> dict:
    configs = {}
    for rel in [
        "config/phase-transitions.yaml",
        "config/review-routing.yaml",
        "config/evidence-clusters.yaml",
        "config/guardian-policy.yaml",
        "config/state.yaml",
    ]:
        path = root / rel
        configs[rel] = require_map(load_yaml(path), path)
    validate_evidence_registry(root, issues)
    return configs


def validate_transition_config_consistency(configs: dict, issues: list[str]) -> None:
    phase_cfg = configs.get("config/phase-transitions.yaml") or {}
    guardian_cfg = configs.get("config/guardian-policy.yaml") or {}
    stages = phase_cfg.get("stages") or {}
    canonical = sorted(
        f"{stage}->{target}"
        for stage, body in stages.items()
        for target in (body.get("exits_to") or [])
    )
    allowed = sorted(
        str(item) for item in ((guardian_cfg.get("heartgate") or {}).get("allowed_transitions") or [])
    )
    if allowed and canonical and allowed != canonical:
        issues.append("WARN config/guardian-policy.yaml: heartgate.allowed_transitions differs from config/phase-transitions.yaml stages")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="UACP_ROOT")
    ap.add_argument("artifacts", nargs="*", help="Artifacts to validate")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    issues: list[str] = []
    try:
        configs = validate_configs(root, issues)
        validate_transition_config_consistency(configs, issues)
        phase_config = configs["config/phase-transitions.yaml"]
        for raw in args.artifacts:
            path = Path(raw)
            if not path.is_absolute():
                path = root / path
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
            elif kind == "uacp.execute_task":
                validate_execute_task(path, obj, issues)
            elif kind == "uacp.evidence_cluster":
                validate_evidence_cluster(path, obj, issues)
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
