# Addendum: Existing Project Landscape and Strands SDK Comparison

Date: 2026-05-17
Status: comparative positioning

## Question

Is there an existing SRE/infra project doing what LEXA proposes? Is LEXA more like AWS Strands SDK?

## Short answer

There are adjacent projects, but no exact match for the LEXA shape as currently defined.

LEXA overlaps with:

- search engines: Elasticsearch/OpenSearch/Vespa;
- vector/hybrid stores: Qdrant, Weaviate, Milvus, LanceDB;
- RAG/retrieval frameworks: LlamaIndex, Haystack, LangChain retrievers;
- local hybrid tools: QMD;
- agent SDKs: AWS Strands Agents SDK.

But LEXA's intended niche is different:

```text
Source-owned hybrid retrieval API server + SDK + adapter framework + recall packet contract + optional BES weighting + workspace/service/source isolation.
```

## AWS Strands comparison

AWS Strands Agents SDK is an agent-building SDK. It helps define agents, tools, model-driven workflows, and can integrate with knowledge bases/memory.

LEXA is not an agent SDK. LEXA is the retrieval substrate that agents/services can use.

Relationship:

```text
Strands-like SDK = agent orchestration/tool execution layer.
LEXA = hybrid retrieval/recall layer under agents and services.
```

A Strands agent could call LEXA as a tool, but LEXA itself is not equivalent to Strands.

## Existing adjacent categories

### Search infrastructure

- Elasticsearch / OpenSearch: mature SRE-grade search, lexical + vector features.
- Vespa: powerful large-scale ranking/retrieval engine with advanced ranking pipelines.

These are strong backends, but they do not define Nortrix source-owned state semantics, MEMEX/BES integration, recall packets, or SEF authority integration.

### Vector / hybrid databases

- Qdrant: strong vector/hybrid backend with dense/sparse retrieval and query API.
- Weaviate / Milvus / LanceDB: vector-centric retrieval backends.

These are index backends, not the full LEXA API/SDK boundary.

### RAG / retrieval frameworks

- LlamaIndex: source connectors, retrievers, router retrievers, rerankers, query engines.
- Haystack: production retrieval pipelines with BM25 + embeddings + rerankers.
- LangChain: retrievers, vector stores, chains.

These are closest in functionality, but tend to be app-framework oriented and Python-first. LEXA is intended as a durable API server + SDK with source-owned canonical state, workspace/service/source isolation, and governance-aware recall packet contracts.

### Local hybrid search tools

- QMD: local hybrid search with BM25, vector search, query expansion, reranking.

QMD is an important reference pattern, but LEXA is intended to become a broader API server/SDK and source adapter framework across Nortrix systems.

## LEXA differentiators

LEXA is justified if it explicitly owns these contracts:

1. Workspace -> Service -> Source isolation.
2. Source-owned canonical state invariant.
3. Durable derived index manifests.
4. Hybrid retrieval as a standard API.
5. Recall packet schema with provenance and privacy metadata.
6. BES/effectiveness weighting as optional source-owned ranking feature.
7. SEF/MEMEX/Cortex/Trustless/Hermes adapters.
8. Transport-neutral API with REST first and optional gRPC later.
9. SRE-grade lifecycle: health, freshness, rebuild, audit, backups, conformance tests.

## Build vs adopt guidance

Do not rebuild low-level search engines unnecessarily.

Use existing backends where suitable:

- Postgres/pgvector/tsvector for durable baseline.
- Qdrant for vector/sparse hybrid backend.
- OpenSearch/Elasticsearch/Vespa if large-scale search/ranking demands it.

Build LEXA for the orchestration/contract layer:

```text
source adapters + query/fusion API + recall packet contract + derived index management + governance-aware metadata.
```

## Correct positioning

```text
LEXA is closer to a retrieval control plane than a search database or agent SDK.
```
