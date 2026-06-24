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

## What it holds

```
symbols(id, lang, file, name, kind, line, commit)      -- nodes
edges(src_id, dst_id, rel, provenance)                 -- the RELATIONS (defines/references/calls; co_change=inferred)
files(path, lang, content_hash)                        -- per-file hash → freshness (see 10-freshness)
watermark(repo_commit, built_at)
```

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
walks; SQLite does (≤1ms at the scale tested — see [05-benchmark](05-benchmark.md)).

## SQLite by default; DuckDB only on a measured trigger

- **SQLite** (D12) — embedded, mature, recursive CTEs, zero-infra. The traversal is a pointer-chase, which
  **columnar/OLAP storage does not help** (it helps scans/aggregations). So DuckDB's advantage mostly
  doesn't apply to the core query.
- **DuckDB watch-trigger** (a *Codeflair-internal* measured trigger, not inherited from graph-engine):
  revisit *only if* the workload turns analytical-scan-heavy — repo-wide fan-in
  ranking, co-change **PMI** over full history — which *is* columnar-friendly. Bench SQLite-vs-DuckDB on
  *that* specific workload if it arises; for blast-radius traversal, SQLite stays. (A native graph DB
  would suit traversal best, but D12's bake-off rejected them as immature.)
