"""Codeflair — a deterministic code-intelligence engine.

Indexes a codebase into ONE fused SQLite graph (edges tagged by source) and
queries it for blast radius / relations / gaps. No LLM in the core (CF-D11):
blast radius is transitive closure; relevance is a deterministic scoring function.

Symbol identity is the SCIP descriptor — location-independent, version-pinned,
move-stable — NOT an autoincrement row id. (The C-spike showed a row id churns on
reindex; the descriptor is the stable anchor `code_anchor` needs.)

The core has ZERO dependency on UACP (CF-D9). UACP plugs in as an adapter.
"""
from codeflair.store import Store, Symbol, Edge, VALID_SOURCES, VALID_PROVENANCE
from codeflair.query import blast_radius, heatmap, HeatmapEntry

__all__ = [
    "Store",
    "Symbol",
    "Edge",
    "VALID_SOURCES",
    "VALID_PROVENANCE",
    "blast_radius",
    "heatmap",
    "HeatmapEntry",
]
