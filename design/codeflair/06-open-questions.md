---
type: analysis
title: Codeflair — Open Questions & Deferred Paths
description: The decisions this brainstorm deliberately left open — model selection, seed modalities, the CTE-strain-at-scale watch-trigger, eval labeling ownership, reuse vs. separation from the Oracle stack — and the two explicitly deferred capabilities (auto-trigger, edge-promotion).
tags: [codeflair, open-questions, deferred, watch-trigger]
timestamp: 2026-06-24
edges:
  - {dst: 05-benchmark, rel: relates_to, provenance: asserted}
---

# Codeflair — Open Questions & Deferred Paths

## Open (resolve before / during BUILD)

1. **Model selection.** Memory's prior leans Qwen3-4B over MiniCPM for edge work. Confirm against the
   `score`/`prune` workload; it must be cheap enough to call every hop and good enough at relevance
   judgment. Settled by the benchmark, not by argument.
2. **Seed modalities for v1.** The seed can be a symbol, a diff, or an NL incident. Symbol/diff is the
   primary mechanizes-the-manual-chain case; NL incident needs a bootstrap hit (grep + code-fuzzy)
   before the loop starts. Decide whether v1 ships symbol/diff only or includes NL bootstrap.
3. **CTE-strain watch-trigger.** D12 set a reconsideration trigger: a native graph engine earns its
   dependency only if a *measured* deep-multi-hop wall appears on SQLite at real code-graph scale.
   **Codeflair is precisely the workload that probes that wall.** Its benchmark may be the evidence that
   fires (or fails to fire) that trigger — feed the result back to graph-engine D12 (and D44).
4. **Eval labeling ownership (now a build-gating prerequisite).** Per [CF-D5](07-decisions.md) the
   20-pair smoke set + inter-labeler-agreement check gates the build; the open part is *naming the
   owner* who produces it ([05](05-benchmark.md)).
5. **When to extract a standalone service.** [CF-D4](07-decisions.md) decided v1 is a spike *around*
   the existing Oracle reranker + SCIP; the open part is the *graduation trigger* — what bake-off
   result justifies extracting a standalone Codeflair service with its own identity, vs. leaving it a
   loop over Oracle. Keep the retrieval-plane boundary clean either way.
6. **Sanction the build path (governance prerequisite).** The indexer writes the code-graph store
   ([01b-store](01b-store.md)). Before it runs under governance, the build path must be registered as a
   **self-attesting engine operation** and the store path fixed **outside** `.uacp/`'s governed roots —
   else Guardian's path rules block it. Decide the exact store location + the registration mechanism
   (a new protected category / self-attesting tool) at BUILD.

## Deferred (named, not designed here)

- **Auto-trigger surface.** v1 is pull-only (called as a tool). A later increment could let an event
  (incident arriving, failing run) pre-warm a heatmap before the orchestrator asks. Deferred — adds a
  trigger surface and a freshness/cost policy.
- **Edge-promotion.** v1 emits hypotheses only. A later, **gated** path could let a confirmed heatmap
  relation be promoted into a real manifest edge via `uacp_entity_write`, behind a confirmation gate so
  it never self-attests. This is where Codeflair would let the graph *learn* correlations over time —
  but it is a separate design, not v1, and must not leak into the read-only service.

## The one-line scope guard

If a proposed feature makes Codeflair **diagnose**, **write governed state / manifest edges**, or
**exist on a small codebase**, it is out of scope. (The build-side *does* write its own rebuildable
index — a derived cache, not governed state; see [01b-store](01b-store.md).) The query layer expands the
codespace into a heatmap, at scale, read-only — nothing more.
