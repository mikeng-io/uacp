---
type: analysis
title: Codeflair — The Indexer (Producer)
description: The producer half the gap was missing — SCIP per-commit (persisted) + LSP live, emitting code_symbol nodes and code_anchor/calls/references edges into the code-graph store. Closes the "code_anchor is a declared edge type with no producer" gap. Build-side; writes a rebuildable projection.
tags: [codeflair, indexer, scip, lsp, producer, code-anchor]
timestamp: 2026-06-24
edges:
  - {dst: 01b-store, rel: depends_on, provenance: asserted}
---

# Codeflair — The Indexer (Producer)

## The gap this closes

`code_anchor` (checkpoint → `code_symbol`) and `code_symbol` are **declared edge/node types in the
graph schema** (`graph-engine/10-edge-schema.md:62`) with **no producer** — *"no code indexing exists
today"* (`graph-engine/20-slices-readiness.md`). graph-engine flagged the code plane as *"the real
strain"* (D12) and never built the thing that emits these edges. The indexer **is** that thing. Without
it, the query layer ([02](02-probes.md)) has no precise symbol edges to walk — only LSP/grep/co-change.

> **Adopted, not built (CF-D14, [14-prior-art-and-adoption](14-prior-art-and-adoption.md)):** Codeflair
> does **not** build a new indexer — it **adopts** the substrate (`scip-go`/SCIP indexers, a tree-sitter
> graph tool, Serena for LSP) and owns only the **normalized, watermarked fused projection + the
> `code_symbol`/`code_anchor` schema** ([11-substrate](11-substrate.md)). "The indexer is that thing"
> means *the engine wires/runs the adopted indexers into the store* — not that we write one.

Per D44's Code-engine shape (*"build = SCIP per-commit (persisted) + LSP live"*):

- **SCIP per-commit (persisted)** — the symbol-precise core. Emits `code_symbol` nodes (file + symbol +
  lines + commit) and `defines`/`references`/`calls` edges (`parsed` provenance). Apache-2.0,
  per-language indexers, edge-rows via `scip print --json` (the D17 bake-off winner). **Build-time
  bake-off obligation (D34/D36):** before committing, evaluate **codegraph** vs. a custom SCIP
  integration ("lean adopt codegraph", D34) — the producer is decided at BUILD, not asserted here.
- **LSP live** — the freshness complement for the working tree (refs/impls/call-hierarchy), tolerating
  the staleness SCIP's per-commit snapshot carries.
- **`code_anchor` edges are NOT a core-indexer output** — they bind a *manifest* `checkpoint` →
  `code_symbol`, and `checkpoint` is a UACP concept the core indexer cannot know (CF-D9). The core
  indexer emits only the **code-side floor** (`code_symbol` + `defines`/`references`/`calls`); the
  **UACP adapter** supplies the checkpoint side and emits `code_anchor` as a manifest-derived join
  (D44:912). Litmus: if the core indexer references `checkpoint`, the seam is violated.
- **tree-sitter** — a cheap change-detector deciding *what* to re-index per commit (not a graph source).

## Build discipline (design altitude; details to BUILD)

- **Truth = files; the index = a rebuildable projection** — watermarked on `repo_commit` + content
  hashes (D29 discipline). Stale → rebuild; crash mid-build → rebuild; truth never corrupts.
- **Per-commit + incremental** — re-index only the tree-sitter-flagged delta per commit, not the world.
- **External deps are external** — SCIP/LSP binaries are EXTERNAL dependencies (D36/D44); UACP owns the
  `code_anchor` + `code_symbol` *schema* and the projection, not the language indexers themselves.
- **The store is ours, not SCIP's own file** (D38) — SCIP's native SQLite is *the tool's* rebuildable
  artifact; the Code Engine's store ([01b](01b-store.md)) is a **re-derived, watermarked projection** of
  the indexer's output, never a second source of truth.

## What it is NOT

Not a governed writer (the index is a derived cache, not manifest state — [01-contract](01-contract.md)).
Not a diagnoser. Not language-complete on day one — SCIP covers the major-language core; grep/LSP cover
breadth; the `code_anchor` floor binds whatever SCIP resolves. Coverage gaps are a measured property, not
a silent one (report what is unindexed).
