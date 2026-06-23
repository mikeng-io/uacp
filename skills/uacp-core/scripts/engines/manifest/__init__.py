"""The Manifest engine — the document-plane read + write model (design/graph-engine node 34).

Public door (node 32 §1/§3): re-import the engine's public names + declare ``__all__``.

CQRS door (node 34 §1/§5): the read-side is ``projection`` (the registered structural Check);
the write-side is ``create_entity`` (the typed, validated, watermarked, atomic manifest write
path — the entity-writer). The carved document validators (``validators``) are NOT re-exported
here: they are reached via Heartgate's delegating methods + run at the transition gate, and
importing them at package-load would re-enter the half-initialised ``engines.heartgate`` package
(``validators`` -> ``engines.heartgate.validators.helpers`` -> ``engines.heartgate`` -> heartgate
-> ``engines.manifest.validators``). The governed write-port (``governed_writers``) is an internal
primitive the entity-writer wraps, also not part of the public door.

The projection STAYS registered in ``ENGINES`` under the name ``"graph_projection"`` for
behaviour-identity; ``engines.graph_projection`` re-exports from here so existing call sites are
unchanged (node 34 §3).

DEFERRED (documented follow-ons, grounded in as-built constraints — see node 35 / the build log):
* the entity-writer's **governed-tool runtime exposure + Guardian unbypassable cutover** (the
  Guardian is tool-keyed, so making validate-on-write unbypassable is a BREAKING cross-runtime
  migration: a new ``uacp_entity_write`` tool + ``artifact.manifest`` category + Layer-B phase
  grammar, then restricting ``uacp_artifact_write``'s manifest roots once the entity-writer
  handles all manifest kinds);
* **re-grounding the projection to the real package model** (D42) — depends on the node-33
  schema-reconciliation BUILD and rewriting the 22 projection gate tests to real shapes.
"""

from __future__ import annotations

from .entity_writer import create_entity
from .projection import validate_graph_invariants, validate_graph_projection

__all__ = [
    "create_entity",
    "validate_graph_invariants",
    "validate_graph_projection",
]
