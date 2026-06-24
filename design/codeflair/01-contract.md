---
type: analysis
title: Codeflair — Contract & Engine Identity
description: Codeflair IS UACP's 4th engine (it owns the code-graph store); the build-side writes a rebuildable index (not governed state), the query layer stays read-only/hypothesis-only over that store. The "expand, don't diagnose" contract, the division of labor, and the deliberate reversal of the first cut's "not an engine" framing.
tags: [codeflair, contract, identity, engine, ddd]
timestamp: 2026-06-24
edges:
  - {dst: 00-overview, rel: realizes, provenance: asserted}
---

# Codeflair — Contract & Engine Identity

## Identity: the 4th engine (corrected from the first cut)

The first cut called Codeflair "a read-only driver, **not** an engine." Under the **all-in-one Code
Engine** scope that is reversed, deliberately ([CF-D8](07-decisions.md)):

- An **engine** = the cohesive module that **owns one plane's persistence** (per `29-ddd-ca-reference.md`:
  *"Storage is touched only by engines — one per plane (State / Manifest / Oracle now, Code later)"*).
- Codeflair **owns the code-graph store** ([01b-store](01b-store.md)) — the SCIP index it produces. So it
  **is** the **Code engine**, UACP's 4th, exactly the slot `29-ddd-ca-reference.md` and D44 reserve.
- The council's "not an engine" was **correct for the discarded lookup-only scope** (a pure reader owns
  no storage). Owning the index makes it an engine. No contradiction — a scope change.
- **Standalone vs embedded (CF-D9, [09-abstraction](09-abstraction.md)):** it is an engine that owns its
  store in *both* modes. Standalone (no UACP) it is simply a code-intelligence engine. The
  *"calling skill above the UACP ring"* framing + the D44:912 cross-plane join below are the **UACP-
  embedded** identity only — supplied by the adapter, not the core.

Two halves, one bounded context:

| | Build-side ([01a](01a-indexer.md)/[01b](01b-store.md)) | Query-side ([02](02-probes.md)–[05](05-benchmark.md)) |
|---|---|---|
| Writes? | **yes** — persists the index | **no** — read-only |
| What | SCIP/LSP → `code_symbol`/`code_anchor` → store | the relation-finder loop → heatmap |
| Governed? | **no** — a rebuildable projection (truth = files; watermarked); the precedent is Oracle's persisted LanceDB index (D44) | n/a |

So write-scope is precise: the **query layer** writes nothing and asserts no manifest edge; the
**build-side** writes only its own rebuildable index — a derived cache, not governed manifest state
(D29/D44), placed **outside** `.uacp/`'s governed roots so Guardian's path rules do not hard-block it
(see [01b-store](01b-store.md)). Cross-plane reads remain a *query-time join in the calling skill*
(D44:912).

## The query contract (what makes a small model sufficient)

> **The query layer expands; it does not diagnose.** Its reasoning is *relevance judgment* — "is this
> node related to the seed?" — and *structural/coverage analysis* — "is this caller untested, this symbol
> unanchored?" It does **not** do *causal/corrective* reasoning — outside its contract, and structurally
> moot since the query layer emits no manifest edge.

Relation-finding is a **narrow-the-haystack** job, not a **solve-the-puzzle** job, so a 4B-class model
*may* suffice — or a no-LLM baseline may match it (Policy D, [05](05-benchmark.md)). The expensive
orchestrator does the causal reasoning on the focused heatmap.

## Division of labor

| | **Codeflair query (light)** | **Orchestrator (expensive)** |
|---|---|---|
| Job | gather + focus | reason + decide |
| Output | heatmap (relations, blast radius, gaps) | the diagnosis / the edit |
| Reasoning | relevance + structural only | causal / corrective |

Its value is **independence** (a pass separate from the orchestrator's own reasoning), not cost — the
property memory flagged as the real prize of a built-in light model.

## Posture of the query layer: read-only, hypothesis only

The query output is a *hypothesis* — a ranked subgraph the orchestrator may use, ignore, or override.
This keeps the LLM-in-the-loop honest against UACP's re-derivability spine: the **evidence** is
deterministic (every probe + result logged), only the **search path** is stochastic (captured as a
replayable trace), and the query writes no governed state. What it must never become: a diagnostician, or
a writer of manifest edges (a separate, deferred, *gated* path — [06](06-open-questions.md)).
