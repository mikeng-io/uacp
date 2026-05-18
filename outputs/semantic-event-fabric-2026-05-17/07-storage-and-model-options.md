# Storage and Model Options

## Correction

Earlier Kuzu was proposed for the graph registry MVP. Mike flagged that Kuzu is deprecated. Therefore Kuzu is **not** the selected path in this capture.

## Storage principle

Do not collapse graph, events, and retrieval into one database.

```text
Graph store = canonical relationships and authority paths.
Event store = append-only history of what happened/requested.
Retrieval store = hybrid search over text, vectors, graph-derived docs, and evidence.
```

## Graph store candidates

### Neo4j

Best if SEF becomes a dedicated service with shared graph queries, operational visibility, and mature graph tooling.

Pros:
- mature property graph and Cypher ecosystem;
- good visualization/tooling;
- server/service mode fits dedicated SEF service;
- supports vector/full-text features, though QMD should still own retrieval protocol.

Cons:
- heavier ops footprint;
- server lifecycle and backup management;
- may be overkill for prototype.

### FalkorDB / RedisGraph lineage

Potential lightweight service-mode graph candidate.

Pros:
- graph queries over Redis-like deployment pattern;
- can be operationally lighter than Neo4j.

Cons:
- must verify maturity, maintenance, query semantics, backup behavior, and ecosystem fit.

### PostgreSQL + Apache AGE or edge tables

Good if operational simplicity and Postgres consolidation matter more than pure graph ergonomics.

Pros:
- familiar operations;
- transactional store;
- can model property graph with nodes/edges.

Cons:
- graph traversal/tooling weaker than dedicated graph DB;
- more app-side logic.

### SurrealDB / ArangoDB / other multi-model DBs

Worth evaluating if the service wants document+graph in one engine, but avoid choosing before testing query and ops behavior.

## Current DB recommendation

For durable design: keep graph-store choice open but treat **Neo4j as the default serious-service candidate** if SEF becomes a dedicated service.

For a very small Hermes-lite prototype, use a simple edge-table store only as a disposable bootstrap, not as the conceptual model.

## Event store candidates

MVP:
- SQLite append-only table if local/Hermes-lite.
- Postgres append-only table if service mode.

Later:
- NATS JetStream, Redpanda, Kafka, or Temporal signals if streaming/durable workflow scale requires it.

## Retrieval/QMD store candidates

- Qdrant for dense+sparse hybrid vector retrieval.
- Postgres FTS/tsvector or SQLite FTS5 for simple lexical MVP.
- Tantivy/Meilisearch if dedicated full-text service becomes useful.

## Model roles

Do not hardcode one model. Use pluggable model roles:

```yaml
models:
  embedding:
    role: dense semantic retrieval
  sparse:
    role: lexical/sparse retrieval
  reranker:
    role: candidate ordering
  resolver:
    role: ambiguity explanation and safe candidate selection
  high_judgment:
    role: risky policy/governance synthesis
```

## Model family guidance

For Mike's English/Cantonese/Mandarin environment, prefer multilingual embedding/reranking families.

Candidates to evaluate:
- BGE-M3 or current BGE multilingual successor.
- Qwen multilingual embeddings/rerankers.
- Jina multilingual embeddings/rerankers.
- OpenAI embeddings for API simplicity where acceptable.

## Safety invariant

```text
LLM/embedding/reranker may propose.
Graph proof and policy decision must authorize.
```
