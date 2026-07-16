---
type: analysis
title: Derivations and the friction budget — what hangs off the telos
description: CMS, Heartgate/gates/witnesses, the lifecycle, and memory all DERIVE from the telos (the inversion #98 flags, corrected). The "CMS at every grain" recursion gets its missing BASE CASE (= the governed write) plus a triviality rule. The FRICTION BUDGET is the means/end guard — the loop is worth running only where the friction it removes exceeds the friction it adds; where negative, the honest move is LESS governance.
tags: [derivations, inversion, grain-base-case, friction-budget, triviality, means-end]
timestamp: 2026-07-16
edges:
  - {dst: 00-telos, rel: depends_on, provenance: derived}
---

# Derivations and the friction budget

## What derives (the inversion, corrected)
CMS does **not** stand above the purpose; it derives from it. Reading the stack top-down:

- **CMS (comprehend → evaluate → serialize)** = the loop instantiated *at a single grain* —
  read the declaration, judge conformance, record the evidence.
- **Heartgate / gates / witnesses** = the *external-witness* requirement (10) made mechanical.
- **The lifecycle** (TRIAGE…RESOLVE) = the loop run *across phases*.
- **Memory** = the loop run *across runs* (the feedback edge, 30).
- **The friction budget** (below) = the means/end guard that keeps all of the above honest.

Corrected inversion: every one of these is a *means*; the telos is the *end*. A change to any of
them is legitimate only insofar as it serves the end — which is measurable only once the end is
encoded (the whole point of #98).

## The grain base case (the missing base case for "CMS at every grain")
`UACP.md` commands CMS "at every grain," and the CMS bundle admits the recursion has **no base
case**. The telos supplies it:

> **The grain bottoms out at the governed write.** CMS applies down to — and stops at — the
> smallest *serialized* act (a governed writer call). Below that there is nothing to make
> conform; there is no sub-grain to comprehend/evaluate/serialize.

Paired with a **triviality rule**: work whose friction-removed does not exceed its
friction-added is *exempt* — you do not wrap a one-line, self-evident, reversible act in the
full loop. (This is the operational form of "no ceremony below the budget," and it is what the
friction budget decides.)

## The friction budget (means/end guard)
The loop is worth running **only where the friction it removes exceeds the friction it adds.**

- Governance has a real cost (declaration, evidence, gates, review). That cost is measured
  against the *purpose* (less friction on cooperation), not indulged for its own sake.
- Where the budget is **negative** — the governance costs more friction than the drift it
  prevents — the honest move is **less** governance, not more. Coherence is a means; buying it
  past its value is the failure this bundle guards against.
- The budget is also a **base case for recursive critique** (20.4): critique stops when further
  critique would cost more than the residual risk it could still find.

Open question for red-pen: is the friction budget **qualitative** (a doctrine + the triviality
rule, applied by judgment) or does it want a **quantitative** proxy (e.g., rework-rounds /
gate-count vs. defects-caught, measured by the Proving Ground)? The telos needs the doctrine;
the number, if any, is an empirical follow-up the substrate can supply.
