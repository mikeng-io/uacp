---
type: analysis
title: Codeflair — The Code-Graph Store
description: The store the Code Engine owns — the persisted code graph (code_symbol nodes + parsed edges) the indexer produces and the query layer reads. SQLite + recursive CTE per D12; truth = files, the store is a rebuildable watermarked projection. This is what makes Codeflair an engine.
tags: [codeflair, store, code-graph, sqlite, projection]
timestamp: 2026-06-24
edges:
  - {dst: 00-overview, rel: realizes, provenance: asserted}
---

# Codeflair — The Code-Graph Store

The store is what makes Codeflair an **engine** rather than a driver: it **owns this persistence**
(no other engine touches it). The indexer ([01a](01a-indexer.md)) writes it; the query layer
([02](02-probes.md)) reads it.

## What it holds

- **`code_symbol` nodes** — file + symbol + lines + commit.
- **Deterministic edges** — `defines` / `references` / `calls` / `code_anchor` (`parsed` provenance).
- **Not** semantic vectors of the corpus (those stay in LanceDB, Oracle-scoped, D29) and **not** manifest
  edges (those are the Manifest engine's, read via a query-time join, D44:912).

## Substrate (decided by the graph-engine bake-offs; this engine consumes the verdict)

- **SQLite + recursive CTE** for all deterministic code edges — **D12** (*"SQLite for ALL deterministic
  edges (manifest + code graph)"*). The real-repo regime is 100k–1M+ edges, dense and cyclic; recursive
  CTEs handle the bounded-depth blast-radius walks the query layer needs.
- **No sqlite-vec, no SurrealDB** — D29/D17 bake-offs; semantic search stays LanceDB (Oracle), the Qwen3
  reranker is post-retrieval/store-agnostic.
- **CTE-strain watch-trigger** — D12 reserves the right to a native graph engine *only if* a measured
  deep-multi-hop wall appears on SQLite at real code-graph scale **and** a maintained embedded graph DB
  exists. **Codeflair's query benchmark is precisely the workload that probes that wall** — feed the
  result back to graph-engine D12 ([06](06-open-questions.md)).

## Trust & rebuild

- **Truth = the files; the store = a rebuildable projection**, watermarked on `repo_commit` + content
  hashes (D29). Stale watermark → rebuild; never trust a store whose watermark ≠ the working tree's.
- **Writing the store is not a governed write** — it is a derived cache (the Manifest-engine /
  graph_projection / LanceDB pattern), so it sits outside the governed-writer set without weakening the
  "no raw FS writes during a run" invariant ([01-contract](01-contract.md)).
