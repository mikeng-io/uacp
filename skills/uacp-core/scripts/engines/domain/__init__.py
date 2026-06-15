"""Domain read-models for the UACP engines.

PURE layer: Pydantic models only, ZERO filesystem I/O. The ``io`` layer reads
disk and returns these models; engines operate on them. Dependencies point
inward — domain depends on nothing in the package above it.

``RunManifest`` (plus the phase graph ``VALID_TRANSITIONS`` / ``TERMINAL_PHASES``
and ``Status``) is REUSED from the kernel's ``state_machine`` rather than
re-declared, so the engines and the kernel share one manifest schema.
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

from .deferral import DeferredItem  # noqa: E402
from .evidence_cluster import (  # noqa: E402
    INVARIANT_CLUSTER_FAMILIES,
    ClusterPhase,
    ClusterState,
    EvidenceCluster,
)
from .ledger import LedgerEntry  # noqa: E402
from .pointer import CurrentPointer  # noqa: E402
from .registry import RunRegistry, RunRegistryEntry  # noqa: E402
from .scope import Scope  # noqa: E402

__all__ = [
    "INVARIANT_CLUSTER_FAMILIES",
    "TERMINAL_PHASES",
    "VALID_TRANSITIONS",
    "ClusterPhase",
    "ClusterState",
    "CurrentPointer",
    "DeferredItem",
    "EvidenceCluster",
    "LedgerEntry",
    "RunManifest",
    "RunRegistry",
    "RunRegistryEntry",
    "Scope",
    "Status",
]
