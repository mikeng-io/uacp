---
type: analysis
title: The pipeline — the atom run in time, and why "evaluate" not "measure"
description: The conformance atom, run in time, is a pipeline Reality -> Comprehend -> Model -> Evaluate -> Decision -> Serialize -> Persistent State, with a FEEDBACK EDGE (Persistent State -> Reality) that IS the cross-run memory loop. "Measure" over-claims determinism (a ruler that exists); the operation is a JUDGMENT, so it is EVALUATE (compare/assess/select). Decision is split from Evaluate — Evaluate produces the signal, Decision acts on it (the gate). Recursive critique attaches to both.
tags: [pipeline, evaluate, measure, decision, feedback-edge, cross-run-memory]
timestamp: 2026-07-16
edges:
  - {dst: 10-conformance-loop, rel: realizes, provenance: asserted}
---

# The pipeline (the atom run in time)

```
Reality → Comprehend → Model → Evaluate → Decision → Serialize → Persistent State
              ▲                                                          │
              └───────────────── recursive critique ─────────────────────┘
                        ( = the cross-run memory loop )
```

## Evaluate, not Measure
"Measure" implies a ruler that objectively exists — it over-claims the determinism the semantic
executor does not have. The operation is a **judgment**: *compare / assess / select*. So the
verb is **Evaluate**. (This supersedes `11-measure.md` in the CMS bundle — see 50. Its "measure
= reduce to a decidable signal, fail-closed" content survives verbatim; only the *name*
over-claimed.)

## Evaluate and Decision are distinct
- **Evaluate** *produces the signal* (the fallible judgment of conformance).
- **Decision** *acts on the signal* (route / gate / accept / reject — the hinge).

Splitting them matters because **recursive critique attaches to both**: you can critique the
evaluation (was the judgment sound?) *and* the decision (was the right action taken on it?).
Collapsing them into "measure" hides the second attachment point.

## Model
Comprehend raises Reality to a computable **Model** (the one semantic act, done once — do not
silently re-interpret downstream). Naming the Model as its own stage makes explicit that Evaluate
judges *the model*, not raw reality — and that a wrong Model is a distinct failure from a wrong
Evaluation.

## The feedback edge = memory (not a bolt-on)
`Persistent State → Reality` is **not decoration.** Run N's serialized residue becomes run
N+1's reality, to be re-comprehended and re-evaluated. So:

- the **memory substrate** is **what the loop leaves behind** — not a store bolted on the side;
- the same edge is the **recursive-critique edge** at the run scale (last run's evidence is this
  run's declaration-to-be-checked);
- this closes the **cross-run axis** that #98 flags as sitting *outside* the axiom.

Memory therefore stops being a separate philosophical "end" and becomes an accumulated
spec-and-evidence corpus — a growing regression suite the next run does not re-derive.
