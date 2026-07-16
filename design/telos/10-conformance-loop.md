---
type: analysis
title: The conformance loop — the atom, its two faces, and the semantic differentia
description: The governed atom is CONFORMANCE (realize-vs-declared). SDD (the declared side) and TDD (the witnessed side) are the two FACES of one atom, not two artifacts; UACP governs the BINDING between them and refuses to let them drift. It must be a running loop, not two static documents, because the executor is SEMANTIC — so the spec cannot be inferred (must be externally declared) and the pass cannot be self-certified (must be externally witnessed).
tags: [conformance, atom, sdd, tdd, refusal-to-drift, semantic-executor, differentia]
timestamp: 2026-07-16
edges:
  - {dst: 00-telos, rel: depends_on, provenance: derived}
---

# The conformance loop

## The atom
The governed unit is **conformance**: *does the realized reality match the declared intent?*

- The **declared** side (intent / design / spec — the "SDD" face) and the **witnessed** side
  (evidence / test — the "TDD" face) are the **two faces of one atom**, not two artifacts.
- UACP makes the **binding itself** the governed primitive — checked at the membrane on every
  transition, not the writing of a spec nor the running of a test in isolation.
- Its defining commitment is **refusal-to-drift**: in ordinary software the spec-doc and the
  tests are separate artifacts owned by separate phases, and they rot apart (the doc lies, the
  tests decay). UACP *forbids that separation* for an actor who cannot be trusted to hold it
  himself.

This is why UACP resists the "SDD + TDD" framing: those are the frozen write-side and
check-side snapshots of the *one relation* it governs. Naming it as a pair mistakes two faces
for two components.

## The semantic differentia (why a loop, not two documents)
The executor is **semantic** (non-deterministic), and that single fact forces the shape:

- it **cannot be trusted to infer the spec** → intent must be **externally declared**
  (PROPOSE / PLAN exist for exactly this);
- it **cannot certify its own pass** → verification must be **externally witnessed**
  (gates / councils / codeflair; the "no self-attesting closure" invariant).

A relation that must stay true **across time and across runs**, enforced against a fallible
actor, cannot live in a static document — a document cannot re-check itself at each transition
or carry the binding into the next run. It must be a **running loop.** That is the reason UACP
had to become a *lifecycle*, not a pair of templates.

## Genus and differentia (one sentence)
- **Genus:** a *conformance loop* — a control loop whose reference is the declared intent,
  whose sensor is the witnessed evidence, whose error signal is *drift*, and whose correction
  is rework / critique.
- **Differentia:** the executor is *semantic* — so both the declaration and the witness must be
  externalized (neither inferred nor self-certified).

`determinism : machines :: conformance-loop-with-external-witness : semantic agents.`
