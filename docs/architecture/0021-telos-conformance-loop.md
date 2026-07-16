---
type: adr
title: The telos — UACP is a conformance loop for semantic work
description: Encode the purpose UACP serves — reduce the long-run, time-asymmetric friction of cooperation on semantic work — as primary, and record that CMS, gates, the lifecycle, and the memory substrate derive from it. Amends (does not supersede) ADR-0018 by supplying the why it left unstated; adds recursive critique with an effort-bounding critique base case, the grain base case (= the governed write), and the memory-substrate reframe; reaffirms ADR-0018's measure naming.
tags: [telos, conformance-loop, purpose, friction, recursive-critique, memory-substrate, measure, issue-98]
timestamp: 2026-07-17
status: accepted
---

# The telos — UACP is a conformance loop for semantic work

## Metadata

- **Status**: accepted — **amends [ADR-0018](0018-cms-semantic-thinking-principle.md)** (supplies the purpose CMS serves; does not supersede or replace it). Per `docs/INDEX.md` ADR immutability, ADR-0018 is NOT edited in place — this successor is the sole record of the amendment.
- **Date**: 2026-07-17
- **Decision Makers**: UACP maintainer
- **Consulted**: a 3-way review panel on the telos design bundle (2× adversarial/completeness + a cross-provider reviewer), findings folded into bundle v2
- **Informed**: all agents (the purpose is now stated in `AGENTS.md`, `UACP.md`, and `docs/policy/first-principles.md`)
- **Related**: the design bundle [`design/telos/`](../../design/telos/); [ADR-0018](0018-cms-semantic-thinking-principle.md) (CMS as the discipline for semantic thinking); the CMS bundle [`design/comprehend-measure-serialize/`](../../design/comprehend-measure-serialize/)

## Context and Problem Statement

ADR-0018 ratified CMS (comprehend → measure → serialize) as UACP's discipline for semantic thinking, and reclassified it from an axiom to a **chosen coherence discipline**. But a chosen discipline logically requires the thing it was chosen *for* — a purpose — and that was never encoded. The #98 audit found the consequences: gates checked the *shape* of work, not whether it served any end; "coherence is the product" stood with no stated reason the product was worth its price; and downstream artifacts (authority chain, first principles) had drifted or dangled because nothing anchored them. Without the purpose written down, no one can judge whether a governance step earns its cost.

## Decision Drivers

- Encode the purpose as primary, so CMS / gates / lifecycle / substrate are legible as *means*, not free-standing machinery.
- Keep the framework honest: bound what is claimed (effort vs correctness), and never let a self-graded escape hatch strip governance.
- Do not reopen settled decisions — reaffirm ADR-0018's `measure` naming explicitly so it does not silently drift a third time.

## Decision Outcome

Adopt the telos as UACP's primary statement, with CMS derived from it:

1. **The telos is primary.** UACP exists to **reduce the long-run friction of cooperation** on work done by *semantic* (non-deterministic) actors. Friction is **time-asymmetric**: governance *adds* it at the point of interaction and *removes* it over the pipeline's lifetime (later work runs on rails — not re-derived, not re-litigated, not silently drifting). The telos is not "less friction"; it is "invest bounded up-front friction where it is repaid over the horizon of cooperation, net-positive."
2. **CMS / gates / lifecycle / substrate derive from it.** CMS is the conformance loop instantiated at a single grain; gates are the external-witness requirement made mechanical; the lifecycle is the loop across phases; the memory substrate is the loop across runs. **Coherence remains the product** these layers manufacture (ADR-0018); the telos is why the product is worth its price.
3. **The mechanism is a conformance loop, forced by the semantic differentia.** The governed atom is *does the realized reality match the declared intent?* It takes loop form because the executor is semantic — it can neither infer the spec (intent must be **externally declared**) nor certify its own pass (verification must be **externally witnessed**). The defining commitment is **refusal-to-drift**: the binding between the declared and witnessed faces is a governed primitive, checked at every transition.
4. **Recursive critique is the third leg.** The witness is *also* a fallible semantic actor, so no evaluation is final by fiat; each is open to critique until a declared **critique base case** is reached (a deterministic check, an *independent* fixpoint, a serialized human verdict, or an exhausted friction budget). The base case **bounds EFFORT, not correctness** — it guarantees the regress halts, not that it halts at truth — and every termination is made **witness-side** and serialized, never by the actor being governed.
5. **Two base cases, two recursions.** The **grain base case** = the governed write: CMS applies down to and stops at the smallest serialized act; below it there is no sub-grain to make conform. (Distinct from the critique base case of driver 4.)
6. **Memory → memory substrate.** UACP does not provide memory; the loop leaves behind typed, provenanced, serialized residue run over run — the **memory substrate**, the foundation memory is *built on*. Memory-as-generalization grows on it, outside the atom, and is honestly declared so.
7. **`measure` naming REAFFIRMED.** A v1 telos draft re-proposed `measure → evaluate` on descriptive grounds; review caught that this re-opened ADR-0018's ratified decision on the exact grounds already rejected (CMS is normative, not descriptive; the LLM's failure mode is premature deciding; the injected word is the intervention). **Ruling (mike, 2026-07-17): the name `measure` stays.** Recorded here so the question does not silently reopen.

## Consequences

- **The purpose is now measurable-in-principle.** A change to any layer is legitimate only insofar as it improves the long-run friction trade — the amortization test the friction budget encodes (witness-side, serialized, critiquable; removing a guardrail needs a serialized evidence case, not doctrine alone).
- **Honest limits are named.** The conformance atom cleanly unifies the PROPOSE → PLAN → EXECUTE → VERIFY → RESOLVE spine; TRIAGE, BRAINSTORM, and priority/authority overrides sit *upstream* of it, and memory-as-generalization sits *outside* it. The framework does not force-fit everything into one metaphor.
- **Deferred to the #98 build's EXECUTE (not this ADR):** the typed human-verdict shape, the `uacp.context_model` artifact + the cross-actor consumption rule, per-gate deterministic-vs-semantic labeling, and the `UACP.md` ↔ bundle sync check. See [`design/telos/50-net-fixes-and-propagation.md`](../../design/telos/50-net-fixes-and-propagation.md).

Canonical targets: `AGENTS.md` (Core Principle section), `UACP.md`, `docs/policy/first-principles.md` (the new principle) + `docs/policy/constitution.md` (authority-chain deferral + re-pointed derivations), `docs/INDEX.md` (read order), `design/telos/`, `design/comprehend-measure-serialize/` (reconciliation edits).
