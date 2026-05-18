# Addendum: CodeGraph / Graphiti Comparison

Date: 2026-05-17
Status: comparative clarification

## Question

Is LEXA/SEF becoming something like CodeGraph or Graphiti?

## Short answer

Partly, but the boundaries are different.

- CodeGraph/code property graph systems are graph construction/query systems for codebases.
- Graphiti/Zep-style systems are temporal knowledge graph/memory systems for agents.
- SEF/SGRN overlaps with Graphiti more than LEXA does.
- LEXA overlaps with retrieval frameworks/search engines more than graph-memory systems.

## Mapping

```text
CodeGraph / CPG:
  codebase -> code entity graph -> structural code queries

Graphiti / Zep:
  episodes/events -> temporal knowledge graph -> agent memory retrieval

SEF / SGRN:
  events/entities/authority/channels -> semantic graph registry + event fabric -> routing/proofs/dispatch

LEXA:
  source-owned corpora/indexes -> hybrid retrieval + rerank + BES weighting -> recall packets
```

## CodeGraph comparison

LEXA is not primarily CodeGraph.

CodeGraph systems usually parse code into graph nodes/edges such as:

- Module
- Class
- Function
- CALLS
- INHERITS_FROM
- DEPENDS_ON
- CONTAINS

LEXA may query a code graph source through an adapter, and LEXA could index code graph-derived documents/chunks. But LEXA should not be reduced to a code graph builder.

If Nortrix later needs codebase understanding, a CodeGraph source adapter could expose a repository graph as one LEXA source.

## Graphiti comparison

SEF/SGRN is closer to Graphiti than LEXA is.

Graphiti/Zep-style systems build temporally-aware context graphs for agent memory, combining temporal, full-text, semantic, and graph retrieval.

SEF/SGRN similarly needs dynamic graph relationships and event/entity resolution. But SEF adds explicit authority proofs, workspace/service/source boundaries, public/private dispatch, and policy gating.

LEXA can retrieve from a Graphiti-like graph source, but LEXA is not itself the graph memory authority.

## Correct layered view

```text
SGRN / SEF graph layer:
  entity/event/authority graph
  similar neighborhood to Graphiti-style temporal graph memory, but governance/dispatch-oriented

LEXA retrieval layer:
  hybrid retrieval engine over source-owned stores, including graph sources

CodeGraph source:
  optional source type for codebase structural graph

Graphiti-like source:
  optional source type for temporal memory/context graph
```

## Design implication

Do not merge LEXA and SGRN.

LEXA should remain the retrieval/fusion/recall API.
SGRN should remain the graph registry/authority path system.

They can integrate:

```text
LEXA retrieves graph candidates and evidence.
SGRN validates canonical graph relationships and authority paths.
SEF emits events and dispatches.
```

## Build vs adopt note

Do not rebuild CodeGraph/Graphiti primitives unless needed. If those capabilities are useful, treat them as source adapters/backends:

- CodeGraph adapter for code structure retrieval.
- Graphiti/Zep-like adapter for temporal agent memory graph retrieval.
- Neo4j/FalkorDB/OpenSearch/Qdrant/Postgres adapters depending on deployment.

## One-line positioning

```text
LEXA is not CodeGraph or Graphiti; it is the hybrid retrieval layer that can query CodeGraph-like and Graphiti-like sources. SEF/SGRN is the graph/event/authority layer closest to Graphiti, but with governance and dispatch semantics.
```
