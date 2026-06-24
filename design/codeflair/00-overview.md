---
type: analysis
title: Codeflair — Overview
description: The mission (mechanize the manual grep·LSP·SCIP comprehension chain into one shot), the sibling framing (graph-engine = manifest plane, Codeflair = codespace plane), why the codespace needs a loop the manifest doesn't, the scale-only justification, and the Trustless evidence.
tags: [codeflair, code-plane, relation-finder, lookup, overview]
timestamp: 2026-06-24
edges: []
---

# Codeflair — Overview

## The problem in one sentence

To understand a change today — its blast radius, what it touches, where it is wrong — the
**orchestrator is the integration layer**: it runs grep, then a script, then LSP, reconciles the
results by hand, and repeats. The repo's own `CLAUDE.md` mandates exactly this "unified
grep·LSP·SCIP flow" as a **manual discipline** (there is even a hook nudging *lead with LSP, combine
with grep, reconcile, the suite decides*). Codeflair's thesis: **that reconciliation is a mechanism,
not a discipline.** One call should return the comprehended relations — blast radius, relations, and
gaps — in one shot.

This is the **comprehend** primitive of `comprehend → measure → serialize` turned into a mechanism
instead of a human-prompted chain of executions.

> **Non-goal (do not re-walk):** Codeflair does *search/evidence* expansion (iterating probe→prune to
> grow the evidence frontier) — **not** *query-string* expansion, which was built, measured, and
> reverted here as the wrong target on a strong-rerank stack. See [CF-D7](07-decisions.md).

## The sibling framing (this is the load-bearing idea)

Codeflair is **graph-engine's code-plane sibling**. Same idea — find the relations — different
substrate:

| | **graph-engine** | **Codeflair** |
|---|---|---|
| Plane | the **manifest** (proposals, plans, work_units) | the **codespace** (symbols, files, anchors) |
| Edges | serialized at **write-time**, typed | many are **not pre-serializable at scale** (co-change, relevance, cross-plane anchors) |
| Traversal | deterministic **FK-walk** | **discover** edges by probes, then **prune** |
| Why | small, DAG-ish; CTEs walk it trivially | large, dense, cyclic; the frontier explodes |

graph-engine's own thesis — *"a relation not serialized at write-time is one you agreed to reconstruct
later; RAG is the interest you pay on lossy serialization"* — **meets its limit at codespace scale.**
You cannot serialize every code relation up front, so Codeflair pays *some* interest: it leads with
the precise serialized edges (SCIP `defines`/`references`/`calls`) and uses a **light model only to
prune** the discovered frontier — never to reconstruct meaning wholesale. graph-engine's scope guard
already says *"code-plane deferred."* Codeflair is that deferred plane — though it proposes a *new
shape* for it (a read-only probe fan-out), not merely filling a reserved slot.

## Why this is a scale tool (and only a scale tool)

On a small codebase Codeflair **should not exist** — the orchestrator greps and reads everything, and
a relation-finder is pure overhead. It earns its keep only when the code graph + manifest history is
**too large to fit in the orchestrator's context** (the graph-engine substrate analysis names the
regime — *100k+ nodes, dense cyclic edges*, D11/D12). The real value is **context compression at scale**: reduce a 1M-node graph to a ~20-node
heatmap the expensive model *can* hold. At that scale, unbounded deterministic expansion blows up at
hop 2 — so **light-model pruning of the frontier is the core job, not a flavor.**

## The evidence is next door: Trustless

The sibling **Trustless** project is *why* lookup-over-the-codespace is the central problem (D12 cites
it): its code graph was file-level (too coarse to bind a task to the right symbol), and it built a
hybrid vector search (QMD), **measured it at ~42s/query, and retired it.** Coarse graph + slow naive
RAG = lookup that does not work. Codeflair is the answer to that exact failure: **precise probes +
iterative expansion + light-model pruning**, not one slow whole-document RAG pass. The 42s/query result
is the bar any Codeflair benchmark must beat (see [05-benchmark](05-benchmark.md)).

## What this bundle decides

- The **contract** that keeps the model small: expand, don't diagnose ([01-contract](01-contract.md)).
- The **probe set** and the cross-plane join that turns "find references" into "find relations"
  ([02-probes](02-probes.md)).
- The **expansion loop** and the swappable policy interface ([03-expansion-loop](03-expansion-loop.md)).
- The **outputs**: heatmap + evidence trail + gap flags + a replayable trace ([04-outputs](04-outputs.md)).
- The **bake-off** that picks the policy by measurement, not faith — incl. a no-LLM control ([05-benchmark](05-benchmark.md)).
- The **decisions + settled priors**, incl. the rejected query-string-expansion path ([07-decisions](07-decisions.md)).
- The **council review** that hardened this bundle ([08-council-review](08-council-review.md)).

It does **not** decide the implementation. Build-detail (model id, beam width, exact trace format) is
deferred to BUILD, where tests arbitrate — pre-resolving it in prose here would be over-serialization.
