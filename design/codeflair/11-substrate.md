---
type: analysis
title: Codeflair — The Store (Substrate & Workload)
description: What the code-graph SQLite holds (schema), when it writes vs reads, why it's neither OLTP nor OLAP (a bulk-rebuilt, read-mostly graph index), the recursive-CTE query model, SQLite-by-default with a DuckDB watch-trigger, and that SCIP emits protobuf which Codeflair re-derives into its own SQLite.
tags: [codeflair, store, sqlite, substrate, cte, workload]
timestamp: 2026-06-24
edges:
  - {dst: 01b-store, rel: depends_on, provenance: asserted}
---

# Codeflair — The Store (Substrate & Workload)

## SCIP emits protobuf; Codeflair re-derives its own SQLite

SCIP's native output is **`index.scip` (protobuf)** — an occurrence/symbol index, *not* a traversable
graph. Codeflair ingests it (`scip print --json`, or protobuf) and **re-derives its own SQLite**
(`symbols`, `edges`, `files`) where the blast-radius walk runs as a recursive CTE. SCIP's file is the
tool's rebuildable artifact (D38); Codeflair's SQLite is a separate, watermarked projection — never a
second source of truth. *(Corrects the earlier "SCIP's native SQLite" phrasing.)*

## What it holds — ONE fused store, edges tagged by source

The edges **fuse into one SQLite** — the recursive CTE must walk the SCIP + tree-sitter edge axis
*together* (you can't CTE across separate DBs), with the coupling axis and the live LSP overlay fused in
at query time (see "Three axes" below). Each edge carries its **`source`** so reconcile, filtering, and
per-source re-ingest work:

```
symbols(id, lang, file, name, kind, line, commit)            -- nodes
edges(src_id, dst_id, rel, source, provenance)               -- the RELATIONS, tagged (EDGE axis)
        -- source ∈ {scip, tree_sitter};  provenance ∈ {parsed, syntactic, …}
coupling(file_a, file_b, kind, weight)                        -- file-level COUPLING axis: kind ∈ {co_change, shared_string}
files(path, lang, content_hash, commit)                      -- per-file hash+commit → freshness (10-freshness)
freshness(source, file, content_hash, commit, tool_version)  -- PER-SOURCE freshness manifest (each source stales independently)
watermark(repo_commit, built_at)
```

### Three axes, not one `source` enum (D3, 15-completion-roadmap.md)

A signal lands on **one of three axes**, and only the first is a persisted `edges.source`:

1. **EDGE axis — `edges.source ∈ {scip, tree_sitter}`.** The two probes that emit *real,
   persisted symbol→symbol edges*: `scip` (`parsed` — precise reference/call edges) and
   `tree_sitter` (`syntactic` — the all-language breadth floor, CF-D14). These are the only
   values `add_edge` accepts. The recursive-CTE blast walk traverses this axis.
2. **COUPLING axis — `coupling.kind ∈ {co_change, shared_string}`.** `grep` (shared-string
   tokens) and `co-change` (commit-history correlation) are **file-level couplings, not
   symbol edges** — there is no `grep`/`co_change` `edges.source`. They project to symbols at
   query time (`expand.py`, weak/`inferred`-grade), never as walkable edges. This is why
   `grep`/`co_change` are **rejected** by `add_edge`.
3. **LSP query-time overlay tier — never persisted (OD-1).** `lsp` is **not** a stored
   source. The LSP/Serena probe runs *always-live at query time* over the working tree and
   tags nodes with a freshness provenance (`live`); it writes no `source="lsp"` row. So `lsp`
   left `VALID_SOURCES` and is a query-time overlay tag, reconciled against the watermark
   (10-freshness's 3-zone `trusted`/`live`/`unreconciled`), not an ingest-time edge.

The precision ladder (CF-D14) still ranks across all three at fuse time — SCIP/LSP (`parsed`)
> tree-sitter (`syntactic`) > grep (text) > co-change (`inferred`) — but ranking at query
time is distinct from *where each signal is stored*.

**Fused for query, partitioned for ingest/freshness.** Each source ingests independently (different
cadences: SCIP per-commit batch; tree-sitter per-file-save; co-change on git change) via **source-scoped
delete-and-replace** (`DELETE WHERE source='scip' AND file=… → re-insert`). The **per-source `freshness`
manifest** is the "separate manifest" — SCIP and tree-sitter go stale on different clocks.

**Raw per-source artifacts are NOT persisted** — `index.scip` (protobuf), tree-sitter trees are
*derivable* transient ingest *inputs*; the store keeps only the normalized fused graph + the watermarks.
Nuke the SQLite anytime → rebuild from files (store = rebuildable projection; truth = files).

Not held: corpus semantic vectors (LanceDB/Oracle, D29) and manifest edges (the Manifest engine's, via a
query-time join). Cross-language edges, when present, are **`inferred`** (see [13-multi-language](13-multi-language.md)).

## Workload: neither OLTP nor OLAP — a bulk-rebuilt, read-mostly graph index

- **Writes — index time only.** Per-file **delete-and-replace** in a batch; **single writer**; infrequent
  (per commit / reindex). The query path **never writes**. Not OLTP (no concurrent small txns).
- **Reads — query time.** Recursive-CTE traversal + lookups; frequent, traversal-shaped. OLAP-ish in
  *shape* (bulk-load + read-heavy) but the hot path is a **pointer-chase**, not wide scans/aggregations.

So it is a **read-mostly, single-writer, bulk-rebuilt graph index** — a third thing, not classic
OLTP/OLAP.

## Query model: recursive CTE (why SQLite suffices)

The blast-radius walk *is* a recursive CTE over `edges` (anchor at the seed; repeatedly join `edges`;
stop at a hop cap). That is SQLite's native idiom — **no graph DB required**. The expensive model never
walks; SQLite does (**≤1ms** on the Trustless spike — see [00-overview](00-overview.md); the bake-off
*protocol* and recall@K gate live in [05-benchmark](05-benchmark.md)).

## SQLite by default; DuckDB only on a measured trigger

- **SQLite** (D12) — embedded, mature, recursive CTEs, zero-infra. The traversal is a pointer-chase, which
  **columnar/OLAP storage does not help** (it helps scans/aggregations). So DuckDB's advantage mostly
  doesn't apply to the core query.
- **DuckDB watch-trigger** (a *Codeflair-internal* measured trigger, not inherited from graph-engine):
  revisit *only if* the workload turns analytical-scan-heavy — repo-wide fan-in
  ranking, co-change **PMI** over full history — which *is* columnar-friendly. Bench SQLite-vs-DuckDB on
  *that* specific workload if it arises; for blast-radius traversal, SQLite stays. (A native graph DB
  would suit traversal best, but D12's bake-off rejected them as immature.)
