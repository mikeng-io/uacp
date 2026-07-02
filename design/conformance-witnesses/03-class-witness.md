---
type: decision
title: "Class witness — per-target symbol claim, kernel-mapped connectivity heuristic (witness #2)"
description: "Extends the scope-witness seam to the Verification-strength layer (issue #87): a scope_item/work_unit optionally claims its code symbol; the gate reuses the gate-invoked codeflair derivation for per-symbol connectivity FACTS; the kernel maps facts to an entailed class via the LOCKED heuristic and feeds validate_class_underclaim. The agent-writable entailed_class field becomes one source in a raise-only max-rank oracle — it can never again be the lone, forgeable word."
tags: [conformance, witness, class-underclaim, codeflair, decision, verification]
timestamp: 2026-07-03
edges:
  - {dst: 02-scope-witness-seam, rel: extends, provenance: asserted}
---
# 03 — The class witness (witness #2)

## What converts

`validate_class_underclaim` (`engines/manifest/projection.py:998`) grades the
strongest class a target's checks DECLARE against an oracle class. The oracle
slot exists in code and is explicitly independence-shaped ("independent
oracle", strongest-wins vs the legacy prose match) — but the value it reads,
`entailed_class`, is projected off the agent's own manifest
(`scope.in_scope[].entailed_class`, `work_units[].entailed_class` —
`projection.py:155,177`). The oracle is agent-forgeable: the row is
**self-attested** on the scoreboard. Issue #87 converts it by feeding the
slot from the code plane.

## Decision

**Reuse the 02 seam wholesale** — same trust root, same doctrine, one new
facts surface:

- **Claim (per-target, plural, diff-grounded)**: a `scope_item` / `work_unit`
  may declare `code_refs: [{file, name}, ...]` (plural — a single ref would
  let a multi-symbol target cherry-pick its weakest symbol; review M3). Same
  ref format as the scope artifact's `code_refs`. **The binding is falsified
  against the diff**: a target's `code_refs` are honored only for symbols
  that appear in the witness's `symbols_touched` — the same independent
  ground truth 02's coverage rides on. A claimed-but-untouched symbol is NOT
  class-derived; it surfaces as `CHK_CLASS_REF_UNTOUCHED` (warn). This kills
  the review's B2 laundering vector: naming a deliberately weakly-connected
  or untouched symbol cannot manufacture a weak oracle, because untouched
  claims derive nothing and weak derivations cannot lower the oracle (below).
  Absent `code_refs` → no-op for that target while advisory; the legacy
  oracle path continues unchanged.
- **Derivation (facts only, mostly the EXISTING wire)**: the gate execs the
  SAME configured codeflair CLI under 02's full envelope. For touched claimed
  symbols, hop-1 fan-in and wiring edges are already computable from 02's
  `neighborhood` (both directions, reason enum) — the only surface addition
  is per-symbol inbound counts where the hop-1 edge list is capped. No
  classes cross the wire — classes are verdicts (02's inversion lesson).
- **Mapping (kernel-side heuristic — held to #87's LOCKED shape, with its
  range stated honestly)**: the kernel maps facts → a witness class:
  - **no inbound references** → `sets_value`;
  - **wired-in** (inbound references exist) → `wires_symbol`;
  - **broad hop-1 fan-in** (bound cited to the spike table; NEVER closure
    magnitude) → `changes_behavior`.
  The heuristic's range deliberately EXCLUDES `ensures_obligation` (rank 2 of
  the four-value `CLASSES` vocabulary — review B3): obligation semantics are
  not derivable from connectivity. Because the oracle can only be raised
  (next bullet), a rank-2 target is never down-ranked by a witness that
  cannot say rank 2. **Open soundness risks, recorded not hidden (review
  M2)**: statically-invisible wiring (route/decorator/string registration —
  the floor's own canonical case) derives `sets_value` for genuinely
  wired symbols, and fan-in magnitude is a connectivity proxy for
  `changes_behavior`, not a semantics proof. Both are contained by the
  raise-only rule + advisory dial, and both are named promotion blockers
  below.
- **Oracle combination (review B1 — the rule that was missing): the witness
  may only ever RAISE the effective oracle, never lower it.** The gate
  computes `oracle = max_rank(witness_class, entailed_class, prose
  candidate_class)` — the as-built strongest-wins ratchet
  (`projection.py:1059-1063`) gains a third source; the prose backstop
  SURVIVES. A witness deriving weaker than the agent's own `entailed_class`
  does not supersede it silently: the disagreement surfaces as
  `CHK_ENTAILED_CLASS_SUPERSEDED` (warn) while max-rank governs. Catch-power
  is therefore monotonically non-decreasing versus today.
- **Availability (review M1)**: when a target declares `code_refs` but the
  witness cannot testify (CLI unavailable per 02's doctrine), the gate emits
  `CHK_CLASS_WITNESS_UNAVAILABLE` (warn) and falls back to today's oracles
  VISIBLY — never a silent revert to the self-attested field.
- **Dial**: advisory-first exactly as 02 — all new codes `warn`; the gate's
  comparison (`oracle_rank > declared_rank` → `CHK_CLASS_UNDERCLAIM`) is
  unchanged; only the oracle's provenance and rank floor upgrade. Promotion
  rides 02's criteria PLUS two class-specific blockers: (a) the
  statically-invisible-wiring false-`sets_value` rate must be measured on
  real targets before any blocking, (b) `CHK_CLASS_REF_UNTOUCHED` must
  stay a flag (the diff-grounding is the anti-laundering premise — it never
  becomes waivable), and (c) claim COMPLETENESS needs a measure before any
  blocking: raise-only means partial claiming (naming only a target's weakest
  touched symbols) cannot regress today's catch, but at promotion — when
  absence escalates — partial claims become the evasion of that escalation;
  code_refs-vs-touched-set completeness is the sibling of 02's criterion 7.

## Why this is the whole design

Everything hard was decided in 02 and survives unchanged: trust root,
facts-only wire, freshness-by-construction, envelope, availability doctrine,
signal discipline (hop-1 only). The decisions added here: (a) the per-target
plural claim, grounded in the diff exactly like 02's coverage; (b) the
raise-only max-rank oracle combination (prose backstop survives; no
regression path); (c) the heuristic's honest range (no `ensures_obligation`)
and named soundness risks; (d) visible availability fallback. The build is
scoped to: schema (`code_refs` on scope_item/work_unit write-time shapes),
projection carry, per-symbol inbound counts on the witness wire, the kernel
mapping fn + threshold, the max-rank feed in `validate_class_underclaim`,
teeth tests per heuristic branch AND per review-blocker (untouched claim,
raise-only, ensures_obligation preservation, unavailable visibility), and an
e2e proof reusing the 02 harness.

## Status / Checkpoint

> **2026-07-03 — DESIGN (R2).** Node authored from the E1 recon; review round
> R1 returned DO-NOT-LOCK (oracle-combination unspecified; symbol-choice
> laundering; class-range mismatch) — all findings folded: diff-grounded
> plural claims, raise-only max-rank combination, honest heuristic range +
> named soundness risks, visible unavailable fallback. Awaiting LOCK.
