"""Runtime-neutral UACP Guardian policy core.

The Hermes plugin adapter translates runtime hook payloads into
``GuardianEvent``.  This module keeps the policy decisions deterministic and
free of plugin framework assumptions.
"""

from __future__ import annotations

import fnmatch
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

try:
    import yaml
except ImportError:  # pragma: no cover - Hermes ships with PyYAML in normal use.
    yaml = None  # type: ignore[assignment]


DECISION_ALLOW = "allow"
DECISION_ALLOW_WITH_AUDIT = "allow_with_audit"
DECISION_REQUIRE_APPROVAL = "require_approval"
DECISION_BLOCK = "block"
DECISION_BLOCK_PENDING_HEARTGATE = "block_pending_heartgate"


@dataclass(frozen=True)
class GuardianEvent:
    runtime: str
    adapter: str
    event_type: str
    tool_provider: str
    tool_name: str
    tool_args: Mapping[str, Any] = field(default_factory=dict)
    task_id: str = ""
    session_id: str = ""
    tool_call_id: str = ""
    workspace: str = ""
    uacp_run_id: str = ""
    uacp_phase: str = ""
    policy_version: str = ""
    declared_authority: str = ""
    declared_side_effects: Any = None
    kanban_task_id: str = ""
    kanban_run_id: str = ""
    filesystem_guard_verified: bool = False


@dataclass(frozen=True)
class GuardianDecision:
    decision: str
    category: str
    reason: str
    evidence: list[str] = field(default_factory=list)
    audit_required: bool = False

    @property
    def blocks_execution(self) -> bool:
        return self.decision in {DECISION_BLOCK, DECISION_BLOCK_PENDING_HEARTGATE}

    def to_hook_result(self) -> dict[str, str]:
        return {
            "action": "block",
            "message": f"UACP Guardian blocked {self.category}: {self.reason}",
        }

    def to_audit_record(self, event: GuardianEvent, *, audit_artifact: str = "") -> dict[str, Any]:
        return {
            "ts": int(time.time()),
            "policy_version": event.policy_version,
            "uacp_run_id": event.uacp_run_id,
            "uacp_phase": event.uacp_phase,
            "runtime": event.runtime,
            "adapter": event.adapter,
            "tool_provider": event.tool_provider,
            "tool_name": event.tool_name,
            "category": self.category,
            "decision": self.decision,
            "reason": self.reason,
            "workspace": event.workspace,
            "authority_artifact": event.declared_authority,
            "side_effects": event.declared_side_effects,
            "audit_artifact": audit_artifact,
            "runtime_commit": os.getenv("HERMES_RUNTIME_COMMIT", ""),
            "uacp_commit": os.getenv("UACP_COMMIT", ""),
            "evidence": list(self.evidence),
        }


class GuardianPolicyError(RuntimeError):
    pass


class HeartgateError(RuntimeError):
    pass


@dataclass(frozen=True)
class HeartgateDecision:
    decision: str
    reason: str
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def blocks_transition(self) -> bool:
        return self.decision == "block"


class GuardianPolicy:
    def __init__(self, data: Mapping[str, Any], *, uacp_root: Path):
        self.data = dict(data)
        self.uacp_root = uacp_root.resolve()
        self.version = str(self.data.get("schema_version") or "")
        self.protected_categories = set((self.data.get("protected_categories") or {}).keys())
        self.tool_classification = dict(self.data.get("tool_classification") or {})
        self.tool_pattern_classification = dict(self.data.get("tool_pattern_classification") or {})
        self.tool_provenance = dict(self.data.get("tool_provenance") or {})
        self.path_rules = dict(self.data.get("path_rules") or {})
        self.runtime_modes = dict(self.data.get("runtime_modes") or {})

    @classmethod
    def load(cls, uacp_root: str | Path | None = None) -> "GuardianPolicy":
        root = resolve_uacp_root(uacp_root)
        policy_path = root / "config" / "guardian-policy.yaml"
        if yaml is None:
            raise GuardianPolicyError("PyYAML is required to load Guardian policy")
        try:
            raw = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise GuardianPolicyError(f"Guardian policy not found: {policy_path}") from exc
        except Exception as exc:
            raise GuardianPolicyError(f"Guardian policy failed to load: {exc}") from exc
        if not isinstance(raw, dict):
            raise GuardianPolicyError(f"Guardian policy must be a YAML mapping: {policy_path}")
        policy = cls(raw, uacp_root=root)
        policy.validate()
        return policy

    def validate(self) -> None:
        if not self.version:
            raise GuardianPolicyError("Guardian policy missing schema_version")
        if not self.protected_categories:
            raise GuardianPolicyError("Guardian policy missing protected_categories")
        for section_name, mapping in (
            ("tool_classification", self.tool_classification),
            ("tool_pattern_classification", self.tool_pattern_classification),
        ):
            for tool_name, category in mapping.items():
                if category not in self.protected_categories:
                    raise GuardianPolicyError(
                        f"{section_name}.{tool_name} targets undefined category {category}"
                    )
        provider_map = self.tool_provenance.get("classification_by_provider") or {}
        symbolic = {
            "use_tool_classification",
            "require_explicit_classification",
            "require_control_plane_guard",
            "prefer_tool_classification_else_runtime_extension",
        }
        for provider, category in provider_map.items():
            if category in symbolic:
                continue
            if category not in self.protected_categories:
                raise GuardianPolicyError(
                    f"tool_provenance provider {provider} targets undefined category {category}"
                )

    def category_defaults(self, category: str) -> Mapping[str, Any]:
        protected = self.data.get("protected_categories") or {}
        value = protected.get(category) or {}
        return value if isinstance(value, dict) else {}

    def is_allowed_tool_for_category(self, category: str, tool_name: str) -> bool:
        allowed = self.category_defaults(category).get("allowed_tools") or []
        return tool_name in allowed


def resolve_uacp_root(uacp_root: str | Path | None = None) -> Path:
    if uacp_root:
        return Path(uacp_root).expanduser().resolve()
    if os.getenv("UACP_ROOT"):
        return Path(os.environ["UACP_ROOT"]).expanduser().resolve()
    if os.getenv("HERMES_HOME"):
        return (Path(os.environ["HERMES_HOME"]).expanduser() / "uacp").resolve()
    return (Path.home() / ".hermes" / "uacp").resolve()


def infer_tool_provider(tool_name: str, explicit_provider: str = "") -> str:
    """Infer a broad provider category without importing a host runtime.

    Runtime adapters may pass a precise ``explicit_provider`` after consulting
    their own tool registries. The neutral kernel intentionally avoids importing
    Hermes modules so it can be reused by non-Hermes adapters.
    """
    if tool_name.startswith("mcp_"):
        return "mcp"
    if explicit_provider and explicit_provider != "core":
        return explicit_provider
    return "core"


class Guardian:
    """Evaluate UACP Guardian events against a loaded policy."""

    def __init__(self, policy: GuardianPolicy):
        self.policy = policy

    def evaluate(self, event: GuardianEvent) -> GuardianDecision:
        category = self.classify(event)
        audit = category != "read.local"
        evidence = [f"tool_provider={event.tool_provider}", f"tool_name={event.tool_name}"]

        if self._is_direct_uacp_state_write(event, category):
            if self.policy.is_allowed_tool_for_category("state.uacp", event.tool_name):
                if missing := self._missing_context(event):
                    return self._block(category, f"missing UACP context fields: {', '.join(missing)}", evidence)
                return GuardianDecision(
                    DECISION_ALLOW_WITH_AUDIT,
                    "state.uacp",
                    "authorized guarded UACP state mutation tool",
                    evidence,
                    True,
                )
            return self._block("state.uacp", "direct UACP state writes must use uacp_state_write", evidence)

        uacp_bound = self.is_uacp_bound(event)
        protected = self._is_protected(category)

        if uacp_bound and protected:
            if missing := self._missing_context(event):
                return self._block(category, f"missing UACP context fields: {', '.join(missing)}", evidence)

        if uacp_bound and category in self._requires_filesystem_containment_categories():
            if not event.filesystem_guard_verified:
                return self._block(
                    category,
                    "protected filesystem containment is unavailable for UACP-bound execution",
                    evidence + ["containment=missing"],
                )

        default = str(self.policy.category_defaults(category).get("default_decision") or DECISION_ALLOW)

        if uacp_bound and default in {DECISION_BLOCK, DECISION_BLOCK_PENDING_HEARTGATE}:
            return GuardianDecision(default, category, "policy default blocks UACP-bound action", evidence, True)

        if uacp_bound and default == DECISION_REQUIRE_APPROVAL:
            return GuardianDecision(
                DECISION_ALLOW_WITH_AUDIT,
                category,
                "required approval represented by declared authority",
                evidence,
                True,
            )

        if not uacp_bound and protected and self._touches_uacp_root(event):
            return self._block(category, "protected UACP path requires UACP context", evidence)

        if default == DECISION_ALLOW:
            return GuardianDecision(DECISION_ALLOW, category, "policy allows action", evidence, audit)
        return GuardianDecision(DECISION_ALLOW_WITH_AUDIT, category, "observe mode for non-UACP action", evidence, True)

    def classify(self, event: GuardianEvent) -> str:
        provider_map = self.policy.tool_provenance.get("classification_by_provider") or {}
        provider_category = provider_map.get(event.tool_provider)
        if provider_category == "prefer_tool_classification_else_runtime_extension":
            if event.tool_name in self.policy.tool_classification:
                return str(self.policy.tool_classification[event.tool_name])
            return "runtime.extension"
        if provider_category and provider_category not in {
            "use_tool_classification",
            "require_explicit_classification",
            "require_control_plane_guard",
        }:
            return provider_category

        if event.tool_name in self.policy.tool_classification:
            return str(self.policy.tool_classification[event.tool_name])

        for pattern, category in self.policy.tool_pattern_classification.items():
            if fnmatch.fnmatch(event.tool_name, pattern):
                return str(category)

        if event.tool_provider in {"plugin", "mcp", "unknown"}:
            return "runtime.extension"
        return "external.unknown_mutator"

    def is_uacp_bound(self, event: GuardianEvent) -> bool:
        if os.getenv("UACP_GUARDIAN_MODE", "").lower() == "enforce":
            return True
        if event.uacp_run_id or event.uacp_phase:
            return True
        if os.getenv("UACP_RUN_ID") or os.getenv("UACP_PHASE"):
            return True
        if str(event.tool_args.get("uacp_run_id") or ""):
            return True
        if self._touches_uacp_root(event):
            return True
        return False

    def _is_protected(self, category: str) -> bool:
        return category not in {"read.local", "external.network_read"}

    def _block(self, category: str, reason: str, evidence: list[str]) -> GuardianDecision:
        return GuardianDecision(DECISION_BLOCK, category, reason, evidence, True)

    def _missing_context(self, event: GuardianEvent) -> list[str]:
        missing = []
        required = {
            "workspace": event.workspace,
            "uacp_run_id": event.uacp_run_id,
            "uacp_phase": event.uacp_phase,
            "policy_version": event.policy_version,
            "declared_authority": event.declared_authority,
            "declared_side_effects": event.declared_side_effects,
        }
        for key, value in required.items():
            if value is None or value == "" or value == []:
                missing.append(key)
        return missing

    def _requires_filesystem_containment_categories(self) -> set[str]:
        rule = self.policy.path_rules.get("protected_write_enforcement") or {}
        required_for = rule.get("required_for") or []
        return set(required_for)

    def _is_direct_uacp_state_write(self, event: GuardianEvent, category: str) -> bool:
        if category == "state.uacp":
            return True
        if category not in {"file.write", "exec.shell", "exec.code_with_tool_proxy"}:
            return False
        return any(self._path_is_under_state(path) for path in self._extract_paths(event))

    def _touches_uacp_root(self, event: GuardianEvent) -> bool:
        return any(self._path_is_under_root(path) for path in self._extract_paths(event))

    def _extract_paths(self, event: GuardianEvent) -> list[str]:
        args = event.tool_args or {}
        paths: list[str] = []
        for key in ("path", "file_path", "target_path", "workdir", "cwd"):
            value = args.get(key)
            if isinstance(value, str) and value:
                paths.append(value)
        return paths

    def _path_is_under_state(self, raw_path: str) -> bool:
        try:
            path = self._resolve_path(raw_path)
            state_root = (self.policy.uacp_root / "state").resolve()
            return path == state_root or state_root in path.parents
        except Exception:
            return True

    def _path_is_under_root(self, raw_path: str) -> bool:
        try:
            path = self._resolve_path(raw_path)
            root = self.policy.uacp_root
            return path == root or root in path.parents
        except Exception:
            return True

    def _resolve_path(self, raw_path: str) -> Path:
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        return path.resolve()


def make_event(
    *,
    tool_name: str,
    args: Mapping[str, Any] | None = None,
    event_type: str = "pre_tool_call",
    tool_provider: str = "",
    task_id: str = "",
    session_id: str = "",
    tool_call_id: str = "",
    filesystem_guard_verified: bool = False,
) -> GuardianEvent:
    tool_args = dict(args or {})
    provider = infer_tool_provider(tool_name, tool_provider)
    return GuardianEvent(
        runtime="hermes",
        adapter="uacp_guardian",
        event_type=event_type,
        tool_provider=provider,
        tool_name=tool_name,
        tool_args=tool_args,
        task_id=task_id,
        session_id=session_id,
        tool_call_id=tool_call_id,
        workspace=str(tool_args.get("workspace") or os.getenv("UACP_WORKSPACE") or os.getcwd()),
        uacp_run_id=str(tool_args.get("uacp_run_id") or os.getenv("UACP_RUN_ID") or ""),
        uacp_phase=str(tool_args.get("uacp_phase") or os.getenv("UACP_PHASE") or ""),
        policy_version=str(tool_args.get("policy_version") or os.getenv("UACP_GUARDIAN_POLICY_VERSION") or ""),
        declared_authority=str(
            tool_args.get("declared_authority")
            or tool_args.get("authority_artifact")
            or os.getenv("UACP_DECLARED_AUTHORITY")
            or ""
        ),
        declared_side_effects=(
            tool_args.get("declared_side_effects")
            if "declared_side_effects" in tool_args
            else os.getenv("UACP_DECLARED_SIDE_EFFECTS", "")
        ),
        kanban_task_id=str(tool_args.get("kanban_task_id") or os.getenv("HERMES_KANBAN_TASK") or ""),
        kanban_run_id=str(tool_args.get("kanban_run_id") or os.getenv("HERMES_KANBAN_RUN_ID") or ""),
        filesystem_guard_verified=filesystem_guard_verified,
    )


def write_audit_record(record: Mapping[str, Any], *, log_root: str | Path | None = None) -> Path:
    default_root = Path(os.getenv("HERMES_HOME") or Path.home() / ".hermes") / "logs" / "uacp"
    root = Path(log_root) if log_root else Path(os.getenv("HERMES_UACP_LOG_ROOT") or default_root)
    root = root.expanduser()
    root.mkdir(parents=True, exist_ok=True)
    path = root / "guardian.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n")
    return path


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return bool(value)


class Heartgate:
    """Validate UACP lifecycle transition artifacts.

    Heartgate validates the adaptive evidence selected for a specific run; it
    does not define a fixed gate checklist.
    """

    def __init__(self, config: Mapping[str, Any], *, uacp_root: str | Path | None = None):
        self.config = dict(config)
        self.uacp_root = resolve_uacp_root(uacp_root)
        self.stages = self.config.get("stages") or {}
        schema = self.config.get("artifact_schema") or {}
        self.required_fields = list(schema.get("required_fields") or [])

    @classmethod
    def load(cls, uacp_root: str | Path | None = None) -> "Heartgate":
        root = resolve_uacp_root(uacp_root)
        path = root / "config" / "phase-transitions.yaml"
        if yaml is None:
            raise HeartgateError("PyYAML is required to load Heartgate config")
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise HeartgateError(f"Heartgate config not found: {path}") from exc
        except Exception as exc:
            raise HeartgateError(f"Heartgate config failed to load: {exc}") from exc
        if not isinstance(raw, dict):
            raise HeartgateError(f"Heartgate config must be a YAML mapping: {path}")
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

        accepted = self._accepted_exception_paths(artifact)
        for cluster in artifact.get("cluster_summary") or []:
            cluster_id = str((cluster or {}).get("cluster_id") or "unknown")
            state = str((cluster or {}).get("state") or "")
            artifact_path = str((cluster or {}).get("artifact_path") or "")
            if state == "block":
                blockers.append(f"cluster {cluster_id} blocks transition")
            elif state == "warn":
                if artifact_path and artifact_path in accepted:
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
            raw_path = self.uacp_root / raw_path
        if yaml is None:
            raise HeartgateError("PyYAML is required to load transition artifact")
        artifact = yaml.safe_load(raw_path.read_text(encoding="utf-8"))
        if not isinstance(artifact, dict):
            return HeartgateDecision("block", "transition artifact must be a YAML mapping", ["invalid artifact"])
        return self.validate_transition(artifact)

    def _transition_allowed(self, from_phase: str, to_phase: str) -> bool:
        stage = self.stages.get(from_phase) or {}
        exits = stage.get("exits_to") or []
        return to_phase in exits

    def _accepted_exception_paths(self, artifact: Mapping[str, Any]) -> set[str]:
        paths = set()
        for item in artifact.get("accepted_exceptions") or []:
            if isinstance(item, Mapping) and item.get("artifact_path") and item.get("owner") and item.get("rationale"):
                paths.add(str(item["artifact_path"]))
        return paths

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
        return bool(item.get("owner") and item.get("condition") and item.get("accepted_by"))

    def _warnings_owned(self, warnings: Any) -> bool:
        for item in warnings:
            if not isinstance(item, Mapping):
                return False
            if not (item.get("owner") and item.get("residual_risk")):
                return False
        return True
