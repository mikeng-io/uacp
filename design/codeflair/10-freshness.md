---
type: analysis
title: Codeflair — Freshness & the Dirty-Tree Problem
description: How the committed-snapshot SQLite store stays correct against a dirty working tree — which is the PRIMARY case for a coding agent. Per-file content-hash invalidation (the index always knows what's stale, zero reindex), never full-reindex on the query path, the runtime three-zone reconcile (clean/dirty/disagree), the optional working-overlay layer, and freshness tags on the heatmap.
tags: [codeflair, freshness, dirty-tree, watermark, staleness, reconcile]
timestamp: 2026-06-24
edges:
  - {dst: 01b-store, rel: depends_on, provenance: asserted}
---

# Codeflair — Freshness & the Dirty-Tree Problem

## The problem (and why it's the *primary* case)

The store is a **committed snapshot** (SCIP indexes a commit). A coding agent almost always works on a
**dirty tree** — uncommitted edits — so the store is stale w.r.t. what you're editing *most of the time*.
Dirty-tree correctness is therefore **the common case, not an edge case.** Codeflair must be correct here
or it is wrong exactly when it's used.

## Index side — the store always *knows* what's stale, for free

The `files` table stores `(path, content_hash)` per indexed file, and the store carries a **watermark**
(`repo_commit` + those hashes). Comparing a working-tree file's hash to the stored hash makes a dirty
file just a **hash mismatch** — detectable with **zero re-indexing**. The store never pretends a dirty
file is fresh; its rows for that file are marked `stale` the instant the hash diverges.

**It never full-reindexes the working tree on the query path** (that is the ~42s trap). Re-index is
always **delta-only, commit-triggered** (tree-sitter flags the changed files; SCIP re-does just those;
watermark advances).

## Two ways to handle the stale (dirty) files

| | **Committed-only store (default)** | **Working-overlay layer (scale-up)** |
|---|---|---|
| Store | last commit's graph only | committed base **+** a transient `working` layer |
| Dirty file | rows flagged `stale`, **not written** → patched at query time by the live **LSP** overlay | a watcher / pre-query hook **micro-reindexes just that one saved file** (single-file tree-sitter/SCIP — fast) into the `working` layer, which **shadows** the base rows |
| On commit | next delta-index folds it in | `working` rows fold into base; layer cleared |
| Cost | nothing extra written; live-LSP per query | one micro-reindex per save; then queries need no live LSP |
| Use when | edits are scattered / one-off | you re-query the **same** dirty files repeatedly (agent iterating one module) |

Default to committed-only + flag + live-LSP overlay; add the working layer only when a measured
edit-then-query loop shows live overlay is the bottleneck (house style — benchmark it).

## Query side — the three-zone reconcile (per-file)

The watermark classifies every file cheaply at query time:

1. **Clean** (hash matches) → the **store** is authoritative; SQL-walk it (fast, trusted).
2. **Dirty** (hash diverged) → store rows are **stale** → **LSP live** (it reads the working tree) overlays
   them (or the working layer already holds them).
3. **Disagree** (SCIP says X, LSP says ¬X — e.g. thin LSP after a structural change) → **keep both, mark
   `unreconciled`, surface it.** Never silently pick.

## The heatmap carries freshness, openly

Every node is tagged `trusted` (clean store) · `live` (LSP overlay on a dirty file) · `unreconciled`
(SCIP↔LSP conflict). The orchestrator *sees* what's stale instead of trusting a silent blend — the same
"surface, don't hide" discipline as provenance. Standalone, stale → overlay/flag; under UACP a watermark
mismatch can additionally **block** a closure (the D24 "stale = block" rule).
