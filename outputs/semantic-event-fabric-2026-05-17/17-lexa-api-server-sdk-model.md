# Addendum: LEXA API Server + SDK Model

Date: 2026-05-17
Status: architectural refinement

## Correction / refinement

LEXA should not be framed as only a package/library. A better mature shape is:

```text
LEXA = API server + SDK + adapter/index backend framework
```

The SDK/package remains important, but the API server becomes the standard runtime surface for services that want a shared query interface, adapter hosting, indexing orchestration, and recall packet assembly.

## State ownership invariant remains unchanged

```text
Each service owns canonical state.
LEXA does not become the central source-of-truth database.
LEXA may own derived indexes, manifests, caches, and query runtime state per source/deployment.
```

This means LEXA server may store derived retrieval state, but it must be clearly rebuildable and traceable to source-owned canonical records.

## Mature architecture

```text
Source Service Canonical State
  ├── UACP MEMEX state
  ├── SEF events / graph state
  ├── Cortex recall/evidence state
  ├── Trustless evidence state
  └── Hermes memory/session state
        │
        │ source adapter / SDK
        ▼
LEXA API Server
  ├── source registry
  ├── adapter host
  ├── indexing orchestrator
  ├── derived index backend(s)
  ├── hybrid retrieval engine
  ├── query expansion
  ├── reranker interface
  ├── BES weighting interface
  ├── recall packet builder
  └── audit / freshness / manifest state
        │
        ▼
Clients
  ├── UACP MEMEX
  ├── SEF resolver
  ├── Cortex
  ├── Trustless tools
  ├── Hermes tools
  └── agents
```

## SDK responsibilities

The LEXA SDK should provide:

- source adapter base classes;
- query client;
- indexing client;
- schema models;
- recall packet validator;
- local embedded mode for tests/dev;
- backend plugin interface;
- conformance test helpers.

## API server responsibilities

The LEXA API server should provide:

- HTTP/gRPC API for query and indexing;
- source registration;
- source health/freshness status;
- incremental indexing orchestration;
- derived index management;
- multi-source query fanout;
- lexical + semantic retrieval;
- query expansion;
- reranking;
- optional BES feature weighting;
- recall packet assembly;
- audit trail for query/index operations.

## Source-owned state model

Each source service chooses one of these integration modes:

### Pull mode

LEXA server uses an adapter to read canonical source records and maintain a derived index.

Good for document/artifact stores where LEXA can crawl/query source APIs.

### Push mode

Source service emits index update events or calls LEXA indexing APIs when canonical state changes.

Good for evented systems and services with strict ownership boundaries.

### Embedded mode

Service uses LEXA SDK locally without a shared API server.

Good for tests, small deployments, or privacy-sensitive isolated environments.

## Database / backend model

LEXA server should support pluggable backends.

Recommended mature baseline:

```text
Postgres:
  - canonical to LEXA's own derived metadata/manifests/audit;
  - tsvector/GIN for keyword index where appropriate;
  - pgvector for dense embeddings where appropriate.
```

Optional specialized backends:

```text
Qdrant:
  - dense/sparse vector index at scale.

OpenSearch/Elasticsearch:
  - full-text + vector hybrid at larger document scale.

Local/embedded:
  - SQLite FTS5 + local vector backend for dev/test/small profile-local deployments.
```

Important: these are LEXA's derived index stores, not canonical source state stores.

## Elasticity and durability

LEXA API server needs:

- source partitioning;
- index namespace per source/scope/tenant;
- durable index manifests;
- content hash/version tracking;
- incremental reindex jobs;
- rebuild-from-source capability;
- backup/restore for derived indexes when rebuild cost is high;
- horizontal split later by source or index backend;
- idempotent indexing APIs.

## MEMEX migration implication

When LEXA matures, UACP MEMEX should use LEXA server/SDK for semantic/hybrid retrieval state management over MEMEX-owned canonical state.

```text
MEMEX owns records and BES.
LEXA indexes/query/reranks/assembles recall packets.
UACP governed writers still own canonical mutation.
```

## Revised canonical phrase

```text
LEXA is a source-owned hybrid retrieval API server and SDK for lexical, semantic, reranked, optionally BES-weighted recall. It standardizes query/index/adapter contracts and may maintain durable derived indexes, while each source service retains canonical state ownership.
```
