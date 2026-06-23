---
type: analysis
title: Composition — CMS is fractal (nested) and iterated (chained)
description: The primitive composes on two axes. ITERATED (horizontal) — serialize(N) feeds comprehend(N+1); the lifecycle is CMS looped over time. FRACTAL (vertical) — every verb, at finer grain, is itself a full CMS loop; a phase that plays one role in the macro-loop (e.g. verify = measure) is internally comprehend→measure→serialize. The disciplines are scale-invariant, which is why UACP is one primitive recursed, not seven phase-logics.
tags: [primitive, composition, fractal, iterated, self-similar, lifecycle]
timestamp: 2026-06-24
edges:
  - {dst: 00-the-axiom, rel: extends, provenance: asserted}
---

# Composition — two axes

CMS is not a single flat loop. It composes on two axes — and that composition is what lets the whole of UACP be **one** primitive rather than seven phase-logics.

## Axis 1 — ITERATED (horizontal): the loop chains over time

`serialize(N) → comprehend(N+1)`. The durable state one cycle commits is the input the next cycle perceives. The **lifecycle is CMS iterated**: TRIAGE → PROPOSE → PLAN → EXECUTE → VERIFY → RESOLVE, each phase's serialized artifact becoming the next phase's comprehend-input. (This axis is the "cycle iterated" noted in [31-instantiations](31-instantiations.md).)

## Axis 2 — FRACTAL (vertical): every verb is itself a CMS loop

Zoom into any verb and you find comprehend → measure → serialize *again*. A phase that plays **one role** in the macro-loop is, at finer grain, a **full loop**:

- **VERIFY** is the lifecycle's *measure* role — "did EXECUTE do what PLAN intended?" But verify, examined internally, is a complete CMS loop:
  - **comprehend** — load the execution checkpoints + PIV obligations into a model;
  - **measure** — judge each obligation (pass / warn / block / contradicted) — deterministic, fail-closed, bound to the evidence (the graph gate's assessment + contradiction checks);
  - **serialize** — write the `piv_assessment` / `verification_package` as typed, registered, provenanced state (the entity-writer).
- The same recursion holds for every phase, every gate, every governed operation. A **gate is the *measure*** of its phase's loop; the **entity-writer is the *serialize*** of every loop.

So: **a verb at scale N is a CMS loop at scale N+1.** The primitive is self-similar across scales — lifecycle, phase, gate, operation.

## Why this matters (the load-bearing consequence)

- **One primitive, recursed — not seven phase-logics.** brainstorm/triage/propose/plan/execute/verify/resolve are not seven rule-sets; they are CMS at one zoom level, each containing CMS at the next. A large reduction in conceptual surface.
- **The disciplines are scale-invariant.** The same enforcing mechanisms hold at every grain: the *measure*-discipline = the Heartgate phase-exit gate (at phase scale) **and** a single fail-closed `validate`/lint call (at operation scale); the *serialize*-discipline = the entity-writer + watermark, whether committing a whole resolution or one `work_unit`.
- **The agent runs CMS at every grain.** A governed run is macro-CMS; each sub-step the agent takes is micro-CMS, with the same three disciplines. This is what the portable `uacp.md` instructs — comprehend → measure → serialize at *every* grain, not only at the lifecycle boundary.

## To expand
- The exact per-phase internal CMS triple (comprehend-input / measure-signal / serialize-artifact) for all 7 phases — the cross-walk.
- The base case: the finest grain where recursion stops (a single governed write = a CMS atom whose *measure* is the validate-on-write).
- Iterated × fractal interaction: a phase's serialize(N) feeds the next phase's comprehend, AND that phase is itself a nested loop.
