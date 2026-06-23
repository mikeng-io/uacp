---
type: analysis
title: Composition — CMS is fractal (nested) and iterated (chained)
description: CMS composes on two axes. ITERATED (horizontal) — serialize(N) feeds comprehend(N+1); the lifecycle is CMS looped over time. FRACTAL (vertical) — CMS is applied at every grain, so a phase that plays one role in the macro-loop (e.g. verify = measure) is internally comprehend→measure→serialize. Applying it everywhere is a deliberate choice FOR COHERENCE, not a discovered recursion — which is why UACP runs on one discipline, not seven phase-logics.
tags: [primitive, composition, fractal, iterated, self-similar, lifecycle]
timestamp: 2026-06-24
edges:
  - {dst: 00-the-axiom, rel: extends, provenance: asserted}
---

# Composition — two axes

CMS composes on two axes. Applying it at *every* grain is a deliberate choice **for coherence** — not a claim that each layer independently turned out to be CMS. The payoff: the whole of UACP runs on one discipline rather than seven phase-logics.

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

- **One discipline at every grain — not seven phase-logics.** brainstorm/triage/propose/plan/execute/verify/resolve are not seven rule-sets; we *impose* CMS at each grain so they stay coherent — a design choice, not a discovered recursion. (This is the honest answer to "fractal is retrofitted": there is nothing to retrofit — coherence is engineered in, not found.) A large reduction in conceptual surface.
- **The conceptual loop is per-phase; the *enforcement* is at the gate.** Each phase conceptually runs comprehend→measure→serialize, but the kernel enforces the measure+serialize disciplines at the **phase-exit gate** (gate-ledger + graph_invariant), not as a checked internal recursion. So "fractal" is the design lens; "gate-shaped" is the enforcement reality — both true, named distinctly.
- **The disciplines are scale-invariant.** The same enforcing mechanisms hold at every grain: the *measure*-discipline = the Heartgate phase-exit gate (at phase scale) **and** a single fail-closed `validate`/lint call (at operation scale); the *serialize*-discipline = the entity-writer + watermark, whether committing a whole resolution or one `work_unit`.
- **The agent runs CMS at every grain.** A governed run is macro-CMS; each sub-step the agent takes is micro-CMS, with the same three disciplines. This is what the portable `uacp.md` instructs — comprehend → measure → serialize at *every* grain, not only at the lifecycle boundary.

## To expand
- The exact per-phase internal CMS triple (comprehend-input / measure-signal / serialize-artifact) for all 7 phases — the cross-walk.
- The base case: the finest grain where recursion stops (a single governed write = a CMS atom whose *measure* is the validate-on-write).
- Iterated × fractal interaction: a phase's serialize(N) feeds the next phase's comprehend, AND that phase is itself a nested loop.
