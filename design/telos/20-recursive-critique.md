---
type: analysis
title: Recursive critique — the third leg, its critique base case, and what the base case does NOT promise
description: The witness is ALSO a fallible semantic actor, so trust cannot rest on "the test is objectively right." It rests on RECURSIVE CRITIQUE — no evaluation is final by fiat — terminating at a declared CRITIQUE BASE CASE. Honesty hardened post-review — the base case bounds EFFORT, not correctness; a fixpoint counts only if the witness is INDEPENDENT (self-consensus is not a floor); the budget floor is soft and human-backed; the human verdict is a serialized-fiat EXCEPTION, named as such; and every termination decision is made witness-side and serialized, never by the actor being governed.
tags: [recursive-critique, critique-base-case, fixpoint, independence, gate-actor-recursion, human-verdict, "issue-98"]
timestamp: 2026-07-16
edges:
  - {dst: 10-conformance-loop, rel: extends, provenance: asserted}
---

# Recursive critique (the third leg)

## Why the loop needs a third leg
SDD gives the loop an external *spec*. TDD gives it an external *test*. But the semantic
differentia (10) bites the **witness** too: the gate / council / reviewer is *also* a fallible
semantic actor. So trust cannot rest on *"the test is objectively right"* — that is the
determinism we already gave up. What is left is **recursive critique**:

> No evaluation is final by fiat. Each evaluation is itself open to critique — recursively —
> until a declared **critique base case** is reached.

Two established practices already do this without naming it: the **council** (a verdict a
second reviewer can overturn) and the **adversarial re-review loop** (critique → fix →
re-critique to convergence). Recursive critique makes the pattern first-class and *bounded*.

## The critique base case
A critique terminates when it reaches one of:

1. a genuinely **deterministic** check — a diff, a codeflair witness, a compile/test pass; or
2. an **independent witness reaching a fixpoint** — critique yields no new finding, where
   *independent* is load-bearing: a **different actor** than the one whose work is being
   critiqued (cross-provider, a distinct reviewer, or a deterministic oracle). **Self-consensus
   is not a floor** — the same witness declaring itself finished terminates nothing; and two
   witnesses sharing the author's blind spot (e.g. sub-agents of the author) do not count as
   independent; or
3. the **human verdict** — the hinge. This is, explicitly, a **serialized-fiat exception** to
   this node's opening rule: a human may terminate any critique *without* a decidable signal
   (exempt from measure-discipline), but the verdict MUST be recorded, provenanced, hinge-side
   (never exempt from serialize-discipline). We carve this exception deliberately and name it,
   rather than pretending it is not fiat; or
4. an exhausted **friction budget** — a *bounded* regress, never infinite. This is a **soft,
   resource floor**, not an epistemic one (see below), and per 40 it is judged on the
   **witness side** and serialized — never declared by the actor being governed.

`terminate-critique := deterministic-check | independent-fixpoint | human-verdict | budget-exhausted(witness-side)`

## What the base case does — and does NOT — promise
**It bounds EFFORT, not correctness.** Floors 2–4 guarantee the regress *halts*; they do not
guarantee it halts at truth. A fixpoint proves the independent perspectives deployed are
exhausted, not that no flaw remains; a budget floor is a decision to stop paying, not a proof
there is nothing left to find. Only floor 1 is an epistemic floor, and only for what it
deterministically checks. The bedrock states this plainly because a termination rule that
*implies* correctness it cannot deliver is itself an unwitnessed claim — the failure mode this
framework exists to prevent.

**Termination is a witness-side, governed decision.** Whoever terminates a critique (declares
the fixpoint, invokes the budget, renders the verdict) must be on the *witness/independent*
side — never the actor whose work is under critique — and the termination itself must be
**serialized** (which base case, by whom, on what grounds). "We critiqued it" without a
recorded termination is an unwitnessed claim; and a governed actor terminating its own critique
is self-attestation, forbidden by 10 and Invariant #5.

## What this closes — stated precisely
- **#98's "gate-actor recursion rule"** is supplied: a semantic gate is legitimate because it
  is itself critiquable, terminating at a declared, recorded, witness-side base case. What is
  *not* claimed: that the regress terminates at certainty — it terminates at a **bounded,
  auditable floor**, which is the strongest guarantee available once determinism is given up.
- The "who watches the watchmen" regress does not vanish; it **halts, auditably** — and the
  halt itself is open to later critique (a terminated critique can be re-opened by a new
  independent witness with a new finding; termination is a floor, not a seal).

## Non-vacuity
A critique step that can never overturn anything is theater. Each critique must be able, in
principle, to change the verdict; the base case reached must be recorded so the termination is
auditable; and floors 2 and 4 are honest only when the record shows the independent effort
actually spent (a round-count of zero is a fixpoint of laziness, not of critique).
