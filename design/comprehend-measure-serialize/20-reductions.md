---
type: analysis
title: Reductions — every capability decomposes to comprehend → measure → serialize
description: The primitivity evidence — worked reductions showing that verify, search, plan, reason, tool-call, memory, and execution are COMPOSITIONS of the CMS cycle, not primitives. If all reduce without forcing, CMS is the atom.
tags: [primitive, reductions, decomposition, primitivity]
timestamp: 2026-06-21
edges:
  - {dst: 00-the-axiom, rel: realizes, provenance: asserted}
---

# Reductions — capabilities are compositions

The case that CMS ([00-the-axiom](00-the-axiom.md)) is a *primitive* rests on this: the things we normally call "operations" each **decompose** to it, cleanly.

| Capability | comprehend | measure | serialize |
|---|---|---|---|
| **verify-JWT** | read token + public key | check signature / exp / aud | verified \| reject |
| **search** | parse query | rank / score | result set |
| **plan** | the goal | cost / dependencies | the plan |
| **reason** | the facts | infer / compare | conclusion |
| **tool-call** | resolve tool + args from intent | admissible? which tool? | invoke + record result |
| **memory write** | the candidate fact in context | importance / novelty / conflict | durable \| session \| drop |
| **execute** | plan + code reality | satisfy frozen criteria | checkpoints |

The pattern: **`verify` is not an operation — it IS `comprehend + measure + serialize`.** Same for the rest.

## The standard this sets

A reduction "counts" only if it is **natural** — no forcing, no relabeling to fit. A capability that needs a contrived mapping is a signal the primitive is incomplete (or that the capability genuinely escapes it — a counterexample, which is [05](30-validation-matrix.md)'s job to surface).

## To expand
- Harder reductions: human approval, council review, a rollback, an escalation.
- The composition algebra: how molecules build from the atom (sequential CMS, nested CMS, looped CMS = the verification convergence loop).
- Where a reduction is *lossy* (if any) — the honest boundary of the claim.
