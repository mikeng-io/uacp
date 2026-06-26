"""Codeflair — a deterministic code-intelligence engine.

Indexes a codebase into ONE fused SQLite graph (edges tagged by source) and
queries it for blast radius / relations / gaps. No LLM in the core (CF-D11):
blast radius is transitive closure; relevance is a deterministic scoring function.

Symbol identity is the SCIP descriptor — location-independent, version-pinned,
move-stable — NOT an autoincrement row id. (The C-spike showed a row id churns on
reindex; the descriptor is the stable anchor `code_anchor` needs.)

The core has ZERO dependency on UACP (CF-D9). UACP plugs in as an adapter.
"""

from codeflair.expand import ExpandResult, Gap, expand, find_test_gaps
from codeflair.freshness import FileStatus, compare_file, content_hash
from codeflair.overlay import (
    FileConflict,
    FreshnessTag,
    LspOverlay,
    ReconcileResult,
    reconcile_overlay,
)
from codeflair.probes import (
    CouplingProjectionProbe,
    PreciseEdgeWalkProbe,
    Probe,
    ProbeContext,
    ProbeParams,
    ProbeRegistry,
    default_registry,
)
from codeflair.query import HeatmapEntry, blast_radius, heatmap
from codeflair.serena_overlay import SerenaOverlay, load_serena_overlay
from codeflair.store import (
    VALID_COUPLING,
    VALID_PROVENANCE,
    VALID_SOURCES,
    Edge,
    Store,
    Symbol,
    default_store_path,
)

__all__ = [
    "Store",
    "Symbol",
    "Edge",
    "VALID_SOURCES",
    "VALID_PROVENANCE",
    "VALID_COUPLING",
    "default_store_path",
    "content_hash",
    "compare_file",
    "FileStatus",
    "blast_radius",
    "heatmap",
    "HeatmapEntry",
    "expand",
    "find_test_gaps",
    "ExpandResult",
    "Gap",
    "Probe",
    "ProbeContext",
    "ProbeParams",
    "ProbeRegistry",
    "PreciseEdgeWalkProbe",
    "CouplingProjectionProbe",
    "default_registry",
    "LspOverlay",
    "FreshnessTag",
    "FileConflict",
    "ReconcileResult",
    "reconcile_overlay",
    "SerenaOverlay",
    "load_serena_overlay",
]
