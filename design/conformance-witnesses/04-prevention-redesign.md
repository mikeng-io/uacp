---
type: decision
title: "Prevention-at-PLAN redesigned — hop-1 forecast vs declared boundary, promotion by measured precision"
description: "Replaces issue #86's invalidated method (dependency-closure magnitude — hub-dominated, ranking-inverting per the #83 spike) with hop-1 membership FORECASTING: at PLAN, the predicted cascade (hop-1 neighborhood of the declared code_refs on the current graph) is compared against the declared boundary; detection-at-VERIFY later measures the actual; the (forecast, outcome) pair is defined file-level in ONE universe against the diff-containment offender set (the naive symbol-coverage pairing is provably disjoint). Blocking is earned only by measured forecast precision, accumulated run-by-run from the predicted-vs-actual pair every governed run naturally produces."
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

- **What is computed (at PLAN-exit)**: the witness derives, on the
  **committed baseline** (HEAD — see the timing clause below), the hop-1
  neighborhood of the scope's declared `code_refs` (02's *claim* surface is
  reused; its *facts* surface is NOT — see the new-mode clause). The kernel
  computes the **predicted out-of-boundary FILE set**: files of hop-1
  neighbors that fall outside the declared write_paths (glob-aware, as landed
  in the 02 build) and outside the declared refs' own files. Non-empty →
  `SC_PLAN_CASCADE_FORECAST` (warn): "editing what you declared plausibly
  cascades into files outside your declared boundary — re-declare before you
  start."
- **A new witness facts mode, named as added machinery (review M1)**: 02's
  LOCKED wire grounds `neighborhood` in `symbols_touched` — at PLAN there is
  no diff, so that wire is EMPTY by construction. The forecast requires a new
  diff-independent facts mode on the witness CLI (hop-1 neighborhood of
  given refs, same envelope, same facts-only discipline). This is an
  extension of the 02 seam, not a reuse of its wire.
- **What is honestly NOT computable**: symbols the work will CREATE (they
  exist in no graph yet — the same ceiling 02 records for
  `unresolved_touched`, one phase earlier), dynamically-wired effects (03's
  static-wiring risk applies verbatim), and anything about work the agent
  declared nothing for. The forecast bounds *declared* work's *existing*
  neighborhood — nothing more, and the advisory text must say so.
- **The (forecast, outcome) pair, defined in ONE universe (review BLOCKER)**:
  the naive pairing — forecast vs the closure `SC_UNDECLARED_CASCADE` set —
  is **structurally disjoint**: anything hop-1 of a declared ref is *covered*
  at closure and can never appear in that set, so precision would be zero on
  every run by construction. The pair is therefore defined **file-level, one
  boundary, both sides**:
  - *forecast* = predicted out-of-boundary files (above; committed-baseline
    graph);
  - *outcome* = the ACTUAL out-of-boundary changed files at closure — the
    offender set the landed diff-containment check already computes
    (glob-aware, governed-namespace-exempt), NOT the symbol-coverage set.
  Precision = |forecast ∩ outcome| / |forecast|; recall over |outcome|.
  **One boundary predicate, applied verbatim to both sides** (the write_paths
  globs + governed/gate-cache exemptions as landed), with a single stated
  asymmetry: the declared refs' OWN files are carved out forecast-side only —
  a changed ref-file outside write_paths lands in the outcome but was never
  forecastable, a structural recall hit recorded here, not hidden. The two
  sides differ in time (pre-change graph vs actual diff) — that is what
  makes it a forecast — never in universe. The
  earlier claim of "zero extra machinery" is RETRACTED: the pairing needs the
  forecast persisted at PLAN and joined at closure (next clause).
- **Serialization home (review M2)**: the plan_exit gate WRITES its forecast
  as a gate-owned record — `verification/<run_id>-cascade-forecast.yaml`
  (02's doctrine: a gate-written evidence copy is legitimate; it is never a
  gate INPUT that trusts agent content). At closure, the sweep computes the
  outcome side and appends the joined (forecast, outcome, precision) record.
  These records are **promotion evidence, not runtime gate inputs**: a
  doctored record games only the promotion corpus, which the promotion
  decision must audit — and the forecast is deterministically re-derivable
  from the recorded `graph_stamp`, so doctoring is detectable, not merely
  forbidden. **Forecast of record** = the record as written at the
  SUCCESSFUL plan_exit (last-write-wins across retried attempts); a heeded
  warning — agent re-declares, boundary widens, final forecast empty —
  yields no pair by design, and pairs exist only for runs that declared BOTH
  `code_refs` and `write_paths` (the outcome side no-ops without a declared
  file boundary).
- **Where it runs (review MINOR made explicit)**: a **new, phase-bound
  check** joins the existing D35 `plan_exit` forced-gate invocation point —
  it is NOT `scope_conformance.validate()` re-invoked earlier (that computes
  the diff cascade, empty at PLAN). plan_exit thereby acquires its first
  subprocess prober; 02's availability doctrine applies verbatim
  (UNAVAILABLE advisory, never a crash, never a silent pass). It does NOT
  join the closure engine sweep (forecasting after the work is done is
  noise).
- **Timing assumption, stated and defended (review MINOR)**: the prediction
  framing holds only if the forecast precedes the work. The worktree
  protocol puts writes in EXECUTE, but ADR-0019 does not raw-block early
  work-product edits — so the forecast derives on the **committed baseline
  (HEAD)**, never the dirty tree, and a dirty tree at plan_exit is flagged
  in the advisory detail (the forecast is then a prediction about declared
  work from the last clean state, and says so).
- **Enforce dial — blocking must be EARNED, and the bar is stated now**:
  `SC_PLAN_CASCADE_FORECAST` stays advisory until ALL of:
  1. 02's detection witness is itself promoted (a forecast may not outrank
     the measurement it is validated against);
  2. measured forecast precision over the accumulated (forecast, outcome)
     pairs clears a pre-registered bar — proposed: ≥0.8 precision over ≥20
     witnessed runs — with the bar AND the aggregation form (per-run mean vs
     pooled-over-pairs; per-run mean proposed, since pooling lets one
     hub-heavy run dominate) recorded in the promotion decision (post-hoc
     bar-moving OR formula-picking is the self-attestation this initiative
     exists to kill);
  3. the block, when it comes, is on **membership** ("this hop-1 neighbor's
     file is outside your boundary"), never on any magnitude;
  4. **hub fan-out is bounded first (02 criterion 7, which hits the forecast
     HARDER — review M3)**: detection's cascade is bounded by the actual
     diff, but the forecast counts ALL hop-1 neighbors of declared refs,
     bounded only by graph degree — one declared 65-caller hub floods the
     forecast with false positives and drives precision toward zero exactly
     where prediction matters. The per-ref fan-out bound / near-minimality
     measure of 02 criterion 7 is a hard prerequisite for this gate's
     promotion, and hub-heavy forecasts must be marked as low-confidence in
     the advisory detail even while advisory.
  A forecast that never clears the bar stays an advisor forever — that is a
  legitimate steady state, not a failure: the scoreboard row records
  "advisory forecaster" honestly rather than promoting a guess.

## Consequences for the issue

#86's build scope shrinks and re-anchors: no closure computation, no
PLAN-time blocking in v1; one new phase-bound membership check at the
existing plan_exit invocation point, one new diff-independent witness facts
mode, and the gate-owned forecast record plus its closure-time join. The ambitious half of the original issue — "block
before work starts" — is not abandoned; it is priced: it costs demonstrated
forecast precision, which costs accumulated governed runs, which is exactly
the promotion evidence the initiative is already gated on.

## Status / Checkpoint

> **2026-07-03 — DESIGN (R2).** R1 returned DO-NOT-LOCK: the naive
> (forecast, outcome) pairing was structurally disjoint (hop-1 of declared =
> covered at closure — precision zero by construction); the facts surface was
> wrongly claimed as 02-reuse; the pair store was unnamed; hub fan-out
> unaddressed. All folded: file-level one-universe pairing against the
> diff-containment offender set, new witness facts mode named as added
> machinery, gate-owned forecast record + closure join (evidence-grade,
> re-derivable), criterion-7 prerequisite, committed-baseline timing clause.
> Awaiting LOCK.
