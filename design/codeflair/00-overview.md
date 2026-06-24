---
type: analysis
title: Codeflair — The Code Engine (Overview)
description: Codeflair is UACP's 4th engine — the codespace plane, end-to-end: it PRODUCES the code graph (SCIP indexing), STORES it, and QUERIES it (the relation-finder loop + heatmap). The mission (mechanize the manual grep·LSP·SCIP comprehension chain), the sibling framing, why it is an engine (it owns the code-graph store), the gap it closes (a producer for the declared-but-unproduced code_anchor), and scope.
tags: [codeflair, code-engine, code-plane, relation-finder, overview]
timestamp: 2026-06-24
edges: []
---

# Codeflair — The Code Engine (Overview)

## The problem in one sentence

To understand a change today — its blast radius, what it touches, where it is wrong — the
**orchestrator is the integration layer**: it runs grep, then a script, then LSP, reconciles the
results by hand, and repeats. `CLAUDE.md` mandates exactly this "unified grep·LSP·SCIP flow" as a
**manual discipline**. Codeflair's thesis: **that reconciliation is a mechanism, not a discipline** —
and the mechanism needs a substrate that does not yet exist, so Codeflair builds it.

This is the **comprehend** primitive of `comprehend → measure → serialize` made a mechanism, and it is
the [[uacp-graph-engine-serialization-initiative|graph engine]]'s **code-plane sibling**: graph-engine
serializes MANIFEST relations; Codeflair serializes CODESPACE relations.

## Codeflair is UACP's 4th engine (not just a lookup tool)

The first cut of this design scoped Codeflair as a *read-only lookup driver*. That was too narrow — and
it exposed a real gap: `code_anchor` / `code_symbol` are **declared edge types in the graph schema with
no producer** (no SCIP indexer exists; *"no code indexing exists today"*). graph-engine even flagged the
code plane as *"the real strain"* (D12) — then never built it. You cannot design the **consumer** (a
lookup) on top of a **producer** that nobody built.

So Codeflair is the whole **Code Engine** — UACP's 4th, alongside **State / Manifest / Oracle** — exactly
the shape D44 already names: *"Code engine (the future 4th) — build = SCIP per-commit (persisted) + LSP
live; query = symbol/reference lookup."* Three responsibilities, one bounded context (the codespace):

| | Node | Role |
|---|---|---|
| **Produce** | [01a-indexer](01a-indexer.md) | SCIP per-commit (persisted) + LSP live → `code_symbol` nodes + `code_anchor`/`calls`/`references` edges |
| **Store** | [01b-store](01b-store.md) | the persisted code graph (rebuildable projection; truth = files; watermarked) |
| **Query** | [02-probes](02-probes.md) → [05-benchmark](05-benchmark.md) | the relation-finder loop + heatmap, reading **its own** store |

Because it **owns the code-graph store**, it **is an engine** (it was *not* one only under the discarded
lookup-only scope — see [01-contract](01-contract.md) and [CF-D8](07-decisions.md)). The build-side
**writes** its index (a rebuildable projection, like graph_projection / LanceDB — not governed state);
the **query layer stays read-only** over that store, same pattern as the Manifest engine.

## Why this is a scale tool (and only a scale tool)

On a small codebase the orchestrator greps and reads everything — an engine is pure overhead. Codeflair
earns its keep only when the code graph is **too large to fit in the orchestrator's context** (the
graph-engine substrate analysis names the regime — *100k+ nodes, dense cyclic edges*, D11/D12). The real
value is **context compression at scale**: reduce a 1M-node graph to a ~20-node heatmap the expensive
model *can* hold.

## The evidence is next door: Trustless

Trustless is *why* lookup-over-the-codespace is the central problem (D12 cites it): its code graph was
file-level (too coarse), and its hybrid vector search (QMD) was **measured at ~42s/query and retired.**
Coarse graph + slow naive RAG = lookup that does not work. Codeflair is the answer: a **precise SCIP
index** (the producer Trustless lacked) + **iterative expansion + light-model pruning** — not one slow
whole-document RAG pass. 42s/query is the bar any Codeflair query must beat ([05-benchmark](05-benchmark.md)).

## Scope

It does **not** decide implementation (model id, beam width, index cadence, exact trace format) — that is
BUILD, where tests arbitrate. It does **not** diagnose, and the query layer writes no manifest edge.
Promoting a heatmap relation into a manifest edge is a separate, gated, deferred path
([06-open-questions](06-open-questions.md)).
