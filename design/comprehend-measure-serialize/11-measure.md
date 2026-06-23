---
type: analysis
title: Measure — reduce the model to a decidable signal
description: The second verb, REDEFINED. Not necessarily numeric — any reduction of the comprehended model to a decidable signal (compare, validate, score, rank, select, infer). The trustless property is deterministic + fail-closed, not quantification. Includes the open naming question.
tags: [primitive, measure, decidable-signal, deterministic]
timestamp: 2026-06-21
edges:
  - {dst: 00-the-axiom, rel: depends_on, provenance: derived}
---

# Measure

**Question:** *what does it mean?* **Output:** a **decidable signal.**

## What the signal is *about* (affordance AND prohibition)

The decidable signal answers an **actionable** question, and that question spans the positive *and* the negative: **what must be done · what was achieved · what must NOT be done.** Measure is not only "is this OK?" — it also produces the *constraints* (the `prohibition` / `method_constraint` of the negative-space layer). A measure that only ever produces affordances and never a "forbidden" verdict is half a measure.

## The redefinition (the key refinement)

"Measure" reads like it must produce a *number* — but most operations don't. The real definition is broader: **any reduction of the comprehended model to a *decidable signal*** — something a decision can act on. All of these are `measure`:

| Form | Example |
|---|---|
| compare | `signature == expected` |
| validate | `balance >= amount` |
| score | `importance = 0.9` |
| rank | order N candidates |
| select | `tool A or tool B` |
| infer | derive a conclusion from facts |

## The discipline (what makes it trustless)

Not numeric-ness — **determinism + fail-closed.** A measurement must be reproducible and keep **PASS / FAIL / ERROR distinct** (ERROR ≠ PASS). A `grep route_mounted` standing in for "the route works" is *not* a measurement — it's a weak proxy (the #503 failure). The signal must bind to the real property.

## Naming: KEEP `measure` (mike's decision, 2026-06-24) — it is the corrective name

Four reviewers (the hunt's falsifiers + kimi + minimax) recommended renaming to `decide`, arguing *descriptively*: the step produces a verdict, and `infer`/`select` are not "measurement." That is correct **for a well-behaved system** — and it is the wrong test. CMS is **normative**, not descriptive: it exists to *discipline a misbehaving processor* (the LLM). The LLM's signature failure mode **is premature deciding** — it asserts, concludes, "looks done," without grounding. That is self-attestation.

So step 2's whole job is to force the model to **measure** (produce a fail-closed, evidence-bound signal) *instead of* **decide** (assert a conclusion):
- **measure** = epistemically humble — observe a property of reality; it can come back FAIL/ERROR; it is *evidence*.
- **decide** = epistemically assertive — commit to a conclusion; it can be arbitrary; it is *assertion*.

Naming step 2 "decide" names it **after the disease**. And because CMS is injected into the LLM's prompt to shape cognition ([25-enforcement-surfaces](25-enforcement-surfaces.md)), **the word is the intervention**: "measure" pushes the model toward *"what is my evidence? can this come back FAIL?"*; "decide" would push it toward *"I conclude X."* In an infra-only framing the name is cosmetic (which is why descriptive reviewers optimized for accuracy); on the cognition surface the name is **load-bearing**, and `measure` is the corrective. **Decision: `measure` stays.** (Bounded by the hunt: the discipline holds where the actor is **mechanical**; for pure state-moves with no decision, `measure` is simply out of scope — node 30.)

## To expand
- The signal taxonomy (boolean / scalar / ordinal / categorical) and which decisions each can route.
- Where the determinism bar bites (a measurement that depends on environment is class-E fragility).
- Multi-signal measures (a measurement that emits importance AND risk AND novelty at once).
