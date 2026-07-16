---
type: analysis
title: The conformance loop — the semantic differentia, the atom, and its honest limits
description: The HEADLINE is the semantic differentia — the executor can neither infer the spec nor certify its own pass, so declaration and witnessing must be EXTERNALIZED. The governed atom is CONFORMANCE (realize-vs-declared). SDD and TDD are two INDEPENDENTLY-OWNED faces whose BINDING UACP governs (independence is what makes the witness meaningful — the faces are not collapsed). Honest limits — TRIAGE/BRAINSTORM/priority sit upstream of the atom; memory-as-generalization grows on the substrate outside it.
tags: [conformance, atom, sdd, tdd, semantic-executor, differentia, independence, honest-limits]
timestamp: 2026-07-16
edges:
  - {dst: 00-telos, rel: depends_on, provenance: derived}
---

# The conformance loop

## The headline: the semantic differentia
Everything in UACP follows from one fact: **the executor is semantic** (non-deterministic), and
that single fact forces two externalizations:

- it **cannot be trusted to infer the spec** → intent must be **externally declared**
  (PROPOSE / PLAN exist for exactly this);
- it **cannot certify its own pass** → verification must be **externally witnessed**
  (gates / councils / codeflair; the "no self-attesting closure" invariant).

This differentia — not the loop metaphor — is what distinguishes UACP from ordinary CI/CD.
A CI system also refuses drift, but it *trusts the machine* running the checks. UACP cannot
trust its actor, so declaration and witnessing must both live *outside* him. The loop shape is
the consequence, not the thesis.

## The atom
The governed unit is **conformance**: *does the realized reality match the declared intent?*

- The **declared** side (intent / design / spec — the "SDD" face) and the **witnessed** side
  (evidence / test — the "TDD" face) are two faces of one governed relation.
- The faces are **independently owned** — authored as separate acts, at separate times, ideally
  by separate actors — and that independence is **load-bearing**: a witness that is not
  independent of the declaration cannot witness it (20 leans entirely on this). UACP does not
  *merge* the faces; it **governs the binding between them** and forbids the binding to decay.
- The defining commitment is **refusal-to-drift**: in ordinary software the spec-doc and the
  tests are separate artifacts owned by separate phases, and they rot apart. UACP makes the
  binding a governed primitive, checked at the membrane on every transition.

This is why UACP resists the "SDD + TDD" pair-framing as a *definition*: the pair names the two
faces but misses the governed thing, which is the **binding**. (And it is why "one atom" must
not be over-read as "one artifact" — the relation requires its two independent relata.)

## Why a loop, not two documents
A relation that must stay true **across time and across runs**, enforced against a fallible
actor, cannot live in a static document — a document cannot re-check itself at each transition
or carry the binding into the next run. It must be a **running loop**. That is the reason UACP
had to become a *lifecycle*, not a pair of templates.

Genus, stated modestly: a conformance loop is *shaped like* a control loop — declared intent as
reference, witnessed evidence as sensor, drift as the error, rework as the correction — but the
analogy must not over-borrow: the "error signal" here is **judged, not measured** (30), and the
reference itself is a fallible, evolving artifact. No convergence guarantee is implied; the
loop earns trust per-cycle from its witnesses, not from control theory.

`determinism : machines :: conformance-loop-with-external-witness : semantic agents.`

## Honest limits (what the atom does NOT cover)
The atom unifies the **PROPOSE → PLAN → EXECUTE → VERIFY → RESOLVE spine** cleanly. It does
not, and should not pretend to, absorb:

- **TRIAGE** — scope calibration *sets the reference*; there is no "declared" yet to conform
  to. Upstream of the atom.
- **BRAINSTORM** — definitionally pre-governance exploration. Outside the atom.
- **Priority / authority / decision-log overrides** — choices about *what should be governed
  at all*. Upstream of the atom.
- **Memory-as-generalization** — lessons, judgments, recall built *on* the substrate (00). The
  loop produces the substrate; what grows on it is not re-checkable realize-vs-declared
  material and is not claimed by the atom.

Declaring these limits is part of the telos's honesty: a bedrock that force-fits everything
into one metaphor invites exactly the over-claiming this framework exists to prevent.
