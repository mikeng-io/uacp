---
type: decision
title: The verdict — building gates did not converge, and cannot
description: Why the remediation lane was parked. Three rounds of external review on the grounding PR found new real defects each time; the last two show structurally why a declarative gate cannot reach them.
tags: [verify, convergence, verdict, semantic-verification]
timestamp: 2026-08-27
edges:
  - {dst: 60-remediation, rel: decides_on, provenance: asserted}
  - {dst: 20-grounding-defects, rel: extends, provenance: asserted}
---

# The verdict

This node supersedes the standing of `60-remediation.md`. The register's findings hold; the
*approach* to fixing them did not.

## What happened

PR #172 (`feat/verify-grounding`) built grounding gates — the conformance floor M1–M5 plus
per-phase grounding. It went through three rounds of external review. Each round found **new,
real defects the gates had missed**, in different classes each time: 6, then 4, then 8, then 2
more on `545e3886` (2026-08-26).

**Non-convergence is the verdict.** A review loop that never runs dry is not a loop converging
slowly; it is evidence that the mechanism under construction does not address the class.

## The two findings that show why

Both verified directly in the code on `origin/feat/verify-grounding`, and both land on the
`next`-response block — the M4 emission fix. So the fix for the emission gap introduced a
data-loss bug and a null-out bug, and verify passed both.

### P1 — the author's blind spot, by construction

`RunManifest` has no `deferred_items` field (17 fields; not among them). The transition path
reads it from the **raw** manifest, and the author knew about the asymmetry — the code says so
at `state_machine.py:952` (*"the state-machine RunManifest model does not model
deferred_items"*) and `:1226`. They compensated on the **read** side. `_save_manifest`
serializes `RunManifest`, so the **write** side strips the field: the mechanism built to replay
carried obligations deletes those obligations on the first transition after they are recorded.

This is the decisive case. Every UACP gate takes the author's declaration as input, and the
generative gate asks the author to author the checks. **An author can only author a check for a
failure they already suspect.** The comment at `:952` proves this author was thinking hard about
exactly this field — and no one writes "transition twice, confirm the field survives the
round-trip" unless they already suspect the round-trip is lossy. The defect was unreachable by
construction, not by oversight.

### P2 — declaration and reality diverging inside one function

`_state_policy()`'s docstring says the workspace copy is *"overlaid"*. The code is `out = raw` —
replace, not overlay. A partial workspace `config/state.yaml` therefore drops
`lifecycle_skill_contracts`, and every `next.required_skill` / `next.write_scope` becomes null.

A conformance gate reads the declaration. Here the declaration and the reality disagree **inside
a single function**, and only something reading the code catches it.

## The structural claim

> A declarative check covers only the anticipated. The unanticipated requires an adversarial
> reader on the real work.

More gates enlarge the *declared* surface — more kinds, more resolvers, more edge cases to get
right — without enlarging what is *verified*. That is why rounds produced new defect classes
rather than a shrinking tail: each round of gate-building added surface that the next round
found defects in.

Verification is a **semantic act**: run an adversarial screening against the real diff and
iterate on the fix delta until a round comes back clean — the fixpoint. It is not a gate
check.

## What this changes in this bundle

- **The register (`00`–`40`) stands.** Those 18 defects were found by reading the kernel, and
  the two above are the same method producing more. Nothing here is retracted.
- **`60-remediation.md` is re-scoped, not deleted.** M2 (the evidence-reference type) and M4
  (the response envelope) are corrections to specific broken mechanisms and remain valid on
  their own terms. **M3 — "ground the planes that already exist" — is gate-building and is
  parked** with the lane.
- **M0 still stands and matters more than before.** UACP is developed in an environment where
  UACP is inert (D-14). Whatever replaces the gate lane has to be felt during development or it
  will repeat this.

## Calibration set

P1 and P2 are the right acceptance test for whatever replaces the gates, precisely because both
were found by a reader with **less** context than UACP had: git-diff only, no run state, no
manifest, no ledger. The question to ask of any successor mechanism is not "does it pass its own
checks" but *"would it have found the `deferred_items` round-trip and the `out = raw` replace?"*

Planted-fault calibration against these two is the honest first gate on the next design.
