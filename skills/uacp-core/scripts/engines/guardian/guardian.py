"""The Guardian write-time gate: classify / contain / evaluate tool events.

Moved out of ``core.py`` (Phase A1, design/graph-engine node 31). The ``Guardian``
classifies a ``GuardianEvent`` against a loaded ``GuardianPolicy`` and returns an
allow / allow_with_audit / require_approval / block ``GuardianDecision`` —
including the path-driven governed-write blocks (D25) and the per-phase
admissibility layer. Typed to the strict-engines bar (node 32 §0).
"""

from __future__ import annotations

import fnmatch
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict, cast

from config import base_dir

from .models import (
    DECISION_ALLOW,
    DECISION_ALLOW_WITH_AUDIT,
    DECISION_BLOCK,
    DECISION_BLOCK_PENDING_HEARTGATE,
    DECISION_REQUIRE_APPROVAL,
    GuardianDecision,
    GuardianEvent,
)
from .policy import GuardianPolicy

# Governed UACP artifact roots — uacp_artifact_write is the ONLY sanctioned writer
# for these (mirrors governed_handlers allowed_roots + the config artifact.uacp
# protected category). A raw write landing under any of them is hard-blocked (D25)
# so a forged manifest edge can't be smuggled in by a native edit.
_UACP_ARTIFACT_ROOTS = (
    "plans",
    "proposals",
    "executions",
    "verification",
    "resolutions",
    "knowledge",
    "lessons",
    "brainstorm",
)

# Categories that do NOT mutate the filesystem. A tool in one of these never
# triggers the governed-path write block even if it carries a governed path (e.g.
# reading a manifest). EVERYTHING ELSE is treated as mutation-capable — so an
# unmapped/unknown tool (external.unknown_mutator, runtime.extension, an MCP tool,
# apply_patch, …) targeting a governed root is hard-blocked by default (default-deny).
# This closes the adversarial-review bypass where the block only fired for a fixed
# 3-category allowlist and let every other mutator through.
_READONLY_CATEGORIES = frozenset(
    {
        "read.local",
        "evidence.containment",
        "lifecycle.transition",
        "external.network_read",
    }
)


class _StageConfig(TypedDict, total=False):
    allowed_tools: list[str]
    forbidden_tools: list[str]


class _PhaseConfig(TypedDict, total=False):
    stages: Mapping[str, _StageConfig]


class Guardian:
    """Evaluate UACP Guardian events against a loaded policy."""

    def __init__(self, policy: GuardianPolicy, *, phase_config: Mapping[str, object] | None = None):
        self.policy = policy
        # Phase 1: per-phase tool admissibility (Layer B). Loaded from
        # config/phase-transitions.yaml `stages.<phase>.allowed_tools` /
        # `forbidden_tools`. If absent, no Layer B restriction.
        self._phase_config: _PhaseConfig = cast(
            "_PhaseConfig", dict(phase_config) if phase_config else {}
        )

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
                    return self._block(
                        category, f"missing UACP context fields: {', '.join(missing)}", evidence
                    )
                return GuardianDecision(
                    DECISION_ALLOW_WITH_AUDIT,
                    "state.uacp",
                    "authorized guarded UACP state mutation tool",
                    evidence,
                    True,
                )
            return self._block(
                "state.uacp", "direct UACP state writes must use uacp_state_write", evidence
            )

        # Direct writes landing under a governed artifact root (plans/, proposals/,
        # executions/, verification/, resolutions/, knowledge/, lessons/, brainstorm/)
        # via a non-uacp_artifact_write tool are a hard block (D25): the governed
        # artifact writer must be the only path that serializes a manifest node, so a
        # forged edge cannot be smuggled in by a native edit. Mirrors the state rule.
        if self._is_direct_uacp_artifact_write(event, category):
            if self.policy.is_allowed_tool_for_category("artifact.uacp", event.tool_name):
                if missing := self._missing_context(event):
                    return self._block(
                        category, f"missing UACP context fields: {', '.join(missing)}", evidence
                    )
                return GuardianDecision(
                    DECISION_ALLOW_WITH_AUDIT,
                    "artifact.uacp",
                    "authorized governed UACP artifact writer",
                    evidence,
                    True,
                )
            return self._block(
                "artifact.uacp",
                "direct UACP artifact writes must use uacp_artifact_write",
                evidence,
            )

        # Generalized allowed-tools branch for any protected category that
        # lists `allowed_tools` (block or allow_with_audit default — see
        # _category_has_governed_tool). pc_5: explicit guard so state.uacp
        # cannot double-fire; that path is handled above.
        if (
            category != "state.uacp"
            and self._category_has_governed_tool(category)
            and self.policy.is_allowed_tool_for_category(category, event.tool_name)
        ):
            if missing := self._missing_context(event):
                return self._block(
                    category, f"missing UACP context fields: {', '.join(missing)}", evidence
                )
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
                return self._block(
                    category, f"missing UACP context fields: {', '.join(missing)}", evidence
                )

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

        default = str(
            self.policy.category_defaults(category).get("default_decision") or DECISION_ALLOW
        )

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
            return GuardianDecision(
                DECISION_ALLOW, category, "policy allows action", evidence, audit
            )
        return GuardianDecision(
            DECISION_ALLOW_WITH_AUDIT, category, "observe mode for non-UACP action", evidence, True
        )

    def classify(self, event: GuardianEvent) -> str:
        provider_map = self.policy.tool_provenance.get("classification_by_provider")
        provider_category = provider_map.get(event.tool_provider) if provider_map else None
        if provider_category == "prefer_tool_classification_else_runtime_extension":
            if event.tool_name in self.policy.tool_classification:
                return str(self.policy.tool_classification[event.tool_name])
            return "runtime.extension"
        # Only a REAL protected category may be returned here. A provider mapping
        # whose value is a symbolic directive (use_tool_classification, …) OR a
        # stray non-category string (e.g. the decision word "block_pending_heartgate",
        # which an earlier config used) must NOT be returned as the category — that
        # leaked an undefined category that defaulted to allow (adversarial review #7).
        # Anything that is not a defined category falls through to tool/pattern/default
        # classification (which resolves an unknown tool to runtime.extension).
        if provider_category and provider_category in self.policy.protected_categories:
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
        missing: list[str] = []
        required: dict[str, object] = {
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
        rule = self.policy.path_rules.get("protected_write_enforcement")
        required_for = rule.get("required_for") if rule else None
        return set(required_for or [])

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
        stages = self._phase_config.get("stages")
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
        stage = stages.get(phase)
        if not isinstance(stage, Mapping):
            return None
        # list(...) is defensive: a malformed scalar-string stage value would
        # otherwise be substring-matched ("state" in "uacp_state_write") instead
        # of list-membership-matched, flipping a block/allow. Coerce to a list of
        # chars (as the pre-typing code did) so a scalar never passes the allowlist.
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
        if category in _READONLY_CATEGORIES:  # reads pass; everything else is mutation-capable
            return False
        return any(self._path_is_under_state(path) for path in self._extract_paths(event))

    def _is_direct_uacp_artifact_write(self, event: GuardianEvent, category: str) -> bool:
        if category == "artifact.uacp":
            return True
        if category in _READONLY_CATEGORIES:  # reads pass; everything else is mutation-capable
            return False
        return any(self._path_is_under_artifact_root(path) for path in self._extract_paths(event))

    def _touches_uacp_root(self, event: GuardianEvent) -> bool:
        return any(self._path_is_under_root(path) for path in self._extract_paths(event))

    def _extract_paths(self, event: GuardianEvent) -> list[str]:
        # `or {}` is defensive: tool_args is typed non-None but an explicit
        # GuardianEvent(tool_args=None) bypasses the dataclass default_factory.
        args: Mapping[str, object] = event.tool_args or {}
        paths: list[str] = []
        context_paths: list[Path] = []
        for key in (
            "path",
            "file_path",
            "target_path",
            "notebook_path",
            "workdir",
            "cwd",
            "workspace",
        ):
            value = args.get(key) or (event.workspace if key == "workspace" else "")
            if isinstance(value, str) and value:
                paths.append(value)
                if key in {"workdir", "cwd", "workspace"}:
                    try:
                        context_paths.append(Path(value).expanduser().resolve())
                    except Exception:
                        pass

        # Defense in depth (adversarial review): a mutating tool can carry its target
        # under ANY arg key (destination/dest/output_path/out/files/...), not just the
        # well-known ones above. Scan every other string / list-of-string arg value as
        # a candidate path; only values that resolve under a governed root actually
        # trigger a block, so non-path args are harmless. The command-text keys are
        # left to the shell scanner below.
        def _path_shaped(s: str) -> bool:
            # Only treat path-LIKE strings as candidate paths, so content args
            # (old_string="a", a YAML body, a reason) are not mistaken for paths and
            # do not falsely bind an edit to the UACP root. A governed-path target
            # always carries a separator (e.g. ".uacp/plans/x.yaml" or an absolute
            # path), so requiring one keeps the alt-key evasion closed.
            return "/" in s or "\\" in s

        for key, value in args.items():
            if key in {
                "path",
                "file_path",
                "target_path",
                "notebook_path",
                "workdir",
                "cwd",
                "workspace",
                "command",
                "code",
                "script",
                "args",
            }:
                continue
            if isinstance(value, str) and _path_shaped(value):
                paths.append(value)
            elif isinstance(value, list):
                paths.extend(
                    v for v in cast("list[object]", value) if isinstance(v, str) and _path_shaped(v)
                )
        root_path = self.policy.uacp_root.resolve()
        root = str(root_path)
        uacp_env = os.getenv("UACP_ROOT") or root
        # Shell/code tools often carry filesystem targets only inside a command
        # string. Treat explicit or context-relative UACP-root references in
        # command text as UACP-bound so protected actions cannot bypass Guardian
        # by omitting direct path metadata.
        for key in ("command", "code", "script", "args"):
            value = args.get(key)
            if isinstance(value, str):
                text = value
            elif isinstance(value, list):
                text = " ".join(str(v) for v in cast("list[object]", value))
            else:
                text = ""
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
            for token in re.split(r"[\s;|&<>]+", compact):
                token = token.strip("\"'")
                if not token or token.startswith("-"):
                    continue
                if token.startswith(
                    (
                        "./",
                        "../",
                        ".uacp/",
                        "state/",
                        "config/",
                        "docs/",
                        "proposals/",
                        "plans/",
                        "executions/",
                        "verification/",
                        "resolutions/",
                        "knowledge/",
                        "uacp/",
                    )
                ):
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

    def _path_is_under_artifact_root(self, raw_path: str) -> bool:
        try:
            path = self._resolve_path(raw_path)
            base = base_dir(self.policy.uacp_root)
            for root in _UACP_ARTIFACT_ROOTS:
                artifact_root = (base / root).resolve()
                if path == artifact_root or artifact_root in path.parents:
                    return True
            return False
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
