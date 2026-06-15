"""Codified ``stages.<phase>`` grammar (Slice 4b T4d-1).

Previously sourced from ``config/phase-transitions.yaml`` ``stages.<phase>`` by
YAML parse, then consumed three ways:

  * Heartgate ``_transition_allowed``     — ``stages.<phase>.exits_to``
  * Heartgate ``_validate_phase_exit_invariants`` — ``stages.<phase>.phase_exit_invariants``
  * Heartgate ``_validate_scope_artifact`` — ``stages.execute.allowed_tools``
  * Guardian Layer-B ``_phase_layer_check`` — ``stages.<phase>.allowed_tools`` / ``forbidden_tools``
  * Evidence-completeness engine ``_stage_invariants`` — ``stages.<phase>.phase_exit_invariants``

The *grammar* of those stages is now declared here as a typed, importable
code-default. ``stages_default()`` is injected by the single I/O seam
``engines.io.load_phase_transitions`` WHEN the loaded ``config/phase-transitions.yaml``
omits a ``stages`` block (production, after the T4d-1 slim). When a loaded config
DOES provide ``stages`` (e.g. the test fixture in ``tests/conftest.py``), that
block wholesale-overrides this default — exactly as a loaded gate-rule block
overrides the T4c code defaults.

Because every runtime consumer reads ``stages`` via ``load_phase_transitions``
(Heartgate.load, the Hermes adapter ``_phase_config``, and the evidence engine),
injecting the default at the loader gives ALL paths the code default with one
seam and removes the Guardian Layer-B fail-open that slimming would otherwise
introduce (empty ``stages`` collapses Layer-B's allowlist + unknown-phase block
to a no-op).

SINGLE SOURCE OF TRUTH FOR THE GRAPH: ``exits_to`` is NOT hardcoded here. It is
DERIVED from ``phase_graph.LIFECYCLE_GRAPH`` so the codified stages cannot drift
from the canonical lifecycle graph. The agreement test
(``tests/unit/uacp_core/test_phase_graph.py``) pins ``stages_default()`` exits_to
== ``phase_graph.lifecycle_edges()``.

PURE layer: module-level constants and a small builder only, ZERO filesystem I/O.

Public API:
    STAGE_ALLOWED_TOOLS          — per-phase allowed_tools (pinned pre-slim)
    STAGE_FORBIDDEN_TOOLS        — per-phase forbidden_tools (pinned pre-slim)
    STAGE_PHASE_EXIT_INVARIANTS  — per-phase phase_exit_invariants (pinned pre-slim)
    STAGE_PURPOSE                — per-phase doc-only purpose strings (pinned pre-slim)
    STAGE_ENTERS_FROM            — per-phase doc-only enters_from (pinned pre-slim)
    TRIAGE_ROUTING_OUTCOMES      — triage doc-only routing_outcomes map (pinned pre-slim)
    TRIAGE_CAN_TERMINATE         — triage doc-only early-exit flag (pinned pre-slim)
    stages_default()             — full ``stages`` mapping (exits_to derived from phase_graph)
"""

from __future__ import annotations

from typing import Any

from .phase_graph import LIFECYCLE_GRAPH

# ---------------------------------------------------------------------------
# Consumed grammar (drives kernel/Guardian behavior). Pinned to the values that
# were in config/phase-transitions.yaml stages.<phase> before the T4d-1 slim.
# ---------------------------------------------------------------------------

# allowed_tools — consumed by Guardian Layer-B (all phases) and Heartgate
# _validate_scope_artifact (execute only).
STAGE_ALLOWED_TOOLS: dict[str, list[str]] = {
    "triage": [
        "uacp_artifact_write",
        "uacp_state_write",
        "uacp_run_registry_update",
        "uacp_escalation_event",
        "uacp_gate_ledger_append",
        "uacp_heartgate_check",
        "uacp_doc_write",
        "uacp_config_write",
    ],
    "propose": [
        "uacp_artifact_write",
        "uacp_state_write",
        "uacp_run_registry_update",
        "uacp_escalation_event",
        "uacp_gate_ledger_append",
        "uacp_heartgate_check",
        "uacp_doc_write",
    ],
    "plan": [
        "uacp_artifact_write",
        "uacp_state_write",
        "uacp_run_registry_update",
        "uacp_escalation_event",
        "uacp_gate_ledger_append",
        "uacp_heartgate_check",
    ],
    "execute": [
        "uacp_doc_write",
        "uacp_config_write",
        "uacp_state_write",
        "uacp_run_registry_update",
        "uacp_escalation_event",
        "uacp_artifact_write",
        "uacp_gate_ledger_append",
        "uacp_contained_shell",
        "uacp_sandbox_check",
        "uacp_heartgate_check",
        "terminal",
        "execute_code",
    ],
    "verify": [
        "uacp_artifact_write",
        "uacp_state_write",
        "uacp_run_registry_update",
        "uacp_escalation_event",
        "uacp_gate_ledger_append",
        "uacp_heartgate_check",
        "uacp_sandbox_check",
        "uacp_contained_shell",
    ],
    "resolve": [
        "uacp_artifact_write",
        "uacp_state_write",
        "uacp_run_registry_update",
        "uacp_escalation_event",
        "uacp_gate_ledger_append",
        "uacp_heartgate_check",
    ],
}

# forbidden_tools — consumed by Guardian Layer-B (all phases). Note: execute has
# an explicit EMPTY list in the pre-slim YAML (terminal/execute_code are allowed
# there), so it must remain present-and-empty, not absent.
STAGE_FORBIDDEN_TOOLS: dict[str, list[str]] = {
    "triage": ["terminal", "execute_code"],
    "propose": ["terminal", "execute_code"],
    "plan": ["terminal", "execute_code"],
    "execute": [],
    "verify": ["terminal", "execute_code"],
    "resolve": ["terminal", "execute_code"],
}

# phase_exit_invariants — consumed by Heartgate _validate_phase_exit_invariants
# and the evidence-completeness engine. Each entry preserves EVERY sub-field
# that was in the pre-slim YAML (artifact_glob/package_directory/gate_ledger_entry,
# required, applies_when, description) so behavior and observability are unchanged.
STAGE_PHASE_EXIT_INVARIANTS: dict[str, list[dict[str, Any]]] = {
    "triage": [
        {"artifact_glob": "proposals/{run_id}-triage*.yaml", "required": True},
        {"gate_ledger_entry": "TRIAGE_COMPLETE", "required": True},
    ],
    "propose": [
        {"artifact_glob": "proposals/{run_id}*.yaml", "required": True},
        {"artifact_glob": "proposals/{run_id}*-gate-selection.yaml", "required": False},
        {
            "artifact_glob": "proposals/{run_id}*-package-selection.yaml",
            "required": False,
            "applies_when": "adaptive_proposal_package_selected",
            "description": (
                "Machine bridge for adaptive proposal documentation selection; "
                "required for selected medium/high consequence work before "
                "PROPOSE->PLAN."
            ),
        },
        {
            "package_directory": "proposals/{run_id}/",
            "required": False,
            "applies_when": "adaptive_proposal_package_selected",
            "description": (
                "Human-reviewable proposal package; YAML proposal artifacts are "
                "lifecycle envelopes, not the complete proposal."
            ),
        },
        {"gate_ledger_entry": "TRIAGE->PROPOSE", "required": True},
    ],
    "plan": [
        {"artifact_glob": "plans/{run_id}*", "required": True},
        {"gate_ledger_entry": "PROPOSE->PLAN", "required": True},
    ],
    "execute": [
        {"artifact_glob": "executions/{run_id}*", "required": True},
        {"gate_ledger_entry": "PLAN->EXECUTE", "required": True},
    ],
    "verify": [
        {"artifact_glob": "verification/{run_id}*", "required": True},
        {"gate_ledger_entry": "EXECUTE->VERIFY", "required": True},
    ],
    "resolve": [
        {"artifact_glob": "resolutions/{run_id}*", "required": True},
        {"gate_ledger_entry": "VERIFY->RESOLVE", "required": True},
    ],
}

# ---------------------------------------------------------------------------
# Documentation-only grammar (NOT consumed by any kernel/Guardian reader; see the
# verify-first grep in the T4d-1 plan). Preserved verbatim so the reconstructed
# stages block is byte-faithful to the pre-slim YAML and the production-equivalence
# pin can assert field-by-field. These do not drive behavior.
# ---------------------------------------------------------------------------
STAGE_PURPOSE: dict[str, str] = {
    "triage": "Calibrate scope, score granularity, and route the request.",
    "propose": "Establish authority, scope, context, risk, and proposal viability.",
    "plan": "Convert approved proposal into bounded execution and verification strategy.",
    "execute": (
        "Perform bounded work through UACP-authorized Agent Council orchestration, "
        "Hermes Kanban coordination, delegated workers, selected runtimes, and "
        "approved tool/evidence adapters."
    ),
    "verify": "Validate completed work with context-selected evidence clusters.",
    "resolve": "Finalize outputs, archive artifacts, and emit lessons.",
}

STAGE_ENTERS_FROM: dict[str, list[str]] = {
    "triage": ["none"],
    "propose": ["triage"],
    "plan": ["propose"],
    "execute": ["plan"],
    "verify": ["execute"],
    "resolve": ["verify"],
}

# triage-only doc-only sub-fields.
TRIAGE_ROUTING_OUTCOMES: dict[str, str] = {
    "direct": "terminal_direct",
    "lightweight": "propose",
    "standard_uacp": "propose",
    "full_governance": "propose",
    "block_or_clarify": "terminal_blocked",
}
TRIAGE_CAN_TERMINATE: bool = True

# Stable phase ordering for the reconstructed mapping (matches pre-slim YAML).
_PHASE_ORDER: tuple[str, ...] = ("triage", "propose", "plan", "execute", "verify", "resolve")


def _exits_to(phase: str) -> list[str]:
    """exits_to for ``phase``, DERIVED from the canonical lifecycle graph.

    Sorted for determinism (LIFECYCLE_GRAPH values are sets). The only multi-edge
    phase is ``triage`` (-> propose, terminal); sorting yields a stable order.
    """
    return sorted(LIFECYCLE_GRAPH.get(phase, set()))


def stages_default() -> dict[str, dict[str, Any]]:
    """Reconstruct the full ``stages`` mapping as the code default.

    ``exits_to`` is DERIVED from ``phase_graph.LIFECYCLE_GRAPH`` (single source of
    truth for the graph); every other sub-field is the pinned pre-slim value. The
    returned mapping has the same shape every ``stages`` consumer read from the
    YAML block, so no reader needs a shape change.

    Returns fresh objects on each call (no shared mutable state) so a consumer
    cannot mutate the module-level defaults.
    """
    stages: dict[str, dict[str, Any]] = {}
    for phase in _PHASE_ORDER:
        body: dict[str, Any] = {
            "enters_from": list(STAGE_ENTERS_FROM[phase]),
            "exits_to": _exits_to(phase),
            "purpose": STAGE_PURPOSE[phase],
        }
        if phase == "triage":
            body["can_terminate_without_full_lifecycle"] = TRIAGE_CAN_TERMINATE
            body["routing_outcomes"] = dict(TRIAGE_ROUTING_OUTCOMES)
        body["allowed_tools"] = list(STAGE_ALLOWED_TOOLS[phase])
        body["forbidden_tools"] = list(STAGE_FORBIDDEN_TOOLS[phase])
        body["phase_exit_invariants"] = [dict(inv) for inv in STAGE_PHASE_EXIT_INVARIANTS[phase]]
        stages[phase] = body
    return stages
