# Addendum: LEXA as Future MEMEX Semantic State Layer

Date: 2026-05-17
Status: design refinement

## Clarification

When LEXA matures beyond prototype, UACP MEMEX should migrate to using LEXA for semantic state management / hybrid retrieval over MEMEX-owned state.

This does not mean LEXA owns MEMEX state.

```text
MEMEX owns UACP canonical memory/evidence/pattern state.
LEXA provides the hybrid retrieval/indexing/query/fusion layer used over that state.
```

## Correct relationship

```text
UACP MEMEX
  ├── canonical evidence records
  ├── pattern registry
  ├── recall packet semantics
  ├── BES source-owned scores
  └── uses LEXA for semantic/hybrid retrieval once LEXA is mature

LEXA
  ├── package/library/protocol
  ├── source adapter contract
  ├── derived indexes
  ├── lexical + semantic retrieval
  ├── query expansion
  ├── reranking
  ├── optional BES weighting interface
  └── recall packet assembly utilities
```

## Semantic state management meaning

For MEMEX, “semantic state management” means managing the derived retrieval/index layer around canonical MEMEX state:

- chunking evidence and pattern records;
- indexing text lexically;
- embedding semantic chunks;
- tracking source version/content hashes;
- maintaining freshness and rebuild state;
- exposing query adapters;
- fusing keyword/vector/reranker/BES signals;
- returning provenance-preserving recall packets.

It does **not** mean LEXA mutates canonical UACP lifecycle state, evidence records, or BES scores without governed writers.

## Migration direction

Prototype path:

1. LEXA defines schemas, adapters, index backend interfaces, and fusion/ranking utilities.
2. MEMEX exposes a LEXA source adapter over its canonical evidence/pattern state.
3. LEXA builds a derived MEMEX retrieval index under UACP-owned storage.
4. MEMEX recall operations call LEXA instead of ad hoc semantic/hybrid search logic.
5. BES remains source-owned and may be surfaced as a ranking feature.
6. Any BES mutation or canonical MEMEX state mutation remains governed by UACP writers.

## State invariant

```text
Canonical MEMEX state stays in UACP.
LEXA index state is derived, versioned, durable, and rebuildable.
LEXA can become MEMEX's semantic retrieval engine without becoming MEMEX's authority layer.
```

## Design consequence

LEXA should be designed as a package/library with enough abstraction to support MEMEX as a first-class source:

- stable adapter API;
- source-owned state references;
- index manifests;
- incremental reindex hooks;
- BES ranking feature hooks;
- provenance-preserving recall packet output;
- backend pluggability for durable indexes.

## Durable backend expectation

For MEMEX-grade use, avoid relying only on ephemeral or toy embedded vector storage. The derived LEXA index should support durable, elastic backends such as Postgres+pgvector+tsvector or a source-owned vector/search backend where appropriate.
