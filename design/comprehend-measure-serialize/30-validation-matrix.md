---
type: analysis
title: Validation Matrix — observation → axiom by counterexample hunt
description: The open ledger that decides whether CMS is a mere observation or a true axiom. Deliberately test the reduction against foreign domains (distributed systems, databases, compilers, protocols); the principle earns "axiom" only by surviving the hunt with no clean break. Self-referential — verify the axiom the way the axiom prescribes.
tags: [primitive, validation, axiom, counterexample, falsification]
timestamp: 2026-06-21
edges:
  - {dst: 00-the-axiom, rel: decides_on, provenance: asserted}
---

# Validation Matrix

The gate between **observation** ("most workflows fit") and **axiom** ("any valid operation MUST contain all three"). You do not assert the stronger claim — you **earn it by failing to falsify it.** This node is the open ledger.

## The hunt (deliberately foreign domains)

| Domain | Reduces to CMS? | comprehend / measure / serialize | Clean, or forced? |
|---|---|---|---|
| Event sourcing | TBD | read command + state / validate invariant / append event | |
| Raft consensus | TBD | receive RPC + log / quorum + term check / commit entry | |
| Git merge | TBD | read two trees + base / 3-way diff conflict-check / write merge commit | |
| k8s reconciliation | TBD | observe actual + desired / diff / apply (write status) | |
| CPU instruction | TBD | fetch / decode | execute → writeback | |
| LLM inference | TBD | tokenize + attend / logits / sample → emit token | |
| DB transaction | TBD | read + locks / constraint check / commit \| rollback | |
| OAuth | TBD | parse grant + creds / validate + scope / issue \| deny token | |
| Human code review | TBD | understand diff / correct? secure? / approve \| request-changes | |

> Fill each row: does it reduce **without forcing**? A clean reduction is evidence; a **forced** one (contrived relabeling) is a yellow flag; a genuine break is a **counterexample** that bounds the claim. Record honestly — a found boundary is more valuable than a forced fit.

## The naming sub-question

While testing, challenge step 2's name: do all of `compare / validate / infer / rank / select` sit comfortably under **"measure"**? If yes, the name holds. If one resists, the primitive may need a broader verb (the property is *"reduce to a decidable signal"*, not *"quantify"*).

## Self-reference (the proof is the method)

We validate this axiom **the way the axiom prescribes**: *comprehend* the claim → *measure* it against adversarial cases → *serialize* the verdict. The [verification method](../verification-method/00-the-primitive.md) is the instrument judging its own foundation — if it cannot, that is itself a finding.

## The promotion gate

Only when this matrix is full and counterexample-free does CMS earn promotion to a canonical principle (a neutral line in AGENTS.md + the per-phase mapping in `docs/`) — via a governed run, not an assertion. Until then it is a **named hypothesis**.

## To expand
- Fill the matrix (one row per session; cite the reasoning, not just a verdict).
- Add domains that *stress* it most (anything with no obvious "measure" — e.g. a pure cache write, a heartbeat).
- Record the strongest near-counterexample found, as the honest boundary.
