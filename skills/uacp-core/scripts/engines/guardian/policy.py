"""Guardian policy: load + validate the ``[guardian]`` config table.

Moved out of ``core.py`` (Phase A1, design/graph-engine node 31). ``load()``
resolves the UACP root via the ``engines.domain.paths`` leaf and reads the
collapsed ``config/uacp.toml`` ``[guardian]`` table through ``config.get_config``.

Typed to the strict-engines bar (node 32 §0): the loosely-structured ``[guardian]``
table is modelled by the ``_GuardianTable`` TypedDict and cast once at the
boundary, so field access is precisely typed rather than ``Any``.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict, cast

from config import get_config
from engines.domain.paths import resolve_uacp_root

from .models import GuardianPolicyError


class _CategoryDefaults(TypedDict, total=False):
    allowed_tools: list[str]
    default_decision: str


class _ToolProvenance(TypedDict, total=False):
    classification_by_provider: Mapping[str, str]


class _ProtectedWriteEnforcement(TypedDict, total=False):
    required_for: list[str]


class _PathRules(TypedDict, total=False):
    protected_write_enforcement: _ProtectedWriteEnforcement


class _SelfAttestingTools(TypedDict, total=False):
    # `object`, not `str`: the config is loosely structured, so the values are
    # filtered through isinstance(str) at read time rather than trusted.
    names: list[object]


class _GuardianTable(TypedDict, total=False):
    """The shape of the ``[guardian]`` config table (the bits this policy reads)."""

    schema_version: object
    mode: object
    protected_categories: Mapping[str, _CategoryDefaults]
    tool_classification: Mapping[str, str]
    tool_pattern_classification: Mapping[str, str]
    tool_provenance: _ToolProvenance
    path_rules: _PathRules
    runtime_modes: Mapping[str, object]
    self_attesting_tools: _SelfAttestingTools | list[object]


class GuardianPolicy:
    def __init__(self, data: Mapping[str, object], *, uacp_root: Path):
        table = cast("_GuardianTable", dict(data))
        self.data: _GuardianTable = table
        self.uacp_root = uacp_root.resolve()
        self.version = str(table.get("schema_version") or "")
        protected = table.get("protected_categories")
        self.protected_categories: set[str] = set(protected) if protected else set()
        tool_cls = table.get("tool_classification")
        self.tool_classification: dict[str, str] = dict(tool_cls) if tool_cls else {}
        pattern_cls = table.get("tool_pattern_classification")
        self.tool_pattern_classification: dict[str, str] = dict(pattern_cls) if pattern_cls else {}
        # Copy (not alias) — consistent with the dict()-copied siblings above and
        # the pre-typing behavior, so policy fields never share mutable state with
        # the (cached) source config blob.
        provenance = table.get("tool_provenance")
        self.tool_provenance: _ToolProvenance = (
            cast("_ToolProvenance", dict(provenance)) if provenance else {}
        )
        path_rules = table.get("path_rules")
        self.path_rules: _PathRules = cast("_PathRules", dict(path_rules)) if path_rules else {}
        runtime_modes = table.get("runtime_modes")
        self.runtime_modes: dict[str, object] = dict(runtime_modes) if runtime_modes else {}
        # self_attesting_tools (Phase 1 / pc_1) — moved out of adapter code.
        # Tools whose handlers perform their own path-bounded containment. May be a
        # {names: [...]} mapping or a bare list (or absent).
        sat = table.get("self_attesting_tools")
        if isinstance(sat, Mapping):
            names: list[object] = sat.get("names") or []
        elif isinstance(sat, list):
            names = sat
        else:
            names = []
        self.self_attesting_tools = frozenset(n for n in names if isinstance(n, str))
        # Enforcement mode is read from policy `mode` field with optional
        # UACP_GUARDIAN_MODE env override.  `enforce` is the default; `observe`
        # downgrades policy-default blocks on UACP-bound actions to
        # allow_with_audit (non-waivable invariants — missing context, missing
        # containment, wrong tool for state.uacp — still block).
        env_mode = os.getenv("UACP_GUARDIAN_MODE", "").strip().lower()
        self.mode = (env_mode or str(table.get("mode") or "enforce")).lower()
        if self.mode not in {"enforce", "observe"}:
            self.mode = "enforce"

    @classmethod
    def load(cls, uacp_root: str | Path | None = None) -> GuardianPolicy:
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
            raw: object = get_config(root).model_dump().get("guardian", {})
        except Exception as exc:
            raise GuardianPolicyError(f"Guardian policy failed to load: {exc}") from exc
        if not isinstance(raw, dict) or not raw:
            raise GuardianPolicyError(
                f"Guardian policy missing or invalid: config/uacp.toml [guardian] for root {root}"
            )
        policy = cls(cast("Mapping[str, object]", raw), uacp_root=root)
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
        provider_map = self.tool_provenance.get("classification_by_provider")
        symbolic = {
            "use_tool_classification",
            "require_explicit_classification",
            "require_control_plane_guard",
            "prefer_tool_classification_else_runtime_extension",
            "block_pending_heartgate",
        }
        if provider_map:
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
            "state.uacp",
            "docs.uacp",
            "config.uacp",
            "artifact.uacp",
            "evidence.containment",
            "exec.shell.contained",
            "lifecycle.transition",
        }
        for tool_name in self.self_attesting_tools:
            if tool_name not in self.tool_classification:
                raise GuardianPolicyError(
                    f"self_attesting_tools entry '{tool_name}' is not in tool_classification"
                )
            cat = self.tool_classification[tool_name]
            if cat not in governed_categories:
                raise GuardianPolicyError(
                    f"self_attesting_tools entry '{tool_name}' targets "
                    f"non-governed category '{cat}'"
                )

    def category_defaults(self, category: str) -> _CategoryDefaults:
        protected = self.data.get("protected_categories")
        if not protected:
            return {}
        value = protected.get(category)
        # Defensive: normalize a malformed non-dict category value to {} (the
        # config table is cast, not validated, so the runtime value may not match
        # _CategoryDefaults). Mirrors the pre-typing behavior.
        return value if isinstance(value, dict) else {}

    def is_allowed_tool_for_category(self, category: str, tool_name: str) -> bool:
        # `or []` is defensive: a malformed falsy non-list allowed_tools (0/False/"")
        # must degrade to "not allowed", not crash `in` with a TypeError.
        return tool_name in (self.category_defaults(category).get("allowed_tools") or [])
