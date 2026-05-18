# Addendum: Hybrid Retrieval Package, Not Just Semantic Search

Date: 2026-05-17
Status: correction addendum

## Correction

The proposed package/library should not be described as only "semantic search".

It should be a **hybrid retrieval / recall package** that can combine:

1. semantic/vector retrieval;
2. keyword/full-text retrieval;
3. reranking;
4. optional BES/effectiveness scoring as a sorting or weighting signal where the owning system exposes it.

## Ground-truth note from Trustless ADR-0031

Trustless ADR-0031 describes QMD as a local hybrid search engine with three retrieval tiers:

```text
qmd search  -> BM25 keyword (~0.3s)
qmd vsearch -> semantic vector (~4-6s)
qmd query   -> hybrid + rerank (~42s)
```

It also records QMD's local model stack:

- `embeddinggemma-300M` for embeddings;
- `qwen3-reranker-0.6b` for reranking;
- `qmd-query-expansion-1.7B` for query variants.

Therefore, if referencing Trustless ACP's QMD-backed control-plane retrieval, do not say it is "not BM25" categorically. The keyword tier is explicitly BM25. The broader system is not *only* BM25 and not *only* semantic search; it is hybrid retrieval with semantic vector search and reranking.

## Package naming implication

Avoid names that imply only semantic search.

Better naming direction:

- `hybrid-recall-kit`
- `retrieval-fabric`
- `recall-fabric`
- `query-fusion-kit`
- `nortrix-recall`
- `nortrix-retrieval`

Current preference for neutral scope:

```text
Hybrid Recall Kit
```

or, branded:

```text
Nortrix Retrieval Kit
```

## Package responsibilities

The package should define:

- query schema;
- source adapter contract;
- keyword/full-text retrieval hooks;
- dense semantic retrieval hooks;
- sparse or lexical retrieval hooks where available;
- query expansion hook;
- reranker hook;
- score normalization;
- fusion strategies such as RRF or weighted merge;
- optional BES weighting interface;
- recall packet schema;
- conformance tests.

## BES integration rule

BES should be optional and source-owned.

```text
Source services expose BES or effectiveness scores if they own them.
The retrieval package may consume those scores as ranking features.
The package must not mutate BES or claim authority from BES.
```

## Invariant

```text
Hybrid retrieval proposes and ranks.
BES may weight.
Graph/policy authority still decides.
```
