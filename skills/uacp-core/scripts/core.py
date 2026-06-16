"""Runtime-neutral UACP core.

Imported by runtime adapters. Contains no framework-specific imports.
"""

from __future__ import annotations

import fnmatch
import json
import importlib.util
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from config import base_dir, get_config

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
        # Slice 3: the Guardian policy is sourced from the collapsed
        # config/uacp.toml `[guardian]` table via config.py (repo-default
        # deep-merged with `<root>/.uacp/config.toml`), NOT from the legacy
        # config/guardian-policy.yaml. `__init__`/`validate`/`evaluate` are
        # unchanged: the `[guardian]` dict has the same key shape the
        # structure-driven `__init__` already consumes. The UACP_GUARDIAN_MODE
        # env override still applies (resolved inside `__init__`), and the
        # anti-bypass invariant in `validate()` still runs against this policy.
        root = resolve_uacp_root(uacp_root)
        try:
            raw = get_config(root).model_dump().get("guardian", {})
        except Exception as exc:
            raise GuardianPolicyError(f"Guardian policy failed to load: {exc}") from exc
        if not isinstance(raw, dict) or not raw:
            raise GuardianPolicyError(
                f"Guardian policy missing or invalid: config/uacp.toml [guardian] for root {root}"
            )
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
            if value is None or value == "":
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
        # Global review SKEP-G-001: reject unknown phase values. Previously
        # `stages.get(phase) or {}` returned an empty stage for any unknown
        # phase string, silently collapsing Layer B to a no-op. Any protected
        # tool call with `uacp_phase: "execute_v2"` (or any typo) bypassed
        # per-phase admissibility. Now: if stages is populated AND phase is
        # not in the declared stage set, the call is blocked. When stages is
        # empty (no phase config loaded, e.g. Phase 0 tests that exercise
        # Layer A only), this check skips so Layer A still applies.
        if stages and phase not in stages:
            return self._block(
                category,
                f"unknown uacp_phase value '{phase}' (not in declared stages)",
                evidence + [f"phase={phase}", "phase_layer=unknown_phase"],
            )
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
        context_paths: list[Path] = []
        for key in ("path", "file_path", "target_path", "workdir", "cwd", "workspace"):
            value = args.get(key) or (event.workspace if key == "workspace" else "")
            if isinstance(value, str) and value:
                paths.append(value)
                if key in {"workdir", "cwd", "workspace"}:
                    try:
                        context_paths.append(Path(value).expanduser().resolve())
                    except Exception:
                        pass
        root_path = self.policy.uacp_root.resolve()
        root = str(root_path)
        uacp_env = os.getenv("UACP_ROOT") or root
        # Shell/code tools often carry filesystem targets only inside a command
        # string. Treat explicit or context-relative UACP-root references in
        # command text as UACP-bound so protected actions cannot bypass Guardian
        # by omitting direct path metadata.
        for key in ("command", "code", "script", "args"):
            value = args.get(key)
            text = value if isinstance(value, str) else " ".join(str(v) for v in value) if isinstance(value, list) else ""
            if not text:
                continue
            expanded = (
                text.replace("$HOME", str(Path.home()))
                .replace("${HOME}", str(Path.home()))
                .replace("$UACP_ROOT", uacp_env)
                .replace("${UACP_ROOT}", uacp_env)
            )
            compact = expanded.replace("\\ ", " ")
            if (
                root in compact
                or ".hermes/uacp" in compact
                or "~/.hermes/uacp" in compact
                or (".hermes" in compact and "uacp" in compact)
            ):
                paths.append(root)
                continue
            # Conservative context-relative binding for common shell path forms.
            # This is not a full shell parser; it intentionally catches obvious
            # relative UACP writes such as `touch state/x` from workspace=UACP_ROOT
            # or `touch uacp/state/x` from cwd=$HERMES_HOME.
            for token in __import__("re").split(r"[\s;|&<>]+", compact):
                token = token.strip('"\'')
                if not token or token.startswith("-"):
                    continue
                if token.startswith(("./", "../", ".uacp/", "state/", "config/", "docs/", "proposals/", "plans/", "executions/", "verification/", "resolutions/", "knowledge/", "uacp/")):
                    for base in context_paths or [root_path]:
                        try:
                            candidate = (base / token).resolve()
                            if candidate == root_path or root_path in candidate.parents:
                                paths.append(str(candidate))
                        except Exception:
                            continue
        return paths

    def _path_is_under_state(self, raw_path: str) -> bool:
        try:
            path = self._resolve_path(raw_path)
            state_root = (base_dir(self.policy.uacp_root) / "state").resolve()
            return path == state_root or state_root in path.parents
        except Exception:
            return False

    def _path_is_under_root(self, raw_path: str) -> bool:
        try:
            path = self._resolve_path(raw_path)
            root = self.policy.uacp_root.resolve()
            return path == root or root in path.parents
        except Exception:
            return False

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
        self._validate_adaptive_proposal_package_gate(artifact, blockers)
        self._validate_adaptive_plan_package_gate(artifact, blockers)
        self._validate_adaptive_execute_evidence_gate(artifact, blockers)
        self._validate_adaptive_verify_evidence_gate(artifact, blockers)
        self._validate_adaptive_resolve_closure_gate(artifact, blockers)
        self._validate_piv_record(artifact, blockers)
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
        if yaml is None:
            blockers.append(f"{label} requires PyYAML")
            return None
        try:
            candidate = Path(rel_path)
            if candidate.is_absolute():
                resolved = candidate.resolve()
            else:
                resolved = (self.governed_root / candidate).resolve()
            root = self.governed_root.resolve()
            if resolved != root and root not in resolved.parents:
                blockers.append(f"{label}: artifact path escapes UACP root: {rel_path}")
                return None
            if not resolved.exists() or not resolved.is_file():
                blockers.append(f"{label}: artifact not found: {rel_path}")
                return None
            data = yaml.safe_load(resolved.read_text(encoding="utf-8"))
        except Exception as exc:
            blockers.append(f"{label}: failed to parse {rel_path}: {exc}")
            return None
        if not isinstance(data, Mapping):
            blockers.append(f"{label}: {rel_path} must be a YAML mapping")
            return None
        return data

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

    def _validate_adaptive_verify_evidence_gate(self, artifact: Mapping[str, Any], blockers: list[str]) -> None:
        if str(artifact.get("from_phase") or "") != "verify" or str(artifact.get("to_phase") or "") != "resolve":
            return
        # F-T3-01 (SECURITY): fail CLOSED — see _validate_adaptive_execute_evidence_gate.
        # An absent or non-mapping adaptive_verify_evidence_gate key must not disable enforcement.
        run_id = str(artifact.get("run_id") or "")
        if not run_id:
            blockers.append("adaptive_verify_evidence_gate requires run_id")
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

    def _piv_rule(self) -> Mapping[str, Any]:
        """Resolve the piv_rule.

        Slice 4b T4c-2: the rule grammar (ledger_required, the piv_* check ids,
        ledger_required_fields, max_attempts, second_failure_action) is codified
        in engines.domain.gate_rules. The block is read from the loaded
        phase-transitions config WHEN PRESENT (production behavior, unchanged);
        when ABSENT it falls back to the code default whose ``ledger_required``
        is True (enforce-by-default / fail-closed: a PIV pass record is required
        on every transition). No operator-tunable knob this wave.

        A test fixture may opt OUT by supplying ``piv_rule: {ledger_required:
        false}``: present-with-falsy-ledger_required is read as the loaded value,
        so the reader's ``not piv_rule.get("ledger_required")`` short-circuits the
        gate exactly as the pre-T4c-2 absent block did.
        """
        if "piv_rule" in self.config:
            return self.config.get("piv_rule") or {}
        from engines.domain.gate_rules import piv_rule_default

        return piv_rule_default()

    def _validate_piv_record(self, artifact: Mapping[str, Any], blockers: list[str]) -> None:
        """Phase 1 / Item 1.4: require a PIV pass record in the ledger before
        Heartgate accepts a transition for which piv_rule applies.

        Tech-F1 remediation: sanitize run_id before constructing the ledger
        path (reject path-traversal characters and resolve under
        state/gate-ledger/ only). Skeptic F5 remediation: tolerate malformed
        piv_rule fields with explicit blockers instead of crashing.

        Global review R1 (SKEP-G-002): generalize the per-check pass
        evidence pattern Phase 3 R1 introduced for PLAN_VALIDATION.
        piv_rule declares `ledger_required_fields: [piv_attempt, result,
        checks]`; when present, the kernel verifies each declared
        piv_check_id appears in the ledger record's `checks` list AND
        has explicit per-check pass evidence (mapping-form or sibling
        `check_results: {piv_id: pass}`).
        """
        piv_rule = self._piv_rule()
        if not isinstance(piv_rule, Mapping) or not piv_rule.get("ledger_required"):
            return
        run_id = str(artifact.get("run_id") or "")
        if not run_id:
            blockers.append("piv_rule requires run_id to verify ledger record")
            return
        if not _is_safe_run_id(run_id):
            blockers.append("piv_rule: unsafe run_id rejected for ledger lookup")
            return
        ledger_path = self.governed_root / "state" / "gate-ledger" / f"{run_id}.jsonl"
        if not ledger_path.exists():
            blockers.append(f"piv_rule unmet: no gate ledger at {ledger_path.relative_to(self.governed_root)}")
            return
        from_phase = str(artifact.get("from_phase") or "")
        # Precompute declared piv_ids when piv_rule.checks is present.
        declared_check_ids: set[str] = set()
        for c in (piv_rule.get("checks") or []):
            if isinstance(c, Mapping):
                cid = str(c.get("id") or "").strip()
                if cid:
                    declared_check_ids.add(cid)
        ledger_required_fields = [str(f) for f in (piv_rule.get("ledger_required_fields") or []) if isinstance(f, str)]
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
                    blockers.append(f"piv_rule: gate ledger line {lineno} unparseable: {type(exc).__name__}: {exc}")
                    return
                if str(rec.get("gate") or "") != "PIV":
                    continue
                if from_phase and str(rec.get("phase") or "") != from_phase:
                    continue
                try:
                    attempt = int(rec.get("piv_attempt") or 0)
                except (TypeError, ValueError):
                    blockers.append(f"piv_rule: gate ledger line {lineno} has non-integer piv_attempt")
                    return
                result = str(rec.get("result") or "")
                if result == "pass":
                    # SKEP-G-002: when piv_rule declares checks + required fields,
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
                                defect = f"line {lineno}: missing required piv_ids {sorted(missing_ids)}"
                            elif extra_ids:
                                defect = f"line {lineno}: unknown piv_ids {sorted(extra_ids)}"
                            elif unproven:
                                defect = f"line {lineno}: missing per-check pass evidence for {sorted(unproven)}"
                    if defect:
                        passing_record_defects.append(defect)
                        continue
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
            detail = f" (per-record defects: {passing_record_defects})" if passing_record_defects else ""
            blockers.append(f"piv_rule unmet: no PIV pass record in ledger for phase '{from_phase}'{detail}")

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
        # Required-field policy for the ledger record (mirrors piv_rule.ledger_required_fields).
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
