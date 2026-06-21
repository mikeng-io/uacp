"""Guardian policy: load + validate the ``[guardian]`` config table.

Moved verbatim out of ``core.py`` (Phase A1 of the core decomposition,
design/graph-engine node 31). ``load()`` resolves the UACP root via the
``engines.domain.paths`` leaf and reads the collapsed ``config/uacp.toml``
``[guardian]`` table through ``config.get_config``.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from config import get_config
from engines.domain.paths import resolve_uacp_root

from .models import GuardianPolicyError


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

    def category_defaults(self, category: str) -> Mapping[str, Any]:
        protected = self.data.get("protected_categories") or {}
        value = protected.get(category) or {}
        return value if isinstance(value, dict) else {}

    def is_allowed_tool_for_category(self, category: str, tool_name: str) -> bool:
        allowed = self.category_defaults(category).get("allowed_tools") or []
        return tool_name in allowed
