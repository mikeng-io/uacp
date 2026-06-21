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

## Open question: is "measure" the right name?

This is the one verb whose naming is genuinely uncertain. If *every* `compare / validate / infer / rank / select` sits comfortably under "measure," the name holds. If one resists, the primitive may need a broader verb (the invariant is *"reduce to a decidable signal"*, not *"quantify"*). Tracked in [30-validation-matrix](30-validation-matrix.md).

## To expand
- The signal taxonomy (boolean / scalar / ordinal / categorical) and which decisions each can route.
- Where the determinism bar bites (a measurement that depends on environment is class-E fragility).
- Multi-signal measures (a measurement that emits importance AND risk AND novelty at once).
