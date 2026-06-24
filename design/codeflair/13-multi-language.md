---
type: analysis
title: Codeflair — Multi-Language & Cross-Language Coherence
description: How N languages coexist in one store (per-language SCIP indexers, namespaced, fused — proven on Go+TS), and the honest finding on cross-language coherence — SCIP gives zero cross-language edges, but the real couplings (HTTP routes, CLI commands, events) are SHARED STRINGS that grep already catches language-agnostically, plus co-change and contracts. All deterministic. An LLM is a deferred, probably-unnecessary residual.
tags: [codeflair, multi-language, cross-language, deterministic, grep, co-change]
timestamp: 2026-06-24
edges:
  - {dst: 02-probes, rel: depends_on, provenance: asserted}
---

# Codeflair — Multi-Language & Cross-Language Coherence

## Multi-language coexistence (proven)

Each language has its own SCIP indexer (`scip-go`, `scip-typescript` (TS+JS), `scip-python`,
`rust-analyzer scip`, `scip-clang`, `scip-java`). They all emit the **same format**, and SCIP symbols are
**namespaced by scheme** (`scip-go …` vs `scip-typescript …`) → **no collision**. Codeflair runs the
right indexer per language and **fuses all outputs into one SQLite** (per-language precise subgraphs).

**Empirically proven** (Trustless spike): Go (66,816 occ) + TS (1,258 occ) fused into one store,
namespaced, zero collisions, both query sub-millisecond. A `lang` column (or the scheme prefix) tags each
node. *Within* a language, edges are precise (SCIP).

## Cross-language coherence — the honest finding: mostly a DETERMINISTIC problem

**SCIP gives zero cross-language edges** (proven: the fusion had 0). A Go service calling a TS service has
**no compile-time symbol relationship** — no indexer sees across the wire. The recursive CTE stops at the
language boundary. So cross-language links must be *constructed* — but the real ones are deterministic:

| Coupling | Real-world form | How Codeflair catches it | Confidence |
|---|---|---|---|
| HTTP / gRPC | shared route `/api/accounts` | **grep** — language-agnostic; finds it in Go *and* TS | deterministic |
| CLI / subprocess | shared command string | **grep** | deterministic |
| events / queues | shared event name `"user.created"` | **grep** (+ normalization) | deterministic |
| typed contract | proto / OpenAPI / GraphQL codegen | **parse the IDL** → `Account` → Go struct + TS iface | near-deterministic |
| temporal | cross-lang files that change together | **co-change** (git is language-blind) | inferred |

**The key insight: `grep` is already cross-language.** The common couplings are *shared strings* (routes,
commands, events), which grep finds across languages with **zero symbol resolution and zero LLM.** Add
co-change (language-blind) and contract parsing, and nearly all real cross-language blast radius is
covered — **deterministically.**

## Why the LLM is deferred here (CF-D13)

The only residual an LLM would add: entities coupled **by meaning** with **no shared string, no contract,
and no co-change** (e.g. Go `Account` ↔ TS `UserProfile`). The plausible near-misses — normalized shared
constants (`USER_CREATED` vs `user.created`) and convention-divergent codegen names (`GetAccount` vs
`getAccount`) — are mostly caught by **normalized grep + contract parsing**, *deterministically*. What's
left after that is genuinely **weak by definition**: if nothing links two symbols textually, contractually,
or temporally, the coupling is probably not blast-radius-relevant.
So a semantic/embedding matcher is a **marginal, probably-unnecessary residual**, explicitly **deferred**
(CF-D13). Cross-language coherence ships **deterministic** (grep + co-change + contracts); revisit an LLM
*only if* real usage proves the residual matters. Cross-language edges are tagged `inferred` and surfaced
as hypotheses, never asserted.
