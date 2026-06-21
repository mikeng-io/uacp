---
type: analysis
title: The Decision Hinge — measure does not imply persist
description: The routing/policy that sits between measure and serialize — measure produces a signal, a policy decides where it lands or whether it drops. Not a fourth primitive but the gate at the seam, and where no-self-attestation lives.
tags: [primitive, decision, routing, policy, no-self-attestation]
timestamp: 2026-06-21
edges:
  - {dst: 00-the-axiom, rel: depends_on, provenance: derived}
---

# The Decision Hinge

`measure → serialize` hides a step: **measure produces a signal; a policy decides what to do with it.**

```
measure → [decision / routing] → serialize
              importance 0.1 → drop
              importance 0.9 → durable memory
              importance 0.4 → session
              risk 0.99      → escalate (human) before any serialize
```

## Two things this clarifies

1. **"Drop" is a serialize outcome, not an absence of one.** Deciding *not* to persist still fixes a result (`decision = drop`) — auditable, replayable. Nothing falls through silently.
2. **It is where authority separates from the doer.** The routing is a *policy* call, not the measurer's. In UACP this is the **gate** (Guardian / Heartgate) + the per-phase **authority**: the doer comprehends and measures; a *separate* authority routes. That is exactly **no-self-attestation** (lifecycle invariant #5) at the primitive level.

## Why it is not a fourth primitive

The hinge is the *application of policy* to a measurement, not a new kind of work. Keeping the triad at three (and treating routing as the policy at the measure→serialize seam) preserves the clean atom; promoting routing to a peer step would blur it. The routing is still *deterministic given the policy* — same trustless discipline.

## To expand
- The routing table as data (measure-signal × policy → target), and whether it is itself a serialized, auditable artifact.
- Multi-target fan-out (one measurement → memory + audit + metric simultaneously).
- The escalation branch (risk over threshold → human/architecture verdict) as a first-class routing outcome ([verification harness](../verification-method/11-harness.md)).
