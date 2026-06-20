---
type: design
title: Per-Phase Profiles — the instantiation table (measure-mode + authority)
description: How the one primitive is parameterized per phase — what each phase comprehends, the mode of measure (generate/satisfy/check/distill), who holds authority, what gets serialized, and where the harness runs. Carries the D35 phase-keyed gates; encodes the EXECUTE generation-exclusion (no-self-attestation).
tags: [verification, phase-profiles, d35, measure-mode, authority]
timestamp: 2026-06-21
edges:
  - {dst: 00-the-primitive, rel: depends_on, provenance: derived}
---

# Per-Phase Profiles

## What this carries

The systematic, phase-parameterized spine: one **verification profile per phase**, attached to the **D35 phase-keyed structural gates** already in the kernel. Each profile is a row of the [primitive's](00-the-primitive.md) instantiation table made concrete and executable.

## A profile (schema sketch)

```
phase: PROPOSE
comprehend: the declared intent (scope_items, constraints)
measure_mode: generate            # generate | satisfy | check | distill
generates: executable assertions + constraint/metric nodes  # the gate's output
authority: proposing authority    # NOT the doer
serialize_to: proposal + assertions.yaml
harness_runs_here: true           # frozen measurements replay even now
exclusions: []                    # PROPOSE may generate
```

```
phase: EXECUTE
comprehend: the plan + code reality
measure_mode: satisfy             # produce evidence against frozen criteria
generates: NOTHING                # generation is gated out — no-self-attestation (invariant #5)
authority: the doer (blind)
serialize_to: checkpoints
harness_runs_here: true           # continuously measured while producing
exclusions: [generate]            # the structural guarantee
```

## The rule the profiles enforce

- **generate** mode ∈ {PROPOSE, PLAN} (define) and {VERIFY, RESOLVE} (check/distill) — by authority *separate from the doer*.
- **satisfy** mode = EXECUTE only, by the doer, who **cannot author its own pass criteria**.
- The harness (run frozen measurements) is permitted in **every** profile, EXECUTE included.

## To expand
- The full profile for each of TRIAGE/PROPOSE/PLAN/EXECUTE/VERIFY/RESOLVE (+ BRAINSTORM, light).
- How a profile binds into the D35 gate table (the gate invokes the loop with the phase's profile).
- The VERIFY profile's dual nature: run frozen criteria **and** generate checks for emergent reality.
