---
type: analysis
title: The pipeline — the atom run in time; the name `measure` stays; the feedback edge is the substrate
description: The conformance atom, run in time, is a pipeline Reality -> Comprehend -> Model -> Measure -> Decision -> Serialize -> Persistent State, with a FEEDBACK EDGE (Persistent State -> Reality) that produces the memory SUBSTRATE. The NAME `measure` is deliberately KEPT (ADR-0018 / 11-measure, mike 2026-06-24, reaffirmed 2026-07-17) — the injected word is the intervention against premature deciding — while the design states honestly that the OPERATION is a grounded, fail-closed judgment. Decision is split from Measure (Measure produces the signal, Decision acts on it) and Model is named as its own stage; recursive critique attaches to measure AND decision.
tags: [pipeline, measure, decision, model, feedback-edge, memory-substrate, adr-0018]
timestamp: 2026-07-16
edges:
  - {dst: 10-conformance-loop, rel: realizes, provenance: asserted}
---

# The pipeline (the atom run in time)

```
Reality → Comprehend → Model → Measure → Decision → Serialize → Persistent State
              ▲                                                          │
              └───────────────── recursive critique ─────────────────────┘
                        ( = produces the memory substrate )
```

## The name `measure` stays (and why v1 was wrong to rename it)
v1 of this bundle proposed `measure → evaluate` on descriptive grounds ("the operation is a
judgment, not a reading off a ruler"). Review caught that this **re-opened a ratified decision
on the exact grounds it had already rejected**: ADR-0018 and `11-measure.md` record that
reviewers wanted a judgment-word and were refused, because CMS is *normative, not descriptive*
— the LLM's signature failure mode is **premature deciding**, so the injected word must pull
*away* from "decide," and *"the word is the intervention."* "Evaluate" drifts back toward the
disease. **Ruling (mike, 2026-06-24; reaffirmed 2026-07-17): the name `measure` stays.**

What survives from the v1 instinct, stated where it belongs (the design, not the injected
cognition): the *operation* named `measure` **is a judgment** — compare / assess / select —
grounded in evidence and fail-closed (PASS/FAIL/ERROR distinct), with no pretense of an
objective ruler. Descriptive honesty lives here; the corrective name lives in the prompt.

## Measure and Decision are distinct
- **Measure** *produces the signal* (the grounded, fail-closed judgment of conformance).
- **Decision** *acts on the signal* (route / gate / accept / reject — the hinge).

The split matters because **recursive critique attaches to both**: you can critique the
measurement (was the judgment sound?) *and* the decision (was the right action taken on it?).
This is compatible with `21-decision-hinge.md` (which already draws `measure → route →
serialize | drop`): Decision remains the **seam-box between the verbs, not a fourth CMS verb** —
this node only makes its critique-attachment explicit.

## Model
Comprehend raises Reality to a computable **Model** (the one semantic act, done once — do not
silently re-interpret downstream). Naming the Model as its own stage makes explicit that
Measure judges *the model*, not raw reality — a wrong Model is a distinct failure from a wrong
measurement — and gives the cross-actor rule (50.A.5) its object: cooperation means a second
actor consumes the **serialized Model**, never re-interprets raw reality behind the first
actor's back.

## The feedback edge produces the memory substrate
`Persistent State → Reality` is **not decoration.** Run N's serialized residue becomes run
N+1's reality, to be re-comprehended and re-measured. Stated precisely (mike's ruling: the
accurate word is *substrate*):

- the feedback edge produces the **memory substrate** — typed, provenanced residue accumulated
  run over run; the foundation memory is *built on*, not memory itself (00);
- the same edge is the **recursive-critique edge at the run scale**: last run's evidence is
  this run's declaration-to-be-checked;
- this brings the **cross-run axis inside the model** (the diagram plus the substrate
  definition). What is *not* claimed closed here: the enforcement mechanism — what RESOLVE must
  serialize so the next TRIAGE can comprehend it — is build work, planned in 50.B.
