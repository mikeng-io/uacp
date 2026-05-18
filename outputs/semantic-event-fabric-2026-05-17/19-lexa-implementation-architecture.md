# Addendum: LEXA Implementation Architecture — CA, DDD, API, Language, Repo

Date: 2026-05-17
Status: architectural recommendation

## Recommendation summary

LEXA should use a pragmatic Clean Architecture + DDD-inspired boundary model.

Recommended initial implementation:

```text
Language: Go
Repo: dedicated monorepo
API: REST/HTTP first, internal service interface designed so gRPC can be added later
SDK: Go SDK first; Python/TypeScript clients later if needed
Storage: pluggable backend interfaces; Postgres as durable baseline candidate
```

## Clean Architecture

Use Clean Architecture to keep retrieval logic independent from API, database, and model backends.

Layers:

```text
Domain
  Query, Source, Document, Chunk, IndexManifest, RetrievalResult, RecallPacket, ScoreFeature

Application
  RegisterSource, IndexSource, QuerySources, BuildRecallPacket, RefreshIndex, CheckFreshness

Ports
  SourceAdapter, IndexBackend, Embedder, KeywordSearcher, VectorSearcher, Reranker, BESProvider, PolicyProvider

Adapters
  Postgres, Qdrant, OpenSearch, filesystem, UACP MEMEX, SEF, Cortex, Trustless, Hermes memory

Transport
  REST API, SDK, optional gRPC later, CLI
```

## DDD boundary

Use DDD tactically, not ceremonially.

Core bounded context:

```text
Hybrid Retrieval / Recall Context
```

Subdomains:

- Source Registry
- Index Management
- Query Planning
- Retrieval Fusion
- Reranking
- Recall Packet Assembly
- Freshness/Audit

Aggregate-like boundaries:

- Workspace
- Service
- Source
- IndexManifest
- QueryRun
- RecallPacket

DDD is useful for vocabulary and boundaries; avoid overbuilding event sourcing or heavy aggregates before the MVP.

## API choice

### REST/HTTP first

Use REST/HTTP+JSON first because:

- easiest for Hermes, scripts, agents, and services;
- easy to debug with curl;
- OpenAPI can generate SDKs;
- good enough for query/index operations;
- lower operational friction than gRPC during early design churn.

Initial endpoints:

```text
GET  /health
GET  /v1/workspaces
POST /v1/sources/register
POST /v1/index/jobs
GET  /v1/index/jobs/{id}
POST /v1/query
POST /v1/recall-packets
GET  /v1/sources/{source_id}/status
```

### gRPC later / optional

Add gRPC when:

- high-throughput service-to-service queries need lower overhead;
- streaming indexing or result streaming becomes important;
- strongly typed polyglot clients become a priority;
- internal microservice deployment stabilizes.

Design application services transport-neutral so REST and gRPC call the same use cases.

## Language

### Go recommended

Go is the best initial API server language for LEXA because:

- strong fit for durable API servers;
- simple concurrency for indexing jobs and query fanout;
- easy static binary deployment;
- good Postgres, OpenSearch, Qdrant, gRPC, OpenAPI ecosystem;
- aligns with SRE/service operational expectations;
- avoids Python dependency drift for core infra.

### Python still useful

Python can be used for:

- model experimentation;
- embedding/reranker adapters;
- notebooks/evaluation;
- optional sidecar workers if a model library is Python-only.

But the control/API plane should likely be Go.

## Monorepo

Use a dedicated LEXA monorepo.

Recommended structure:

```text
lexa/
├── cmd/
│   ├── lexa-server/
│   └── lexa-cli/
├── internal/
│   ├── domain/
│   ├── app/
│   ├── ports/
│   ├── adapters/
│   │   ├── postgres/
│   │   ├── qdrant/
│   │   ├── opensearch/
│   │   ├── filesystem/
│   │   ├── uacp/
│   │   ├── sef/
│   │   └── cortex/
│   └── transport/
│       ├── http/
│       └── grpc/        # later
├── pkg/
│   ├── client/          # public Go SDK
│   ├── schema/          # stable public schemas/types
│   └── adapterkit/      # adapter helpers safe for external services
├── api/
│   ├── openapi.yaml
│   └── proto/           # later
├── migrations/
├── docs/
├── examples/
└── tests/
```

Keep source-specific adapters in-tree initially for coherence. Split adapters into separate repos only after APIs stabilize.

## State rule

LEXA server may manage derived state only:

- source registry;
- index manifests;
- chunks/embeddings/full-text indexes;
- query audit;
- freshness status;
- caches.

Canonical state remains source-owned.

## First implementation tranche

1. Define domain/schema models.
2. Implement REST API skeleton.
3. Implement workspace/service/source registry.
4. Implement Postgres-backed metadata/index manifest store.
5. Implement simple filesystem source adapter.
6. Implement keyword search first.
7. Add vector backend behind interface.
8. Add recall packet output.
9. Add UACP MEMEX adapter after core contracts stabilize.

## Decision invariant

```text
CA keeps dependencies inward.
DDD keeps vocabulary stable.
REST keeps early integration easy.
gRPC remains an internal/high-throughput option.
Go is the API/control-plane default.
Monorepo keeps schemas, server, SDK, adapters, and tests coherent during early evolution.
```
