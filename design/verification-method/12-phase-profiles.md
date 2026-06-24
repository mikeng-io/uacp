---
type: design
title: Per-Phase Profiles — the verification payload carried into the phase-keyed gate
description: How the one primitive is parameterized per phase — the measure-mode (generate/satisfy/check/distill), who holds authority, and the eventual structural exclusions — carried as a PAYLOAD into the D35 phase-keyed gates already wired in the kernel. References the canonical phase→kind→gate crosswalk rather than restating it; covers BRAINSTORM (first-class) and the goal-driven track (VERIFY judges a checkpoint manifest, not a fixed package). Encodes the EXECUTE generation-exclusion (no-self-attestation), noting it is not yet structurally enforced.
tags: [verification, phase-profiles, d35, measure-mode, authority, goal-driven, brainstorm]
timestamp: 2026-06-24
edges:
  - {dst: 00-the-primitive, rel: depends_on, provenance: derived}
---

# Per-Phase Profiles

## What this carries

A **verification profile per phase**: the verification-specific payload that parameterizes the one primitive ([00-the-primitive](00-the-primitive.md)) for each lifecycle phase. The payload is two specializing columns — **the mode of `measure`** and **who holds authority** — plus the eventual **structural exclusions** (below). It is *not* the phase→artifact-kind→gate mapping: that is canonical and lives in [`24-phase-crosswalk`](../comprehend-measure-serialize/24-phase-crosswalk.md). This node carries only what verification adds on top of that crosswalk.

## The binding point already exists; the profile payload is the gap

The D35 **phase-keyed structural gates** are not aspirational — they are wired today. Each phase declares a `graph_invariant` exit invariant (`plan_exit`, `execute_exit`, `verify_exit`) in `STAGE_PHASE_EXIT_INVARIANTS` (`engines/domain/phase_transitions.py`), keyed `<from_phase>_exit`, and Heartgate runs the phase-scoped structural subset of the graph engine at the transition where that check's inputs first complete (`_validate_phase_exit_invariants`). A dropped intent / orphan / missing coverage / contradiction therefore fails **at the boundary**, not only at terminal closure.

So the binding *mechanism* is built. What is missing is the **payload carried into it**: today the gate runs a fixed structural subset; it does not yet receive a per-phase verification profile (the measure-mode + authority + exclusions) that would let it also enforce *which* generative discipline is in force at that phase. The profile is the net-new content; the gate is the seam it plugs into.

## A profile (schema sketch)

```
phase: PROPOSE
measure_mode: generate            # generate | satisfy | check | distill
authority: proposing authority    # the role permitted to run measure here; NOT the doer
exclusions: []                    # PROPOSE may generate
harness_runs_here: true           # frozen measurements replay even now (run_all_engines @ every transition)
```

```
phase: EXECUTE
measure_mode: satisfy             # produce evidence against frozen criteria
authority: the doer (blind)
exclusions: [generate]            # the structural guarantee — see caveat below
harness_runs_here: true           # continuously measured while producing
```

(The phase's `comprehend` input and `serialize_to` kind are *not* repeated here — read them from the crosswalk. The profile names the verification mode; the crosswalk names the artifact.)

## The rule the profiles enforce

- **generate** mode ∈ {PROPOSE, PLAN} (define) and {VERIFY, RESOLVE} (check / distill) — by authority *separate from the doer*.
- **satisfy** mode = EXECUTE only, by the doer, who **cannot author its own pass criteria**.
- The harness (replay frozen measurements) is permitted in **every** profile, EXECUTE included — consistent with `run_all_engines` firing at every transition.

## The full per-phase table (the payload)

Standard track. The `measure`/`authority` columns are the verification payload; the crosswalk supplies the matching gate + kind.

| Phase | measure — mode | authority | exclusions |
|---|---|---|---|
| **BRAINSTORM** | classify (admissible to governance?) | explorer | `[generate]` — no frozen criteria authored pre-governance |
| TRIAGE | classify (scope / risk / granularity / track) | router | `[generate]` |
| PROPOSE | **generate** success criteria (assertions) | proposing authority | `[]` |
| PLAN | **generate** decomposition checks (coverage, per-`work_unit` obligations) | planning authority | `[]` |
| **EXECUTE** | **satisfy** the frozen criteria (produce evidence) | **the doer (blind)** | **`[generate]`** |
| VERIFY | **check** criteria + **generate** checks for emergent reality | separate authority | `[]` |
| RESOLVE | **distill** what held | curator | `[]` |

### BRAINSTORM is first-class (not a footnote)

BRAINSTORM is now a **first-class phase** in the kernel grammar, with a **required exit invariant**: `brainstorm/*/07-scope-package.yaml` must exist with non-empty title/description/in_scope, declared side-effects, documented authority source, and a valid routing advisory (`STAGE_PHASE_EXIT_INVARIANTS["brainstorm"]`, `phase_transitions.py`). Its verification profile is **classify, not generate**: BRAINSTORM `measure`s one thing — *is this scope admissible to governance?* — and serializes the scope-package as its evidence. It authors **no frozen success criteria** (that begins at PROPOSE), so `generate` is excluded here too. The exit invariant *is* its measure-discipline: a malformed scope-package fails the brainstorm→triage boundary.

### The VERIFY profile's dual nature

VERIFY alone runs **both** halves of the primitive at once: it *replays* the frozen criteria (the harness checking PROPOSE/PLAN's assertions) **and** *generates* new checks for emergent reality the plan could not foresee. That dual mode is why VERIFY is the richest profile — and why its `measure` cannot be reduced to a single verb.

## The goal-driven track variant

On the **goal-driven track** ([ADR-0016]; resolved by `triage_track`, `run_track` in `engines/heartgate/goal_driven.py`), the VERIFY profile's `measure` changes target. Instead of checking a **fixed criteria package** authored at PROPOSE/PLAN, VERIFY judges a **checkpoint manifest** — the run-appended ledger of checkpoint entries loaded by `load_checkpoint_manifest`, whose **final entry** carries the promoted result. The measure-discipline becomes: *is the final checkpoint a `keep`, bound to THIS run's `goal_id`, and coherent with the manifest's history?* (`final_checkpoint_entry`, the goal-driven closure gate).

| | standard track | goal-driven track |
|---|---|---|
| VERIFY `measure` target | the frozen criteria package | the **checkpoint manifest** (final entry + goal binding) |
| what is "done" | every obligation has a verdict | final checkpoint = `keep`, goal-bound, manifest-coherent |
| authority | separate authority | separate authority (unchanged) |

The other phases' profiles are track-invariant; only VERIFY's measure-target swaps. This keeps the standard path byte-identical (the goal-driven branch fires only behind `track == "goal-driven"`).

## Honest caveat — the EXECUTE generation-exclusion is not yet structurally enforced

The **`exclusions: [generate]` on EXECUTE is the load-bearing thesis** ([00-the-primitive](00-the-primitive.md): the doer must not author its own pass condition — UACP invariant #5, no self-attesting closures). But it is **not yet a structural field in the kernel today.** What the kernel enforces at EXECUTE is `STAGE_FORBIDDEN_TOOLS["execute"]` (an explicitly empty list — terminal/execute_code *permitted* there) and the `execute_exit` graph invariant (checkpoint coverage). There is **no per-phase `exclusions` field** the gate reads. So this exclusion is **genuine net-new to build**: a profile field carried into the existing `graph_invariant` seam. Until then, the no-self-attestation guarantee rests on the lifecycle's authority separation (a separate VERIFY authority supplies the verdict EXECUTE cannot self-grant), not on a structural `generate`-block at the EXECUTE boundary.

## To build
- The `exclusions` profile field + its enforcement at the phase-keyed `graph_invariant` gate (net-new).
- The profile-payload carrier: how the gate receives a phase's profile rather than a fixed structural subset.
- Reconcile the BRAINSTORM/goal-driven profile wording against the live SKILL.md once the verification skill lands.

---

**Changes:** (1) BRAINSTORM promoted to a first-class profile row with its `07-scope-package` exit invariant and classify-not-generate measure-mode; (2) wove in the goal-driven track — VERIFY's measure judges the checkpoint manifest (final entry + goal binding), not a fixed package; (3) stopped restating the phase→kind→gate mapping (now references `24-phase-crosswalk`) and reframed "to expand: how a profile binds" as "binding point exists, profile payload is the gap," with the EXECUTE `exclusions:[generate]` exclusion kept but flagged as net-new (not yet structurally enforced).
