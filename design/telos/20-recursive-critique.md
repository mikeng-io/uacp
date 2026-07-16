---
type: analysis
title: Recursive critique — the third leg, and its mandatory base case
description: The witness is ALSO a fallible semantic actor, so trust cannot rest on "the test is objectively right" (the determinism we gave up). It rests on RECURSIVE CRITIQUE — no evaluation is final by fiat; each is itself open to critique — terminating at a DECLARED base case (deterministic check | independent-witness fixpoint | human verdict | friction budget). Recursive-critique-without-a-base-case is the unbounded regress the bedrock must not have; the base case IS the rule. This is the gate-actor-recursion rule #98 flags as missing.
tags: [recursive-critique, base-case, fixpoint, gate-actor-recursion, human-verdict, "issue-98"]
timestamp: 2026-07-16
edges:
  - {dst: 10-conformance-loop, rel: extends, provenance: asserted}
---

# Recursive critique (the third leg)

## Why the loop needs a third leg
SDD gives the loop an external *spec*. TDD gives it an external *test*. But the semantic
differentia (see 10) bites the **witness** too: the gate / council / reviewer is *also* a
fallible semantic actor. So trust cannot rest on *"the test is objectively right"* — that is
the determinism we already gave up. What is left is **recursive critique**:

> No evaluation is final by fiat. Each evaluation is itself open to critique — recursively —
> until a **declared base case** is reached.

Two established practices already do this without naming it: the **council** (a verdict a second
reviewer can overturn) and the **adversarial re-review loop** (critique → fix → re-critique to
convergence). Recursive critique makes the pattern first-class and, crucially, *bounded*.

## The base case (not optional — it IS the rule)
Recursion without a base case is the unbounded regress the bedrock must not contain (#98's
"the recursion has no base case"). A critique terminates when it reaches one of:

1. a genuinely **deterministic** check — a diff, a codeflair witness, a compile/test pass; or
2. an **independent witness reaching a fixpoint** — critique yields no new finding (empirically:
   the multi-round adversarial review that converges on "no further findings"); or
3. the **human verdict** — the hinge, exempt from measure-discipline, never from
   serialize-discipline (see the human-verdict primitive, 50); or
4. an exhausted **friction budget** — a *bounded* regress, never infinite (see 40).

`terminate-critique := deterministic-check | witness-fixpoint | human-verdict | budget-exhausted`

## What this closes
- **#98's "gate-actor recursion rule."** Recursive critique *is* that rule: a semantic gate is
  legitimate because it is itself critiquable, down to a base case.
- **The "who watches the watchmen" regress.** It does not vanish; it *terminates* — explicitly,
  at a declared floor, rather than being ignored or pretended-away.

## Non-vacuity
A critique step that can never overturn anything is theater. Each critique must be able, in
principle, to change the verdict; and the base case reached must be *recorded* (serialized) so
the termination is auditable — otherwise "we critiqued it" is itself an unwitnessed claim.
