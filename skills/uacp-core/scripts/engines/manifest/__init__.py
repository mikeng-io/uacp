"""The Manifest engine — the document-plane read + write model (design/graph-engine node 34).

Public door (node 32 §1/§3): re-import the engine's public names + declare ``__all__``.

Phase C is built in increments: this increment lands the **read-side projection**
(``graph_projection`` moved here as ``projection.py``). The document validators,
governed writers, and the entity-writer (write-side) land in subsequent increments.

The projection STAYS registered in ``ENGINES`` under the name ``"graph_projection"``
for behaviour-identity; ``engines.graph_projection`` re-exports from here so existing
call sites are unchanged (node 34 §3).
"""

from __future__ import annotations

from .projection import validate_graph_invariants, validate_graph_projection

__all__ = [
    "validate_graph_invariants",
    "validate_graph_projection",
]
