"""Re-export shim: the projection engine moved into the Manifest engine (node 34 §3).

The structural-integrity projection now lives at ``engines.manifest.projection``;
this module re-exports its public validators so existing importers
(``from engines.graph_projection import ...``) and the ``ENGINES`` self-registration
(triggered on import) are unchanged. Importing this module imports
``engines.manifest.projection``, which registers the ``graph_projection`` Check.
"""

from __future__ import annotations

from engines.manifest.projection import (
    convergence_status,
    escalation_candidates,
    investigation_status,
    validate_check_floor,
    validate_check_replay,
    validate_class_underclaim,
    validate_graph_invariants,
    validate_graph_projection,
)

__all__ = [
    "convergence_status",
    "escalation_candidates",
    "investigation_status",
    "validate_check_floor",
    "validate_check_replay",
    "validate_class_underclaim",
    "validate_graph_invariants",
    "validate_graph_projection",
]
