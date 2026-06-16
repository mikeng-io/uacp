"""Domain read-models for the UACP engines.

PURE layer: Pydantic models only, ZERO filesystem I/O. The ``io`` layer reads
disk and returns these models; engines operate on them. Dependencies point
inward — domain depends on nothing in the package above it.

``RunManifest`` (plus the phase graph ``VALID_TRANSITIONS`` / ``TERMINAL_PHASES``
and ``Status``) is REUSED from the kernel's ``state_machine`` rather than
re-declared, so the engines and the kernel share one manifest schema.

Slice 4a Task 3: ``CurrentPointer`` expanded with optional fields +
``CURRENT_POINTER_REQUIRED_FIELDS`` constant; ``LedgerEntry`` expanded with
optional phase/result/reviewer fields; ``EscalationRecord`` added (new module).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the uacp-state state_machine importable so RunManifest can be REUSED
# (not duplicated) regardless of how this package is imported.
_ENGINES_DIR = Path(__file__).resolve().parents[1]
_CORE_DIR = _ENGINES_DIR.parent
_STATE_DIR = _CORE_DIR.parents[1] / "uacp-state" / "scripts"
for _p in (str(_CORE_DIR), str(_STATE_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from state_machine import (  # noqa: E402  (path bootstrap must precede import)
    TERMINAL_PHASES,
    VALID_TRANSITIONS,
    RunManifest,
    Status,
)

from .artifact_schema import (  # noqa: E402
    BLAST_RADIUS_VALUES,
    BlastRadius,
    EvidenceDispositionSchema,
    IntentSchema,
    LessonsSchema,
    ScopeSchema,
    artifact_schemas_dict,
)
from .checkpoint import CheckpointEntry  # noqa: E402
from .deferral import DeferredItem  # noqa: E402
from .escalation import (  # noqa: E402
    EscalationMode,
    EscalationRecord,
    EscalationSeverity,
)
from .evidence_cluster import (  # noqa: E402
    INVARIANT_CLUSTER_FAMILIES,
    ClusterPhase,
    ClusterState,
    EvidenceCluster,
)
from .gate_rules import (  # noqa: E402
    HEARTGATE_COHERENCE_MIN_GRANULARITY_DEFAULT,
    HEARTGATE_COHERENCE_REQUIRED_FIELD,
    HEARTGATE_COHERENCE_REQUIRED_LENSES,
    HEARTGATE_COHERENCE_SELECTORS_DEFAULT,
    PIV_CHECKS,
    PIV_LEDGER_REQUIRED,
    PIV_LEDGER_REQUIRED_FIELDS,
    PIV_MAX_ATTEMPTS,
    PIV_SECOND_FAILURE_ACTION,
    PLAN_NOT_APPLICABLE_REQUIRED_FIELDS,
    PLAN_REQUIRED_UNIVERSAL_CORE,
    PLAN_VALIDATION_CHECKS,
    PLAN_VALIDATION_LEDGER_GATE_NAME,
    PLAN_VALIDATION_LEDGER_REQUIRED_FIELDS,
    PLAN_VALIDATION_LEDGER_REQUIRED_PHASE,
    PLAN_VALIDATION_REQUIRED_LEDGER_GATE_FOR_TRANSITION,
    PROPOSAL_NOT_APPLICABLE_REQUIRED_FIELDS,
    PROPOSAL_REQUIRED_UNIVERSAL_CORE,
    RUN_REGISTRY_ENFORCEMENT_DEFAULT,
    heartgate_coherence_required_when_default,
    piv_rule_default,
    plan_validation_gate_default,
    run_registry_rule_default,
)
from .ledger import LedgerEntry, LedgerResult, LedgerReviewer  # noqa: E402

# Re-export the canonical lifecycle-graph accessors so the rest of the codebase
# has ONE access path. state_machine derives VALID_TRANSITIONS/TERMINAL_PHASES
# from these (via a bare phase_graph import), so the constants above and these
# accessors share a single source of truth.
from .phase_graph import (  # noqa: E402
    LIFECYCLE_GRAPH,
    lifecycle_edges,
    runtime_terminal_phases,
    state_machine_projection,
)
from .phase_transitions import (  # noqa: E402
    COUNCIL_SYNTHESIS_REQUIRED_FIELDS,
    PHASE_TRANSITION_REQUIRED_FIELDS,
    PHASE_TRANSITION_TERMINAL_KIND_VALUES,
    STAGE_ALLOWED_TOOLS,
    STAGE_ENTERS_FROM,
    STAGE_FORBIDDEN_TOOLS,
    STAGE_PHASE_EXIT_INVARIANTS,
    STAGE_PURPOSE,
    TRIAGE_CAN_TERMINATE,
    TRIAGE_ROUTING_OUTCOMES,
    council_synthesis_required_fields,
    phase_transition_required_fields,
    phase_transition_terminal_kind_values,
    stages_default,
)
from .pointer import (  # noqa: E402
    CURRENT_POINTER_REQUIRED_FIELDS,
    CurrentPointer,
    MutationPolicy,
    UacpMode,
)
from .registry import RunRegistry, RunRegistryEntry  # noqa: E402
from .scope import Scope  # noqa: E402

__all__ = [
    "BLAST_RADIUS_VALUES",
    "LIFECYCLE_GRAPH",
    "BlastRadius",
    "CURRENT_POINTER_REQUIRED_FIELDS",
    "EscalationMode",
    "EscalationRecord",
    "EscalationSeverity",
    "EvidenceDispositionSchema",
    "INVARIANT_CLUSTER_FAMILIES",
    "IntentSchema",
    "LedgerResult",
    "LedgerReviewer",
    "LessonsSchema",
    "MutationPolicy",
    "ScopeSchema",
    "TERMINAL_PHASES",
    "VALID_TRANSITIONS",
    "CheckpointEntry",
    "ClusterPhase",
    "ClusterState",
    "CurrentPointer",
    "DeferredItem",
    "EvidenceCluster",
    "HEARTGATE_COHERENCE_MIN_GRANULARITY_DEFAULT",
    "HEARTGATE_COHERENCE_REQUIRED_FIELD",
    "HEARTGATE_COHERENCE_REQUIRED_LENSES",
    "HEARTGATE_COHERENCE_SELECTORS_DEFAULT",
    "PIV_CHECKS",
    "PIV_LEDGER_REQUIRED",
    "PIV_LEDGER_REQUIRED_FIELDS",
    "PIV_MAX_ATTEMPTS",
    "PIV_SECOND_FAILURE_ACTION",
    "PLAN_NOT_APPLICABLE_REQUIRED_FIELDS",
    "PLAN_REQUIRED_UNIVERSAL_CORE",
    "PLAN_VALIDATION_CHECKS",
    "PLAN_VALIDATION_LEDGER_GATE_NAME",
    "PLAN_VALIDATION_LEDGER_REQUIRED_FIELDS",
    "PLAN_VALIDATION_LEDGER_REQUIRED_PHASE",
    "PLAN_VALIDATION_REQUIRED_LEDGER_GATE_FOR_TRANSITION",
    "PROPOSAL_NOT_APPLICABLE_REQUIRED_FIELDS",
    "PROPOSAL_REQUIRED_UNIVERSAL_CORE",
    "RUN_REGISTRY_ENFORCEMENT_DEFAULT",
    "heartgate_coherence_required_when_default",
    "piv_rule_default",
    "plan_validation_gate_default",
    "run_registry_rule_default",
    "LedgerEntry",
    "RunManifest",
    "COUNCIL_SYNTHESIS_REQUIRED_FIELDS",
    "PHASE_TRANSITION_REQUIRED_FIELDS",
    "PHASE_TRANSITION_TERMINAL_KIND_VALUES",
    "STAGE_ALLOWED_TOOLS",
    "STAGE_ENTERS_FROM",
    "STAGE_FORBIDDEN_TOOLS",
    "STAGE_PHASE_EXIT_INVARIANTS",
    "STAGE_PURPOSE",
    "TRIAGE_CAN_TERMINATE",
    "TRIAGE_ROUTING_OUTCOMES",
    "council_synthesis_required_fields",
    "phase_transition_required_fields",
    "phase_transition_terminal_kind_values",
    "stages_default",
    "lifecycle_edges",
    "runtime_terminal_phases",
    "state_machine_projection",
    "RunRegistry",
    "RunRegistryEntry",
    "Scope",
    "Status",
    "UacpMode",
    "artifact_schemas_dict",
]
