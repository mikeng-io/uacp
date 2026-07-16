---
type: analysis
title: Derivations, the grain base case, and the friction budget (hardened)
description: CMS, Heartgate/gates/witnesses, the lifecycle, and the memory substrate all DERIVE from the telos. The "CMS at every grain" recursion gets its missing GRAIN BASE CASE (= the smallest serialized act — a governed-state write, or a work-product edit captured as evidence) plus a deterministic triviality floor. The FRICTION BUDGET is an AMORTIZATION test (up-front friction vs lifetime repayment), and it is HARDENED against self-authorization — any budget/triviality/termination decision is made on the WITNESS side, serialized as a first-class governed decision, itself open to critique; never asserted by the actor being governed.
tags: [derivations, grain-base-case, friction-budget, amortization, triviality, witness-side, means-end]
timestamp: 2026-07-16
edges:
  - {dst: 00-telos, rel: depends_on, provenance: derived}
---

# Derivations, the grain base case, and the friction budget

## What derives
Reading the stack top-down, each layer is a *means* to the telos:

- **CMS (comprehend → measure → serialize)** = the loop instantiated *at a single grain* —
  read the declaration, judge conformance, record the evidence.
- **Heartgate / gates / witnesses** = the *external-witness* requirement (10) made mechanical.
- **The lifecycle** (TRIAGE…RESOLVE) = the loop run *across phases* (with TRIAGE/BRAINSTORM
  honestly upstream of the atom, per 10).
- **The memory substrate** = the loop run *across runs* (the feedback edge, 30).
- **The friction budget** (below) = the amortization test that keeps all of the above honest.

Coherence remains **the product** these layers manufacture (00); the telos is why the product
is worth its price. A change to any layer is legitimate only insofar as it improves the
long-run friction trade — which is measurable only once the telos is encoded (the point of #98).

## The grain base case (closing "CMS at every grain")
`UACP.md` commands CMS "at every grain," and `23-composition.md` admits the recursion has no
base case. The telos supplies it (matching 23's own "To expand" sketch):

> **The grain bottoms out at the smallest serialized act.** Per ADR-0019 there are two write
> classes, so the terminal grain takes two forms: a **governed-state write** (a governed writer
> call — .uacp/ namespace + lifecycle/manifest artifacts) or a **work-product edit captured as
> checkpoint/diff evidence** (project code during EXECUTE, worktree-contained). Below the
> serialization/evidence boundary there is nothing to make conform; there is no sub-grain to
> comprehend/measure/serialize.

(Named the **grain base case** to keep it distinct from 20's **critique base case** — two
different recursions, two different floors.)

## The triviality floor (deterministic, witnessed — not a judgment call)
Trivial work is exempt from the full loop — but *triviality is not self-declared*. The
exemption requires BOTH:

1. a **deterministic floor** — the change is bounded (e.g. contained in a single governed
   write / single work-unit), reversible, and passes all automated checks; AND
2. a **witnessed record** — the exemption itself is serialized as a governed decision (who
   exempted, on what floor). Skipping governance is *itself a governed act*.

An exemption that fails either prong is not triviality — it is drift wearing a label. (This is
the operational form of "no ceremony below the budget," with the ceremony's *absence* still on
the ledger.)

## The friction budget (amortization form, hardened)
The v1 phrasing — "where the budget is negative, the honest move is less governance" — was
correctly flagged by review as a **self-authorizing escape hatch**: an actor optimized for
velocity will always claim the budget is negative. v2 restates the budget with two locks.

**Form: amortization, not instant cost.** Friction is time-asymmetric (00): governance *adds*
friction at the point of interaction and *removes* it over the pipeline's lifetime (guardrails,
SOPs, no re-derivation, no silent drift). The budget question is never "does this feel
expensive now?" but **"is the up-front investment repaid over the horizon of cooperation?"** A
governance step with lifetime-negative return should be removed; one that is merely annoying
today is exactly the investment the telos exists to make.

**Lock 1 — witness-side, serialized, critiquable.** Any decision that invokes the budget —
terminating a critique (20.4), exempting work as trivial, or removing a governance step as
lifetime-negative — is made on the **witness/independent side**, serialized as a first-class
governed decision, and remains open to recursive critique. **Never asserted by the actor being
governed** — a self-graded budget is self-attestation, forbidden by 10 and Invariant #5. The
friction budget thereby obeys the very atom it governs.

**Lock 2 — asymmetric burden.** Adding governance needs a plausible amortization case;
*removing* governance needs a **serialized, witness-side case with evidence** (e.g. measured
cost vs. measured defect-catch — numbers the Proving Ground substrate can supply). Doctrine
alone never removes a guardrail.

**Status of quantification:** the doctrine above is normative now; the quantitative proxy
(rework-rounds / gate-cost vs. defects-caught, measured per-run) is an empirical follow-up the
Proving Ground is designed to feed. Until it lands, budget invocations lean on Lock 1's
witness + serialization — a *soft floor honestly labeled* (20), not a pretended measurement.
