"""Codified Heartgate gate-rule grammar (Slice 4b T4c-1).

Previously sourced from ``config/phase-transitions.yaml`` by YAML parse and read
via ``self.config.get(<block>)`` in ``core.py``. The *structural grammar* of three
gate rules is now declared here as typed, importable defaults:

  * ``heartgate_coherence_required_when`` — when a transition must carry a
    ``heartgate_coherence`` field, and which lenses that field must cover.
  * ``run_registry_rule`` — the PLAN->EXECUTE write-path overlap rule grammar
    (registry path, guarded transition, governed writer tool).
  * Pattern-A adaptive gate ``required_universal_core`` lists for the
    ``adaptive_proposal_package_gate`` and ``adaptive_plan_package_gate``.

The Heartgate readers in ``core.py`` now use ``loaded_config.get(<block>)`` WHEN
PRESENT, else the code default exposed here. So:

  * production (block present in YAML) = unchanged behavior;
  * block absent (slimmed from production YAML, or omitted by a test fixture) =
    code default applies (enforce-by-default / fail-closed).

The operator-tunable knobs (coherence threshold + the phase/routing/domain
selectors, and the run_registry ``enforcement`` mode) live in
``config/uacp.toml [heartgate.coherence]`` / ``[heartgate.run_registry]`` and are
read via ``config.get_config(root)`` — they are NOT duplicated here. This module
holds only the *structural* grammar (required fields, required lenses, the
registry/writer wiring) that is not operator-tunable.

PURE layer: module-level constants and small builders only, ZERO filesystem I/O.

Public API:
    HEARTGATE_COHERENCE_REQUIRED_FIELD     — the artifact field the rule demands
    HEARTGATE_COHERENCE_REQUIRED_LENSES    — lenses that field must cover
    HEARTGATE_COHERENCE_SELECTORS_DEFAULT  — code-default phases/routing/domains
    HEARTGATE_COHERENCE_MIN_GRANULARITY_DEFAULT — code-default threshold
    heartgate_coherence_required_when_default() — full rule dict (grammar+selectors)
    run_registry_rule_default()           — full run_registry_rule grammar dict
    PROPOSAL_REQUIRED_UNIVERSAL_CORE       — proposal gate universal-core keys
    PLAN_REQUIRED_UNIVERSAL_CORE           — plan gate universal-core keys
    PROPOSAL_NOT_APPLICABLE_REQUIRED_FIELDS — proposal NA-rationale fields
    PLAN_NOT_APPLICABLE_REQUIRED_FIELDS     — plan NA-rationale fields
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# A. heartgate_coherence_required_when
# ---------------------------------------------------------------------------
# Structural grammar (NOT operator-tunable): which artifact field carries the
# coherence evidence, and which lenses it must cover. Pinned to the values that
# were in config/phase-transitions.yaml before the T4c-1 slim.
HEARTGATE_COHERENCE_REQUIRED_FIELD: str = "heartgate_coherence"

HEARTGATE_COHERENCE_REQUIRED_LENSES: list[str] = [
    "doctrine_coherence",
    "cross_artifact_consistency",
    "runtime_state_alignment",
    "warning_and_deferred_item_honesty",
    "authority_plane_integrity",
    "next_phase_readiness",
]

# Operator-tunable selection policy — code DEFAULT only. Production reads these
# from config/uacp.toml [heartgate.coherence]; this default is the fail-closed
# fallback that pins the pre-slim production YAML values. The reader prefers the
# uacp.toml values (when present) over this default.
HEARTGATE_COHERENCE_MIN_GRANULARITY_DEFAULT: int = 7

HEARTGATE_COHERENCE_SELECTORS_DEFAULT: dict[str, list[str]] = {
    "phases": ["execute", "verify"],
    "routing_outcomes": ["full_governance"],
    "domains": [
        "runtime",
        "governance",
        "guardian",
        "heartgate",
        "kanban",
        "agent_council",
        "uacp",
    ],
}

# Documentation-only purpose string (matches the pre-slim YAML).
HEARTGATE_COHERENCE_PURPOSE: str = (
    "Require transition-boundary Heartgate coherence evidence for material "
    "runtime/governance transitions while keeping low-risk transitions lightweight."
)


def heartgate_coherence_required_when_default(
    *,
    min_composite_granularity: int | None = None,
    selectors: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Reconstruct the full ``heartgate_coherence_required_when`` rule dict.

    Composes the code-default structural grammar (required field + lenses) with
    the operator-tunable threshold/selectors. When ``min_composite_granularity``
    / ``selectors`` are supplied (e.g. from ``config/uacp.toml [heartgate.coherence]``)
    they win; otherwise the pinned pre-slim production defaults apply.

    The returned dict has the same shape ``_validate_heartgate_coherence_requirement``
    consumed from the YAML block, so the reader needs no shape change.
    """
    sel = dict(HEARTGATE_COHERENCE_SELECTORS_DEFAULT)
    if isinstance(selectors, dict):
        for key in ("phases", "routing_outcomes", "domains"):
            value = selectors.get(key)
            if isinstance(value, list):
                sel[key] = [str(item) for item in value]
    threshold = (
        int(min_composite_granularity)
        if min_composite_granularity is not None
        else HEARTGATE_COHERENCE_MIN_GRANULARITY_DEFAULT
    )
    return {
        "purpose": HEARTGATE_COHERENCE_PURPOSE,
        "min_composite_granularity": threshold,
        "phases": list(sel["phases"]),
        "routing_outcomes": list(sel["routing_outcomes"]),
        "domains": list(sel["domains"]),
        "required_field": HEARTGATE_COHERENCE_REQUIRED_FIELD,
        "required_lenses": list(HEARTGATE_COHERENCE_REQUIRED_LENSES),
    }


# ---------------------------------------------------------------------------
# B. run_registry_rule
# ---------------------------------------------------------------------------
# Structural grammar (NOT operator-tunable here): the registry path, the guarded
# transition, and the governed writer tool. The ``enforcement`` MODE is
# operator-tunable and read from config/uacp.toml [heartgate.run_registry]; this
# default pins the pre-slim production string for equivalence and as the
# fail-closed fallback.
RUN_REGISTRY_REGISTRY_PATH: str = "state/run-registry.yaml"
RUN_REGISTRY_REQUIRED_FOR_TRANSITION: str = "plan->execute"
RUN_REGISTRY_WRITER_TOOL: str = "uacp_run_registry_update"
RUN_REGISTRY_EXCLUSIVE_MUTATOR_ADVISORY: str = "uacp-state skill"
RUN_REGISTRY_ENFORCEMENT_DEFAULT: str = (
    "heartgate blocker on overlap with another active_run's write_paths"
)
RUN_REGISTRY_DESCRIPTION: str = (
    "Phase 3 Item 3.2: write-path overlap detection across concurrent runs. "
    "Heartgate consults state/run-registry.yaml at PLAN->EXECUTE; if another "
    "active run declares an overlapping write_paths entry, this transition "
    "blocks (enforce) or warns (observe)."
)


def run_registry_rule_default(*, enforcement: str | None = None) -> dict[str, Any]:
    """Reconstruct the full ``run_registry_rule`` dict.

    Composes the code-default structural grammar with the operator-tunable
    ``enforcement`` string (from ``config/uacp.toml [heartgate.run_registry]``
    when present, else the pinned pre-slim production value). Shape matches what
    ``_validate_run_registry_overlap`` consumed from the YAML block.
    """
    enforcement_value = (
        str(enforcement) if enforcement is not None else RUN_REGISTRY_ENFORCEMENT_DEFAULT
    )
    return {
        "description": RUN_REGISTRY_DESCRIPTION,
        "registry_path": RUN_REGISTRY_REGISTRY_PATH,
        "enforcement": enforcement_value,
        "required_for_transition": RUN_REGISTRY_REQUIRED_FOR_TRANSITION,
        "writer_tool": RUN_REGISTRY_WRITER_TOOL,
        "exclusive_mutator_advisory": RUN_REGISTRY_EXCLUSIVE_MUTATOR_ADVISORY,
    }


# ---------------------------------------------------------------------------
# C. Pattern-A adaptive gate grammar — consumed sub-fields only
# ---------------------------------------------------------------------------
# These were already hardcoded as `... or [<list>]` fallbacks in the two gate
# readers in core.py. Codified here so the gate reads
# ``gate.get("required_universal_core") or CODE_DEFAULT``; the default pins the
# pre-slim production YAML values for BOTH gates. The unconsumed doctrine
# (description/selected_when_any/block_when/required_artifacts/...) STAYS in the
# YAML — only these consumed sub-fields are codified.
PROPOSAL_REQUIRED_UNIVERSAL_CORE: list[str] = [
    "intent",
    "authority",
    "scope",
    "containment",
    "risk",
    "verification",
    "transition",
    "artifact_map",
]

PLAN_REQUIRED_UNIVERSAL_CORE: list[str] = [
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

# not_applicable_required_fields — the NA-rationale fields the package gates
# demand. These were ALREADY hardcoded in _validate_package_na / _validate_plan_na
# (they were never actually read from the YAML block); codified here so the YAML
# sub-field can be slimmed and the single source of truth is this module.
PROPOSAL_NOT_APPLICABLE_REQUIRED_FIELDS: list[str] = [
    "reason",
    "accepted_by",
    "owner",
    "residual_risk",
    "revisit_phase",
]

PLAN_NOT_APPLICABLE_REQUIRED_FIELDS: list[str] = [
    "reason",
    "accepted_by",
    "owner",
    "residual_risk",
    "revisit_phase",
    "revisit_trigger",
]
