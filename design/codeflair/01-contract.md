---
type: analysis
title: Codeflair — Contract & Identity
description: The contract that lets the model stay small (expand, don't diagnose — with the structural/causal line drawn precisely), the division of labor, the independence property, the read-only/hypothesis posture, the v1 shape (a spike around the existing Oracle reranker, not a standalone service yet), and the identity grounded in D44's sanctioned cross-plane pattern.
tags: [codeflair, contract, identity, read-only, ddd]
timestamp: 2026-06-24
edges:
  - {dst: 00-overview, rel: realizes, provenance: asserted}
---

# Codeflair — Contract & Identity

## The contract (what makes a small model sufficient)

> **Codeflair expands; it does not diagnose.** The reasoning it does is *relevance judgment* — "is
> this node related to the seed?" — and *structural/coverage analysis* — "is this caller untested,
> is this symbol unanchored?" It does **not** do *causal or corrective reasoning* — "why did this
> break, and how do I fix it." It hands the orchestrator a focused subgraph; the expensive model
> reasons over it.

The structural/causal line matters and the council sharpened it: flagging a *missing test* or an
*orphan symbol* is **structural** (a graph property — present/absent), and Codeflair may do it.
Explaining *why* a co-change correlation is causal, or proposing the fix, is **causal/corrective** —
outside its contract, and structurally moot since Codeflair emits no manifest edge at all. Relation-finding is a **narrow-the-haystack** job, not a **solve-the-puzzle** job — which is
why a 4B-class model *may* suffice. (Whether it actually does, or whether a no-LLM baseline matches it,
is the open empirical question — see [05-benchmark](05-benchmark.md), Policy D.)

## Division of labor

| | **Codeflair (light)** | **Orchestrator (expensive)** |
|---|---|---|
| Job | gather + focus | reason + decide |
| Output | heatmap subgraph (relations, blast radius, gaps) | the diagnosis / the edit |
| Reasoning | relevance + structural only | causal / corrective |
| Re-derivable? | yes (deterministic evidence + replayable trace) | n/a |

A bonus property falls out: because Codeflair runs **separately from the orchestrator's own
reasoning**, its heatmap is an **independent** pass — the property memory flagged as the real prize of
a built-in light model (independence, not cost). Its value is *not* that it is cheap; it is that it is
*separate*.

## Posture: read-only, hypothesis only

Codeflair **writes nothing** and **asserts no manifest edge.** Its output is a *hypothesis* — a ranked
subgraph the orchestrator may use, ignore, or override. This dissolves the tension between an
LLM-in-the-loop and UACP's re-derivability spine:

- the **evidence** is deterministic (every SCIP/LSP/grep probe + result is logged),
- only the **search path** is stochastic, and it is captured as a **replayable trace**,
- the **output** is never a governed write, so there is no governed-writer and no self-attestation risk.

It behaves exactly like grep/SCIP themselves: a read-side lookup tool — just a smarter, reconciling one.

## v1 shape: a spike around Oracle, not a standalone service (yet)

The council's sharpest scope finding: most of the substrate already exists — **Oracle's Qwen3 reranker**
+ the **SCIP graph walk** + the **Manifest engine** relation graph. The genuine *new* delta is small:
(1) the **co-change probe** and (2) **iterating the reranker across hops with a beam.** So v1 is **not**
a new service with its own identity — it is a **spike**: a loop wrapped around the *existing* Oracle
reranker + Manifest-engine read-side projection + LSP/grep/co-change probes (SCIP and the cross-plane
`code_anchor` hop join only when the deferred code plane ships), built to measure whether the
iterated-beam + co-change delta beats a **no-LLM baseline** ([05](05-benchmark.md), Policy D). Codeflair **graduates** to a standalone, named service
only *after* the loop proves out. Building service-shaped infrastructure before that measurement is the
mistake this framing avoids (decision recorded in [07-decisions](07-decisions.md)).

## Identity (the graduation target) in UACP's architecture

When/if it graduates, Codeflair's slot is **already reserved and sanctioned** — D44 (`02-decisions.md:912`):

> *"Cross-plane is by edge (provenance / `code_anchor`) + a **query-time join in the calling skill** …
> never one engine reaching into another's storage."*

That is exactly Codeflair: a **calling skill / driver above the application ring** (where the
modular-architecture reference places drivers — they *call into* the ring, they are not in it) that
performs a read-only query-time join across the code plane (SCIP → the deferred code-graph store,
D27/D44) and the relation plane (the **Manifest engine**'s read-side projection over YAML, D43/D44). It
**owns no storage**,
so per the modular-architecture reference (`29-ddd-ca-reference.md`) it is **NOT an engine**; it blocks
nothing, so it is **not a gate**; it is not transition-bound, so it is **not a check**. It is a driver
that composes existing read APIs + a light-model adapter.

What it must never become: a fourth "engine" (it owns no plane), a diagnostician (see the contract), or
a writer of manifest edges (a separate, deferred, *gated* path — [06-open-questions](06-open-questions.md)).
