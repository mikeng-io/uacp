# LEXA Implementation Plan

Date: 2026-05-17
Status: implementation planning
Target repo: `/home/norty/workspace/lexa`

## Decision

Yes: implement LEXA as a standalone dedicated monorepo at:

```text
/home/norty/workspace/lexa
```

Do not place it inside Hermes, UACP, SEF, Cortex, or Trustless. LEXA is UACP-stewarded but neutral at the surface.

## Goal

Build LEXA as a source-owned universal semantic context framework: API server + SDK + adapter framework for agenda-shaped context assembly over source-owned canonical state.

## Architecture

Use pragmatic Clean Architecture + tactical DDD.

```text
Domain -> Application -> Ports -> Adapters -> Transport
```

Initial implementation stack:

```text
Language: Go
API: REST/OpenAPI first
SDK: Go SDK first
Repo: standalone monorepo
State: Postgres durable baseline for derived LEXA state
Local/dev: optional SQLite-only mode later, not first-class MVP
```

## Core invariants

1. LEXA is UACP-stewarded but neutral/generic in API and README.
2. Each service owns canonical state.
3. LEXA owns only derived index/query/runtime state.
4. LEXA groups access by Workspace -> Service -> Source.
5. Output is agenda-shaped context packets, not just search results.
6. Backends/models are pluggable.
7. REST first; gRPC only after boundaries stabilize.

## Phase 0 — Repo bootstrap

Purpose: create an empty but production-shaped repo.

Tasks:

1. Create `/home/norty/workspace/lexa`.
2. Initialize git repo.
3. Add `README.md` with neutral definition.
4. Add `GOVERNANCE.md` with UACP stewardship note.
5. Add `docs/architecture.md`.
6. Add Go module, e.g. `github.com/nortrix-labs/lexa`.
7. Add Makefile.
8. Add CI-ready commands: `make fmt`, `make test`, `make lint`.
9. Add `.gitignore`.

Acceptance:

```text
go test ./... passes
README explains LEXA without making it UACP-only
GOVERNANCE explains UACP stewardship
```

## Phase 1 — Domain model and schemas

Purpose: lock vocabulary before backend complexity.

Create domain entities:

- Workspace
- Service
- Source
- Agenda
- Query
- ContextPacket
- Result
- ScoreFeature
- Provenance
- PrivacyView
- IndexManifest
- IndexJob

Tasks:

1. Add `internal/domain` package.
2. Define stable IDs:
   - `workspace:<id>`
   - `service:<workspace>/<service>`
   - `source:<workspace>/<service>/<source>`
   - `item:<workspace>/<service>/<source>/<item>`
   - `chunk:<workspace>/<service>/<source>/<item>#<chunk>`
3. Add validation tests.
4. Add JSON schema/OpenAPI models under `api/openapi.yaml`.

Acceptance:

```text
Domain tests pass.
Invalid IDs fail validation.
Agenda -> ContextPacket types are serializable.
```

## Phase 2 — REST API skeleton

Purpose: expose transport without retrieval implementation.

Endpoints:

```text
GET  /health
POST /v1/workspaces
POST /v1/services
POST /v1/sources/register
GET  /v1/sources/{source_id}/status
POST /v1/agendas/query
POST /v1/context-packets
POST /v1/index/jobs
GET  /v1/index/jobs/{job_id}
```

Tasks:

1. Add `internal/transport/http`.
2. Add request/response validation.
3. Add in-memory app service implementation.
4. Add integration tests with `httptest`.

Acceptance:

```text
All endpoints respond with valid JSON.
Invalid workspace/service/source scopes are rejected.
No DB required yet.
```

## Phase 3 — Application ports

Purpose: define stable interfaces before adapters.

Ports:

```go
type SourceAdapter interface {}
type IndexBackend interface {}
type KeywordSearcher interface {}
type VectorSearcher interface {}
type Reranker interface {}
type BESProvider interface {}
type FusionEngine interface {}
type PacketBuilder interface {}
```

Tasks:

1. Add `internal/ports`.
2. Add application use cases:
   - RegisterSource
   - CreateIndexJob
   - RunAgendaQuery
   - BuildContextPacket
   - CheckSourceFreshness
3. Add fake adapters for tests.

Acceptance:

```text
App layer tests run without HTTP or DB.
Use cases depend only on ports/domain.
```

## Phase 4 — Postgres derived-state backend

Purpose: durable baseline for LEXA-owned derived metadata and indexes.

Initial tables:

- workspaces
- services
- sources
- index_manifests
- index_jobs
- chunks
- lexical_documents
- query_runs
- context_packets

Tasks:

1. Add migrations under `migrations/`.
2. Add `internal/adapters/postgres`.
3. Add repository tests using testcontainers or local docker compose.
4. Add manifest/content-hash tracking.

Acceptance:

```text
Migration up/down works.
Source registration persists.
Index manifest persists.
Query audit persists.
```

## Phase 5 — Filesystem source adapter

Purpose: first source adapter with no UACP coupling.

Tasks:

1. Add `internal/adapters/filesystem`.
2. Read markdown/text files from configured root.
3. Emit source items with ID, content, metadata, hash.
4. Add chunking strategy.
5. Add tests with fixtures.

Acceptance:

```text
Filesystem source indexes markdown fixtures.
Content hash changes when file changes.
Re-index skips unchanged files.
```

## Phase 6 — Keyword retrieval MVP

Purpose: prove the full pipeline before vector/model complexity.

Backend options:

- Postgres `tsvector`/GIN first.
- BM25-like ranking can be added later via OpenSearch/Qdrant/specialized backend.

Tasks:

1. Add lexical indexing for chunks.
2. Add keyword search port implementation.
3. Add `RunAgendaQuery` using keyword mode only.
4. Add context packet output with provenance.

Acceptance:

```text
POST /v1/agendas/query returns context packet from filesystem source.
Packet includes source/item/chunk provenance.
Privacy/workspace/source filters apply.
```

## Phase 7 — Vector backend interface

Purpose: add semantic retrieval without locking to one model/backend.

Tasks:

1. Add Embedder port.
2. Add VectorSearcher port.
3. Add index manifest fields:
   - embedding_model_id
   - embedding_dimension
   - similarity_metric
   - chunker_version
4. Add stub/local deterministic embedder for tests.
5. Add pgvector implementation or Qdrant implementation after interface stabilizes.

Acceptance:

```text
Changing embedding model marks index stale/incompatible.
Vector tests pass with deterministic fake embedder.
```

## Phase 8 — Fusion, rerank, BES feature hooks

Purpose: make LEXA hybrid.

Tasks:

1. Add score model:
   - lexical
   - semantic
   - sparse
   - rerank
   - bes
   - recency
   - provenance
   - final
2. Add RRF fusion.
3. Add weighted merge.
4. Add reranker interface with fake implementation.
5. Add BESProvider interface with fake/source-owned implementation.

Acceptance:

```text
Hybrid result ordering is deterministic in tests.
BES can affect ranking only as optional feature.
BES absence does not fail query.
```

## Phase 9 — SDK and CLI

Purpose: make LEXA usable by services and agents.

Tasks:

1. Add `pkg/client` Go SDK.
2. Add `pkg/adapterkit` helper interfaces.
3. Add `cmd/lexa-cli`.
4. Add CLI commands:
   - `lexa health`
   - `lexa source register`
   - `lexa index run`
   - `lexa query`

Acceptance:

```text
Go SDK can query local server.
CLI can register filesystem source, run index, query packet.
```

## Phase 10 — UACP MEMEX adapter

Purpose: first real governance integration.

Tasks:

1. Design read-only MEMEX source adapter.
2. Index MEMEX evidence/pattern docs without mutating canonical state.
3. Expose BES as optional ranking feature if available.
4. Add privacy/source scope tests.

Acceptance:

```text
MEMEX canonical state remains untouched.
LEXA derived index is rebuildable.
MEMEX query returns provenance-preserving context packet.
```

## Phase 11 — SEF adapter

Purpose: support event/entity/authority context.

Tasks:

1. Add SEF event source adapter.
2. Add graph-context source adapter if SGRN exists.
3. Support agendas like `sef.resolve_entity` and `sef.authority_context`.

Acceptance:

```text
SEF can ask LEXA for candidate context.
SEF remains responsible for graph proof and policy decisions.
```

## Non-goals for MVP

- No central canonical state ownership.
- No gRPC initially.
- No public Nora data initially.
- No automatic live dispatch.
- No direct mutation of UACP protected state.
- No required Neo4j/Qdrant/OpenSearch dependency on day one.
- No LLM-heavy reranker required for first milestone.

## Verification plan

Every phase must include:

```text
go test ./...
go vet ./...
make fmt
make lint if configured
OpenAPI validation
adapter conformance tests
privacy/scope boundary tests
```

## First concrete milestone

Milestone 1 should produce:

```text
LEXA server running locally
filesystem markdown source registered
Postgres-derived index metadata stored
keyword-only agenda query working
context packet returned with provenance
```

This validates the architecture before vector search, rerankers, BES, MEMEX, or SEF integration.

## Suggested first command sequence

```bash
mkdir -p /home/norty/workspace/lexa
cd /home/norty/workspace/lexa
git init
go mod init github.com/nortrix-labs/lexa
```

Do not run these until Mike explicitly confirms repository creation.
