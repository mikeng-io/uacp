# Addendum: LEXA Is Hybrid Retrieval Engine, Qdrant Is Backend

Date: 2026-05-17
Status: architectural clarification

## Clarification

LEXA is becoming a **hybrid retrieval engine / recall engine**, not merely a semantic search engine.

It includes semantic/vector retrieval, but also:

- lexical/keyword retrieval;
- query expansion;
- reranking;
- optional BES/effectiveness weighting;
- source/workspace/service access policy;
- recall packet assembly;
- source-owned state boundaries;
- durable derived index management.

## Qdrant relationship

Qdrant is a candidate **index backend**, not the LEXA architecture itself.

LEXA should be able to use Qdrant for dense/sparse vector retrieval, but LEXA must keep a backend abstraction so deployments can choose Postgres, OpenSearch, Qdrant, SQLite/local, or future engines.

## Model flexibility with Qdrant

Yes, LEXA can use other embedding/reranking/query-expansion models with Qdrant.

Qdrant stores/query vectors; it does not require one specific embedding model.

LEXA should record per-index model metadata:

```yaml
embedding_model_id: bge-m3 | qwen-embedding | jina | openai | custom
embedding_dimension: 1024
similarity_metric: cosine | dot | euclidean
chunker_version: ...
sparse_model_id: bm25 | splade | custom
reranker_model_id: bge-reranker | qwen-reranker | jina-reranker | custom
schema_version: ...
```

Changing embedding model usually requires re-indexing that source/index namespace because vector dimensions and embedding distributions differ.

## Algorithm flexibility

LEXA should support pluggable retrieval strategies:

- keyword/full-text: BM25, tsvector, FTS5, OpenSearch lexical;
- dense vector: Qdrant/pgvector/OpenSearch/Lance/etc.;
- sparse vector: Qdrant sparse vectors, SPLADE-like encoders, backend-supported sparse retrieval;
- fusion: RRF, weighted merge, learned/rule-based scoring;
- reranking: cross-encoder/model reranker hook;
- BES feature weighting: source-owned BES surfaced as a ranking feature.

## Correct abstraction

```text
LEXA = query/index/fusion/rerank/packet API + SDK.
Qdrant = optional vector/sparse index backend.
Model = pluggable producer/reranker of retrieval features.
Source service = canonical state owner.
```

## Durable invariant

Do not couple LEXA to one backend or one model. LEXA's contract should be stable across model/backend swaps, with index manifests declaring model/backend versions and rebuild requirements.
