---
type: analysis
title: Codeflair — Outputs (Heatmap, Gaps, Trace)
description: What a Codeflair run returns — a ranked heatmap subgraph, the evidence trail, first-class gap flags, and a watermarked replayable search trace — and how the trace reconciles a stochastic loop with UACP's re-derivability spine.
tags: [codeflair, outputs, heatmap, gaps, trace, determinism]
timestamp: 2026-06-24
edges:
  - {dst: 03-expansion-loop, rel: consumes, provenance: asserted}
---

# Codeflair — Outputs

A run returns one object: a **read-only heatmap**, pre-governance input for the orchestrator. Four parts.

## 1. The heatmap subgraph

A ranked subgraph spanning **both planes** — code-plane nodes (symbols/files) and the relation-plane
manifest nodes they anchor to. Each node carries a **relevance weight** (the "heat"), so the
orchestrator can read it as *here is the blast radius, hottest first* without re-ranking. This is the
context-compression payload: a few dozen weighted nodes standing in for a million-node graph.

## 2. The evidence trail

For every node: **which probe found it, from which parent, with what provenance** (parsed / derived /
inferred / asserted). This is what lets the orchestrator trust or discount a node — a `parsed` SCIP
edge is firm; an `inferred` co-change edge is a lead. Reconciliation outcomes from
[02](02-probes.md) (agree / grep-only / unreconciled) live here, not silently dropped.

## 3. Gap flags (a first-class output, not a side effect)

The mission was "get the **gap** and the relations." A gap is a **hole in the relation graph the seed
exposes** — surfaced explicitly, not inferred by the reader:

- a caller/dependent in the blast radius with **no test** covering it,
- a symbol with **no manifest anchor** (code that no intent governs),
- a **cross-plane orphan** — a manifest node whose anchored code is gone, or code whose governing
  manifest node was never written.

Codeflair returns *what is connected* **and** *where the connection is thin or missing* relative to
the seed. The gap set is often the most actionable part of the heatmap. Gaps stay a first-class
*output*, but they are *absences* with no clean ground truth, so they are scored on a separate
best-effort label set — **not** folded into the primary recall@K ([CF-D6](07-decisions.md),
[05](05-benchmark.md)).

## 4. The search trace (this is the re-derivability reconciliation)

An append-only log of every hop: frontier in, probes run, candidates out, scores, beam kept. The trace
makes a stochastic loop honest:

- the **evidence** is fully deterministic — re-running the logged probe sequence reproduces it exactly;
- the trace is **watermarked** on `repo_commit` + content hashes (the determinism discipline: zero out
  timestamps; key on commit + content) so a stale trace is detectable and a run is cache-keyable;
- the **search path** need not be bit-identical across re-runs (the model is stochastic), but it is
  **replayable from the trace** and auditable. "Replayable + watermarked," not "bit-identical," is the
  re-derivability bar a hypothesis-only lookup tool must clear — and it clears it.

## What the output is *not*

It is not a diagnosis, not a fix, not a proposed manifest edge, and not a governed write. The
orchestrator consumes the heatmap and does the causal/corrective reasoning itself
([01](01-contract.md)). Promoting any heatmap relation into a real manifest edge is a separate, gated,
deferred path ([06](06-open-questions.md)).
