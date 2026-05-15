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
        # self_attesting_tools (Phase 1 / pc_1) — moved out of adapter code.
        # Tools whose handlers perform their own path-bounded containment.
        sat = self.data.get("self_attesting_tools") or {}
        if isinstance(sat, dict):
            names = sat.get("names") or []
        elif isinstance(sat, list):
            names = sat
        else:
            names = []
        self.self_attesting_tools = frozenset(str(n) for n in names if isinstance(n, str))
        # Enforcement mode is read from policy `mode` field with optional
        # UACP_GUARDIAN_MODE env override.  `enforce` is the default; `observe`
        # downgrades policy-default blocks on UACP-bound actions to
        # allow_with_audit (non-waivable invariants — missing context, missing
        # containment, wrong tool for state.uacp — still block).
        env_mode = os.getenv("UACP_GUARDIAN_MODE", "").strip().lower()
        self.mode = (env_mode or str(self.data.get("mode") or "enforce")).lower()
        if self.mode not in {"enforce", "observe"}:
            self.mode = "enforce"

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
            "block_pending_heartgate",
        }
        for provider, category in provider_map.items():
            if category in symbolic:
                continue
            if category not in self.protected_categories:
                raise GuardianPolicyError(
                    f"tool_provenance provider {provider} targets undefined category {category}"
                )
        # Phase 1 remediation (skeptic F2): every self_attesting_tools name
        # must be in tool_classification AND target a governed category.
        # Rejects "terminal", "execute_code", unknown names, and any name
        # classified into a non-governed category. Prevents containment
        # bypass via policy edit.
        governed_categories = {
            "state.uacp", "docs.uacp", "config.uacp", "artifact.uacp",
            "evidence.containment", "exec.shell.contained", "lifecycle.transition",
        }
        for tool_name in self.self_attesting_tools:
            if tool_name not in self.tool_classification:
                raise GuardianPolicyError(
                    f"self_attesting_tools entry '{tool_name}' is not in tool_classification"
                )
            cat = self.tool_classification[tool_name]
            if cat not in governed_categories:
                raise GuardianPolicyError(
                    f"self_attesting_tools entry '{tool_name}' targets non-governed category '{cat}'"
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

    def __init__(self, policy: GuardianPolicy, *, phase_config: Mapping[str, Any] | None = None):
        self.policy = policy
        # Phase 1: per-phase tool admissibility (Layer B). Loaded from
        # config/phase-transitions.yaml `stages.<phase>.allowed_tools` /
        # `forbidden_tools`. If absent, no Layer B restriction.
        self._phase_config = dict(phase_config or {})

    def evaluate(self, event: GuardianEvent) -> GuardianDecision:
        # pc_4: empty tool_name is a non-waivable block in all modes.
        if not (event.tool_name or "").strip():
            return self._block(
                "external.unknown_mutator",
                "empty tool_name is not admissible",
                [f"tool_provider={event.tool_provider}", "tool_name=<empty>"],
            )

        category = self.classify(event)
        audit = category != "read.local"
        evidence = [f"tool_provider={event.tool_provider}", f"tool_name={event.tool_name}"]

        # Phase 1 Layer B: per-phase admissibility (uses uacp_phase from the
        # event). Forbidden tools always block; allowed-tools lists are an
        # allowlist if present. Phases without configured lists impose no
        # Layer B restriction (backward-compatible).
        phase_decision = self._phase_layer_check(event, category, evidence)
        if phase_decision is not None:
            return phase_decision

        # Direct writes that land under state/ via a non-state.uacp tool path
        # remain a hard block — they bypass the governed state writer.
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

        # Generalized allowed-tools branch for any protected category that
        # lists `allowed_tools` (block or allow_with_audit default — see
        # _category_has_governed_tool). pc_5: explicit guard so state.uacp
        # cannot double-fire; that path is handled above.
        if category != "state.uacp" and self._category_has_governed_tool(category) and self.policy.is_allowed_tool_for_category(category, event.tool_name):
            if missing := self._missing_context(event):
                return self._block(category, f"missing UACP context fields: {', '.join(missing)}", evidence)
            return GuardianDecision(
                DECISION_ALLOW_WITH_AUDIT,
                category,
                f"authorized governed tool for {category}",
                evidence,
                True,
            )

        uacp_bound = self.is_uacp_bound(event)
        protected = self._is_protected(category)

        if uacp_bound and protected:
            if missing := self._missing_context(event):
                return self._block(category, f"missing UACP context fields: {', '.join(missing)}", evidence)

        if uacp_bound and category in self._requires_filesystem_containment_categories():
            if not event.filesystem_guard_verified:
                # Write containment is a non-waivable invariant per the
                # constitution: observe mode MUST NOT downgrade this block.
                # Only policy-default blocks below are mode-sensitive.
                return self._block(
                    category,
                    "protected filesystem containment is unavailable for UACP-bound execution",
                    evidence + ["containment=missing", f"mode={self.policy.mode}"],
                )

        default = str(self.policy.category_defaults(category).get("default_decision") or DECISION_ALLOW)

        if uacp_bound and default in {DECISION_BLOCK, DECISION_BLOCK_PENDING_HEARTGATE}:
            if self.policy.mode == "observe":
                # Observe mode logs but does not block policy-default blocks.
                # Non-waivable blocks (missing context, missing containment,
                # wrong tool for state.uacp) already returned earlier and are
                # unaffected by this downgrade.
                return GuardianDecision(
                    DECISION_ALLOW_WITH_AUDIT,
                    category,
                    f"observe mode downgrade of policy default {default}",
                    evidence + [f"mode={self.policy.mode}", f"original_default={default}"],
                    True,
                )
            return GuardianDecision(
                default,
                category,
                "policy default blocks UACP-bound action",
                evidence + [f"mode={self.policy.mode}"],
                True,
            )

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
        # Mode is consulted via self.policy.mode in evaluate(); UACP binding is
        # purely a function of context presence and UACP_ROOT path touch.  The
        # previous duplicated `UACP_GUARDIAN_MODE` env branch here was dead — it
        # was a strict subset of the next branch and added a second, drift-prone
        # source of truth for mode.
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

    def _category_has_governed_tool(self, category: str) -> bool:
        """True when the category is meant to be entered through a governed
        writer surface (it lists `allowed_tools` and its default decision is
        either `block` — the canonical writer pattern — or `allow_with_audit`
        — the read-only governed surfaces, e.g. evidence.containment,
        lifecycle.transition; the allowed-tools branch produces a consistent
        audit-log reason string for these too (pc_6)).
        """
        defaults = self.policy.category_defaults(category)
        default = str(defaults.get("default_decision") or "")
        if default not in {DECISION_BLOCK, DECISION_ALLOW_WITH_AUDIT}:
            return False
        return bool(defaults.get("allowed_tools"))

    def _phase_layer_check(
        self,
        event: GuardianEvent,
        category: str,
        evidence: list[str],
    ) -> GuardianDecision | None:
        """Per-phase tool admissibility (Layer B).

        Returns a decision when Layer B has something to say (forbidden_tools
        match or allowed_tools allowlist miss), otherwise None to fall through
        to Layer A (category-level evaluation).
        """
        phase = (event.uacp_phase or os.getenv("UACP_PHASE") or "").strip()
        if not phase:
            return None
        stages = self._phase_config.get("stages") or {}
        if not isinstance(stages, Mapping):
            # Skeptic F5 remediation: malformed stages config does not crash
            # — Layer B is skipped, Layer A still applies, audit logs the issue.
            return None
        stage = stages.get(phase) or {}
        if not isinstance(stage, Mapping):
            return None
        forbidden = list(stage.get("forbidden_tools") or [])
        allowed = list(stage.get("allowed_tools") or [])
        if event.tool_name in forbidden:
            return self._block(
                category,
                f"tool '{event.tool_name}' is forbidden in phase '{phase}'",
                evidence + [f"phase={phase}", "phase_layer=forbidden"],
            )
        if allowed and event.tool_name not in allowed and self._is_protected(category):
            # Layer B allowlist only restricts protected categories; reads pass.
            return self._block(
                category,
                f"tool '{event.tool_name}' is not in phase '{phase}' allowed_tools",
                evidence + [f"phase={phase}", "phase_layer=allowlist_miss"],
            )
        return None

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
            path = self.policy.uacp_root / path
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


def _load_artifact_schemas(uacp_root: Path) -> dict[str, Any]:
    """Load config/artifact-schemas.yaml (Phase 2). Returns empty dict on
    missing / malformed so legacy transitions keep working."""
    if yaml is None:
        return {}
    path = uacp_root / "config" / "artifact-schemas.yaml"
    if not path.exists():
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
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
        self.stages = self.config.get("stages") or {}
        schema = self.config.get("artifact_schema") or {}
        self.required_fields = list(schema.get("required_fields") or [])
        # Phase 2: artifact schemas (scope, intent, evidence_disposition, lessons)
        self.artifact_schemas = _load_artifact_schemas(self.uacp_root)

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

        self._validate_heartgate_coherence(artifact, blockers, warnings)
        self._validate_heartgate_coherence_requirement(artifact, blockers)
        self._validate_phase_exit_invariants(artifact, blockers)
        self._validate_piv_record(artifact, blockers)
        # Phase 2: per-transition artifact-structure checks.
        self._validate_intent_doc(artifact, blockers)
        self._validate_scope_artifact(artifact, blockers, warnings)
        self._validate_evidence_dispositions(artifact, blockers)
        self._validate_lessons_artifact(artifact, blockers)

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

    def _validate_heartgate_coherence(self, artifact: Mapping[str, Any], blockers: list[str], warnings: list[str]) -> None:
        """Validate optional Heartgate transition-coherence evidence."""
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
                path = self.uacp_root / path
            resolved = path.resolve()
            root = self.uacp_root.resolve()
            if resolved != root and root not in resolved.parents:
                return False
            return resolved.exists()
        except Exception:
            return False


    def _validate_heartgate_coherence_requirement(self, artifact: Mapping[str, Any], blockers: list[str]) -> None:
        rule = self.config.get("heartgate_coherence_required_when") or {}
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
        and check each: required artifact_glob entries must match at least one
        file under UACP_ROOT; required gate_ledger_entry values must appear in
        state/gate-ledger/{run_id}.jsonl.
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

    def _validate_piv_record(self, artifact: Mapping[str, Any], blockers: list[str]) -> None:
        """Phase 1 / Item 1.4: require a PIV pass record in the ledger before
        Heartgate accepts a transition for which piv_rule applies.

        Tech-F1 remediation: sanitize run_id before constructing the ledger
        path (reject path-traversal characters and resolve under
        state/gate-ledger/ only). Skeptic F5 remediation: tolerate malformed
        piv_rule fields with explicit blockers instead of crashing.
        """
        piv_rule = self.config.get("piv_rule") or {}
        if not isinstance(piv_rule, Mapping) or not piv_rule.get("ledger_required"):
            return
        run_id = str(artifact.get("run_id") or "")
        if not run_id:
            blockers.append("piv_rule requires run_id to verify ledger record")
            return
        if not _is_safe_run_id(run_id):
            blockers.append(f"piv_rule: unsafe run_id rejected for ledger lookup")
            return
        ledger_path = self.uacp_root / "state" / "gate-ledger" / f"{run_id}.jsonl"
        if not ledger_path.exists():
            blockers.append(f"piv_rule unmet: no gate ledger at {ledger_path.relative_to(self.uacp_root)}")
            return
        from_phase = str(artifact.get("from_phase") or "")
        passing_attempts: list[int] = []
        failing_attempts: list[int] = []
        try:
            for line in ledger_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if str(rec.get("gate") or "") != "PIV":
                    continue
                if from_phase and str(rec.get("phase") or "") != from_phase:
                    continue
                attempt = int(rec.get("piv_attempt") or 0)
                result = str(rec.get("result") or "")
                if result == "pass":
                    passing_attempts.append(attempt)
                elif result in {"warn", "block", "fail"}:
                    failing_attempts.append(attempt)
        except Exception as exc:
            blockers.append(f"piv_rule ledger read failed: {type(exc).__name__}: {exc}")
            return
        raw_max = piv_rule.get("max_attempts")
        if raw_max is None:
            raw_max = 2
        try:
            max_attempts = int(raw_max)
        except (TypeError, ValueError):
            blockers.append("piv_rule.max_attempts must be a positive integer")
            return
        if max_attempts <= 0:
            blockers.append("piv_rule.max_attempts must be >= 1")
            return
        # Skeptic F2 remediation: second-failure block is the default action.
        # Only an explicit known relaxation value bypasses it.
        action = str(piv_rule.get("second_failure_action") or "block_unconditional")
        if action not in {"block_unconditional", "warn"}:
            blockers.append(f"piv_rule.second_failure_action unknown value '{action}'")
            return
        if len(failing_attempts) >= max_attempts and action == "block_unconditional":
            blockers.append(
                f"piv_rule: {len(failing_attempts)} failed PIV attempts for phase '{from_phase}' — second-failure unconditional block"
            )
            return
        if not passing_attempts:
            blockers.append(f"piv_rule unmet: no PIV pass record in ledger for phase '{from_phase}'")

    def _glob_matches_any(self, pattern: str) -> bool:
        """Phase 1 remediation (skeptic F3): reject symlinks and out-of-root
        matches. A glob match must resolve to a real file under UACP_ROOT and
        not be a symlink whose target is outside the root.
        """
        import glob as _glob
        try:
            root = self.uacp_root.resolve()
            matches = _glob.glob(str(self.uacp_root / pattern), recursive=True)
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
        ledger_path = self.uacp_root / "state" / "gate-ledger" / f"{run_id}.jsonl"
        if not ledger_path.exists():
            return False
        try:
            for line in ledger_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
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
        path = self.uacp_root / template.replace("{run_id}", run_id)
        if not path.exists():
            blockers.append(f"intent doc missing: {path.relative_to(self.uacp_root)}")
            return
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            blockers.append(f"intent doc unreadable: {type(exc).__name__}")
            return
        required_sections = list(schema.get("required_sections") or [])
        for section in required_sections:
            if f"## {section}" not in text and f"# {section}" not in text:
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
        path = self.uacp_root / template.replace("{run_id}", run_id)
        if not path.exists():
            blockers.append(f"scope artifact missing: {path.relative_to(self.uacp_root)}")
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
        execute_stage = (self.stages.get("execute") or {})
        allowed_tools = list((execute_stage or {}).get("allowed_tools") or [])
        tool_path_capabilities = self._tool_path_capabilities()
        for wp in write_paths:
            wp_str = str(wp)
            reachable = False
            for tool in allowed_tools:
                prefixes = tool_path_capabilities.get(tool) or []
                if any(wp_str.startswith(pfx) or wp_str == pfx.rstrip("/") for pfx in prefixes):
                    reachable = True
                    break
            if not reachable:
                blockers.append(
                    f"scope.write_paths cross-check: '{wp_str}' is not reachable by any execute-phase allowed_tool"
                )

    def _tool_path_capabilities(self) -> dict[str, list[str]]:
        """Path prefixes each governed writer tool can reach.

        Phase 2 remediation (F2): the canonical source is now
        `config/artifact-schemas.yaml#cross_checks.scope_write_paths_vs_layer_b.tool_path_capabilities`.
        Loaded from `self.artifact_schemas`. Shell/exec surfaces are
        deliberately absent — they target the workspace, not UACP_ROOT,
        and do not satisfy UACP-rooted scope.write_paths (F1).

        Fail-closed default: if the config section is missing or malformed,
        return an empty mapping so every write_path is unreachable.
        """
        cross = (self.artifact_schemas.get("cross_checks") or {})
        block = (cross.get("scope_write_paths_vs_layer_b") or {})
        caps = block.get("tool_path_capabilities") or {}
        if not isinstance(caps, Mapping):
            return {}
        result: dict[str, list[str]] = {}
        for tool, prefixes in caps.items():
            if not isinstance(tool, str):
                continue
            if isinstance(prefixes, list):
                result[tool] = [str(p) for p in prefixes if isinstance(p, str)]
            elif isinstance(prefixes, str):
                result[tool] = [prefixes]
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
                p = self.uacp_root / rel
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
            assumptions_path = self.uacp_root / assumptions_rel
            if assumptions_path.exists():
                try:
                    text = assumptions_path.read_text(encoding="utf-8")
                    self._check_pending_assumptions(text, cluster_id, blockers)
                except Exception:
                    pass

    def _check_pending_assumptions(self, text: str, cluster_id: str, blockers: list[str]) -> None:
        """Parse a simple markdown table looking for `pending` rows with empty
        owner or empty next_phase_obligation. The expected table shape is:
            | Assumption | Disposition | Owner | Next-phase obligation |
        """
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line.startswith("|") or "Disposition" in line or "---" in line:
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 4:
                continue
            disposition = cells[1].lower()
            owner = cells[2]
            next_obl = cells[3]
            if disposition == "pending" and (not owner or not next_obl):
                blockers.append(
                    f"evidence_disposition: cluster '{cluster_id}' has unowned 'pending' assumption: {cells[0][:60]}"
                )

    def _validate_lessons_artifact(self, artifact: Mapping[str, Any], blockers: list[str]) -> None:
        """Phase 2.4: VERIFY->RESOLVE requires outputs/{run_id}-lessons.yaml
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
        template = str(schema.get("path_template") or "outputs/{run_id}-lessons.yaml")
        path = self.uacp_root / template.replace("{run_id}", run_id)
        if not path.exists():
            blockers.append(f"lessons artifact missing: {path.relative_to(self.uacp_root)}")
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
