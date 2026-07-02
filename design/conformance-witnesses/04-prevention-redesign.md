---
type: decision
title: "Prevention-at-PLAN redesigned — hop-1 forecast vs declared boundary, promotion by measured precision"
description: "Replaces issue #86's invalidated method (dependency-closure magnitude — hub-dominated, ranking-inverting per the #83 spike) with hop-1 membership FORECASTING: at PLAN, the predicted cascade (hop-1 neighborhood of the declared code_refs on the current graph) is compared against the declared boundary; detection-at-VERIFY later measures the actual. Blocking is earned only by measured forecast precision, accumulated run-by-run from the predicted-vs-actual pair every governed run naturally produces."
tags: [conformance, witness, prevention, plan, codeflair, decision, scope]
timestamp: 2026-07-03
edges:
  - {dst: 02-scope-witness-seam, rel: extends, provenance: asserted}
  - {dst: 03-class-witness, rel: relates_to, provenance: asserted}
---
# 04 — Prevention-at-PLAN, redesigned

## Why the written method is dead

Issue #86 as written: "codeflair computes dependency closure of the declared
symbols against the current graph; claimed boundary ⊉ cascade → block before
work starts." Two findings killed it:

- **Closure magnitude is hub-dominated and inverts the true ranking** (spike
  #83: `run_all_engines`, 3-4 direct callers, closure 267 — larger than
  `Violation` at 123 with 65 direct callers). Node 02 already bans it from
  every threshold; a PLAN gate built on it would block the wrong plans.
- **Prevention has no ground truth.** Detection (02) and the class witness
  (03) are honest because an independent account of *what actually happened*
  exists — the diff. At PLAN nothing has happened: there is no diff to
  falsify anything against, and new symbols the work will create do not exist
  in any graph. A PLAN-time "block" therefore cannot be a measurement of
  reality; unacknowledged, it is a guess wearing a gate's authority.

## Decision

**Prevention is a FORECAST, priced as one.** Same seam as 02 (gate-invoked
CLI, kernel-default trust root, facts-only wire, full envelope), same signal
discipline (hop-1 membership, never closure magnitude), and an explicitly
probabilistic posture with a measurable path to teeth:

- **What is computed (at PLAN-exit)**: the witness derives, on the CURRENT
  tree, the hop-1 neighborhood of the scope's declared `code_refs` (02's
  claim — no new claim surface). The kernel computes the **predicted
  cascade**: hop-1 neighbors whose FILES fall outside the declared
  write_paths (glob-aware, as landed in the 02 build) and outside the
  declared refs' own files. Non-empty → `SC_PLAN_CASCADE_FORECAST` (warn):
  "editing what you declared plausibly cascades into files outside your
  declared boundary — re-declare before you start."
- **What is honestly NOT computable**: symbols the work will CREATE (they
  exist in no graph yet — the same ceiling 02 records for
  `unresolved_touched`, one phase earlier), dynamically-wired effects (03's
  static-wiring risk applies verbatim), and anything about work the agent
  declared nothing for. The forecast bounds *declared* work's *existing*
  neighborhood — nothing more, and the advisory text must say so.
- **The symmetry that makes it measurable**: prevention and detection are the
  SAME comparison at two times — predicted-vs-declared at PLAN, actual-vs-
  declared at closure. Every governed run that declares `code_refs` therefore
  produces a natural (forecast, outcome) pair: the PLAN-time predicted
  cascade and the closure-time `SC_UNDECLARED_CASCADE` set. **Forecast
  precision and recall are computable per run with zero extra machinery** —
  this is the promotion currency.
- **Where it runs**: the PLAN→EXECUTE phase-exit already carries a forced
  graph gate (D35 `plan_exit`); the forecast check joins that invocation
  point. It does NOT join the closure engine sweep (forecasting after the
  work is done is noise). The engine remains phase-agnostic code; only the
  invocation site is phase-bound.
- **Enforce dial — blocking must be EARNED, and the bar is stated now**:
  `SC_PLAN_CASCADE_FORECAST` stays advisory until ALL of:
  1. 02's detection witness is itself promoted (a forecast may not outrank
     the measurement it is validated against);
  2. measured forecast precision over the accumulated (forecast, outcome)
     pairs clears a pre-registered bar — proposed: ≥0.8 precision over ≥20
     witnessed runs, with the bar itself recorded in the promotion decision
     (post-hoc bar-moving is the self-attestation this initiative exists to
     kill);
  3. the block, when it comes, is on **membership** ("this hop-1 neighbor's
     file is outside your boundary"), never on any magnitude.
  A forecast that never clears the bar stays an advisor forever — that is a
  legitimate steady state, not a failure: the scoreboard row records
  "advisory forecaster" honestly rather than promoting a guess.

## Consequences for the issue

#86's build scope shrinks and re-anchors: no closure computation, no
PLAN-time blocking in v1, one membership check at an existing invocation
point, plus the per-run (forecast, outcome) serialization that detection
already half-produces. The ambitious half of the original issue — "block
before work starts" — is not abandoned; it is priced: it costs demonstrated
forecast precision, which costs accumulated governed runs, which is exactly
the promotion evidence the initiative is already gated on.

## Status / Checkpoint

> **2026-07-03 — DESIGN.** Node authored to unstick #86 (its written method
> was invalidated by the #83 spike; recorded on the issue and in node 02).
> Awaiting review round.
