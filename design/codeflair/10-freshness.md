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

> **If LSP (Serena/`uv`) is absent** ([12-delivery](12-delivery.md): `uv` is the user's responsibility),
> the **live-overlay path is skipped, not errored** — dirty files are returned **`stale`+flagged**, so the
> engine runs as a **two-zone** reconcile (clean / stale-flagged), not the three-zone one. Zone ② becomes
> a no-op, the orchestrator still *sees* the staleness. This is the documented degrade, not a hidden one.

## Worktrees — key the store per worktree; the watermark does the rest

git worktrees = one repo, N working trees at different branches/commits/dirty-states, sharing one `.git`.
A store built for worktree A (branch X) is *wrong* for worktree B (branch Y). Handling:

- **Per-worktree store.** The `.codeflair/` cache lives *in* (or is keyed by) the **worktree root** — each
  worktree gets its own watermarked graph reflecting *its* checkout + dirty state. Clean isolation. The
  cache dir is **gitignored** (same hygiene as `.worktrees/` and `.mcp.json` secrets).
- **The watermark makes it automatic.** A store from a different worktree/commit reads as **stale →
  rebuild the delta** — worktrees need no special logic beyond keying the store right; it's just another
  input to the freshness check.
- **Aligns with UACP's worktree-protocol** — worktrees nest under `$UACP_ROOT/.worktrees/` *so tooling
  (LSP/SCIP/the code plane) sees them*. Codeflair runs the indexer **in-worktree**, store **in-worktree**.
- **Deferred optimization:** worktrees share git objects, so the *committed* graph for a common commit is
  identical — one could share a committed base + per-worktree dirty overlay. Premature; per-worktree store
  is the simple correct v1.

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
