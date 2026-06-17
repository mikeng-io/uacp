---
type: digest
title: Goal-Driven Track — Kernel Contract
description: "Shipped kernel-contract mirror for the goal-driven lifecycle track; read when operating a run with track: goal-driven"
tags: [goal-driven, lifecycle, track, kernel]
timestamp: 2026-06-17
resource: docs/architecture/0016-goal-driven-track.md
---

# Goal-Driven Track — Kernel Contract (mirror)

> **Read when** a lifecycle skill is operating a run whose `track: goal-driven`.
> Origin of record: ADR-0016 (`docs/architecture/0016-goal-driven-track.md`) — not
> shipped with skills; this file is the shipped, citable mirror of the *enforced
> contract*. The authority is the code cited below, not this prose.

UACP has two lifecycle **tracks** under one phase graph: `standard` (default) and
`goal-driven` (semantic/exploratory work whose success criterion is not specifiable
as a verifiable artifact before EXECUTE). The five phases are reused unchanged;
per-run transitions are forward-only in both tracks (no back-edges).

## Where the contract lives in code (authority)

- `skills/uacp-core/scripts/engines/domain/checkpoint.py` — `CheckpointEntry`
  (the checkpoint manifest record schema, `extra="forbid"`).
- `skills/uacp-core/scripts/engines/domain/budget.py` — `ConvergenceBudget`
  (`max_checkpoints` required, int > 0).
- `skills/uacp-core/scripts/core.py` — Heartgate gates:
  `_validate_convergence_budget_gate` (PROPOSE→PLAN), `_triage_track` (track
  binding), `_validate_goal_driven_checkpoint_gate` (EXECUTE→VERIFY coherence),
  `_validate_goal_driven_closure_gate` (VERIFY→RESOLVE).
- `skills/uacp-state/scripts/state_machine.py` — `handle_init` (`track`,
  `goal_id`, `inherits_from`; `_VALID_TRACKS`), `list_runs_for_goal`.

## The persistent goal + run-chain

A goal-driven run anchors to a **persistent goal** (`goal_id` on the run manifest),
the invariant that does not move. Rollback is NOT an in-run rewind: it is a **new
forward run** under the held goal (`uacp_state_write` init with the same `goal_id`
and `inherits_from: <prior run_id>`), which inherits the parent's triage/proposal/
plan output references. A goal is realized as a *chain* of such runs.

## Convergence budget (PROPOSE→PLAN — BLOCKS without it)

PROPOSE must write `proposals/{run_id}-convergence-budget.yaml`:

```yaml
convergence_budget:
  max_checkpoints: 8     # REQUIRED, integer > 0 — the enforced cap
  max_spend: null        # optional, declare-only (not enforced)
  max_wall_clock: null   # optional, declare-only (not enforced)
```

Without it (or with non-positive `max_checkpoints`), Heartgate blocks PROPOSE→PLAN.
The cap counts `CHECKPOINT` entries across the goal's **whole run-chain**.

## Track binding (un-forgeable)

The run manifest `track` must equal the TRIAGE artifact's `track`
(`proposals/{run_id}-triage*.yaml`). A manifest claiming `goal-driven` over a TRIAGE
artifact that did not decide it fails closed — a worker may not self-select the
track to relax the PIV-artifact gate.

## Checkpoint manifest (EXECUTE)

Each EXECUTE probe is recorded as a `gate: CHECKPOINT` gate-ledger entry (via
`uacp_gate_ledger_append`) carrying a `CheckpointEntry`:

```yaml
checkpoint_id: "<unique within run>"
run_id: "<this run>"
goal_id: "<the held goal>"
phase: execute
what_changed: "what this probe produced/changed"
why: "why this probe, toward the goal"
evidence: "executions/{run_id}/cp-3-hero.png"   # REAL governed-root artifact; prose is rejected
verdict: keep | roll_back | restart
invariant: "the goal invariant this probe is judged against"
rolled_back_to: "<checkpoint_id>"               # only when verdict=roll_back
```

`evidence` must reference a real, governed-root-contained artifact — Heartgate runs
the same no-self-attestation / no-fabrication check it applies to all gate-ledger
evidence. Extra fields BLOCK (`extra="forbid"`).

## EXECUTE→VERIFY coherence (manifest substitutes for the PIV *artifact*)

For a goal-driven run, a COHERENT checkpoint manifest substitutes for the
PIV/execution-evidence *artifact* gate. "Coherent" =: non-empty; every entry
validates as `CheckpointEntry`; every `evidence` ref exists and is contained; total
count ≤ `max_checkpoints` (exactly the cap PASSES; cap+1 BLOCKS); the **final entry's
verdict is `keep`** (a dangling `roll_back`/`restart` has not converged). The PIV
*ledger* gate, authority/containment, and no-fabrication engines still fire.

## VERIFY→RESOLVE closure (coherence + goal binding)

At closure the manifest must be coherent AND the final (promoted) checkpoint's
`goal_id` must equal the run manifest's `goal_id` — a result must satisfy *this*
run's goal. The standard closure invariants (computed engines, Heartgate coherence,
no-fabrication, containment) fire unchanged. RESOLVE then closes the goal: records
the converged checkpoint + the run-chain, and releases the goal anchor
(deregisters the goal's runs).
