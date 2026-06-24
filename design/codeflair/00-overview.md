---
type: analysis
title: Codeflair — The Code Engine (Overview)
description: Codeflair is a STANDALONE code-intelligence engine (runs on any git repo, zero UACP, CF-D9); embedded in UACP it serves as the 4th engine (the codespace plane). It PRODUCES the code graph (SCIP indexing), STORES it, and QUERIES it (the relation-finder loop + heatmap). The mission (mechanize the manual grep·LSP·SCIP comprehension chain), the standalone/adapter split, why it is an engine (it owns the code-graph store), the gap it closes (a producer for the declared-but-unproduced code_anchor), and scope.
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

## Codeflair is a standalone code-intelligence engine (UACP is an adapter)

**Codeflair's core does not depend on UACP.** It is a standalone code-intelligence engine — SCIP/LSP/grep/
co-change probes + a code-graph store + the expansion loop + the heatmap — that runs on **any git repo
with zero UACP** (CF-D9, [09-abstraction](09-abstraction.md)). Dropped into a bare repo it still answers
blast-radius / relations / gaps; you lose only the cross-plane "what governs this code" half.

**Embedded in UACP, the same engine serves as the 4th engine** (the code plane, alongside **State /
Manifest / Oracle**) — exactly the shape **D44:906** names: *"Code engine (the future 4th) — build = SCIP
per-commit (persisted) + LSP live; query = symbol/reference lookup."* (The cross-plane *join* is the
separate **D44:912** bullet.) UACP plugs in via a thin **adapter**:
the manifest-graph probe + the `code_anchor` cross-plane join + the governed-writer/Guardian wrapper.

The first cut scoped Codeflair as a *read-only lookup driver* — too narrow, and it exposed a real gap:
`code_anchor` / `code_symbol` are **declared edge types with no producer** (*"no code indexing exists
today"*); graph-engine flagged the code plane as *"the real strain"* (D12) then never built it. You can't
design the **consumer** on a **producer** nobody built. So Codeflair owns the whole pipeline — three
responsibilities, one bounded context (the codespace):

| | Node | Role |
|---|---|---|
| **Produce** | [01a-indexer](01a-indexer.md) | SCIP per-commit (persisted) + LSP live → `code_symbol` nodes + `defines`/`references`/`calls` edges (`code_anchor` is adapter-side, [01a](01a-indexer.md)) |
| **Store** | [01b-store](01b-store.md) | the persisted code graph (rebuildable projection; truth = files; watermarked) |
| **Query** | [02-probes](02-probes.md) → [05-benchmark](05-benchmark.md) | the relation-finder loop + heatmap, reading **its own** store |

Because it **owns the code-graph store**, it **is an engine** (it was *not* one only under the discarded
lookup-only scope — see [01-contract](01-contract.md) and [CF-D8](07-decisions.md)). The build-side
**writes** its index (a rebuildable projection — the precedent is Oracle's persisted LanceDB index, D44 —
not governed state; standalone it writes to a normal cache dir, and under UACP, outside `.uacp/`'s
governed roots); the **query layer stays read-only**
over that store.

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
index** (the producer Trustless lacked) + **iterative expansion + deterministic scoring** — not one slow
whole-document RAG pass. 42s/query is the bar any Codeflair query must beat ([05-benchmark](05-benchmark.md)).

## The landing: Codeflair is a DETERMINISTIC engine (no LLM)

The design's conclusion (CF-D11/D13): the engine is **deterministic, core and cross-language.** Blast
radius is transitive closure; relevance is a scoring function; cross-language links are grep/contract/
co-change. **No LLM** — semantics lives in the orchestrator, not Codeflair. The LLM is a deferred,
probably-unnecessary residual.

**Proven on Trustless (spike, 2026-06-24):** scip-go indexed the repo in **4.1s**; ingest → SQLite **0.3s**;
blast-radius query **0.1–0.2 ms** and *correct* (`Pool#Conn` → the right dependent symbols);
**multi-language fusion** (Go + TS, one store, 0 collisions, 0 cross-language symbol edges, as predicted).
~`200,000×` under the 42s/query bar — with zero LLM. The operational layers (freshness/SCIP⊕LSP reconcile,
co-change, grep, heatmap ranking, recall@K) remain to build/test.

Full operational detail: [10-freshness](10-freshness.md) · [11-substrate](11-substrate.md) ·
[12-delivery](12-delivery.md) · [13-multi-language](13-multi-language.md).

## Scope

It does **not** decide implementation (model id, beam width, index cadence, exact trace format) — that is
BUILD, where tests arbitrate. It does **not** diagnose, and the query layer writes no manifest edge.
Promoting a heatmap relation into a manifest edge is a separate, gated, deferred path
([06-open-questions](06-open-questions.md)).
