# Addendum: LEXA State Management Framework

Date: 2026-05-17
Status: design refinement

## Locked naming / ownership

`LEXA` is the working single-name package/library for hybrid retrieval.

LEXA is **not** a central state database and not primarily a daemon.

```text
LEXA = package/library/protocol for source-owned hybrid retrieval.
```

It combines:

- keyword/full-text retrieval;
- semantic/vector retrieval;
- query expansion;
- reranking;
- optional BES/effectiveness weighting;
- recall packet assembly;
- adapter conformance tests.

## State ownership invariant

```text
Each service owns its canonical state.
LEXA owns retrieval contracts and reusable indexing/query logic.
LEXA must not force services to share one state database.
```

Examples:

- UACP MEMEX owns UACP evidence/pattern/BES state.
- SEF owns graph/events/authority proof state.
- Cortex owns editorial recall/evidence state.
- Trustless owns Trustless evidence/control-plane state.
- Hermes owns sessions/memory.

LEXA interacts through adapters and optional local indexes.

## Concrete state framework

Use a three-layer state model per service/source:

### 1. Canonical source state

The service's own authoritative data.

Examples:

- markdown docs;
- events table;
- graph DB;
- proposal artifacts;
- memory/session store;
- workflow state;
- evidence records.

LEXA never becomes the canonical owner of this layer.

### 2. LEXA local retrieval index

A derived, rebuildable index owned by the source service or deployment.

Contains:

- normalized chunks;
- full-text index;
- dense embeddings;
- sparse/lexical vectors if used;
- metadata filters;
- source pointers;
- freshness/version hashes.

This layer must be durable, but not authoritative. It can be rebuilt from canonical source state.

### 3. LEXA query/runtime cache

Optional transient cache for query expansion, reranker outputs, frequent recall packets, or source health.

This layer is disposable and should have TTLs.

## Elastic and durable state requirement

Durability comes from:

- source-owned canonical state;
- append-only or versioned source records;
- rebuildable derived indexes;
- index manifests with content hashes;
- snapshots/backups of local indexes when rebuild cost is high.

Elasticity comes from:

- per-source adapters;
- pluggable index backends;
- sharding/partitioning by source/scope/collection;
- optional remote index backends;
- optional daemon/caching layer only when needed.

## Backend abstraction

LEXA should define interfaces rather than one required database:

```text
LexaSourceAdapter
  -> exposes canonical items and metadata

LexaIndexBackend
  -> stores full-text/vector/sparse indexes

LexaFusionEngine
  -> combines lexical, semantic, rerank, BES, recency, authority features

LexaPacketBuilder
  -> emits recall packets with provenance
```

## Backend candidates by deployment mode

### Local / embedded

Useful for Hermes-lite or per-service local deployment.

- SQLite FTS5 for keyword/full-text.
- sqlite-vec or LanceDB for vectors, if acceptable.
- DuckDB + extensions where analytics-style retrieval matters.
- Local files + manifest for small sources.

### Durable service-owned production

Useful where state durability and concurrent access matter.

- Postgres with pgvector + tsvector/GIN for combined lexical/vector indexes.
- Qdrant for vector/sparse/hybrid indexes plus source metadata.
- OpenSearch/Elasticsearch for lexical + vector hybrid where ops already exist.
- Neo4j remains SEF graph candidate, not the default LEXA retrieval index.

### Graph source integration

Graph stores remain source-owned. LEXA queries graph sources through adapters and may use graph-derived priors/features, but it should not require graph data to be copied into LEXA as canonical state.

## Recommended first implementation direction

Start with package-level abstractions and a Postgres/Qdrant-capable design, not a single embedded vector DB mandate.

MVP can support:

```text
LexaIndexBackend:
  - SQLite FTS5 + local vector backend for small/local tests
  - Postgres pgvector + tsvector as the durable baseline candidate
```

Evaluate Qdrant for dense+sparse hybrid if retrieval quality/scale requires it.

## Critical rule

Do not say “just use an embedded vector DB.”

An embedded vector DB alone does not solve:

- keyword retrieval;
- source-owned state;
- durability semantics;
- index rebuild/versioning;
- reranking;
- BES weighting;
- recall packet provenance;
- privacy/scope filtering.

## Canonical invariant

```text
Canonical state stays with source services.
LEXA indexes are derived, versioned, rebuildable, and deployment-local.
LEXA backends must be pluggable.
Durable baseline should support Postgres-class persistence; embedded backends are for local/MVP only.
```
