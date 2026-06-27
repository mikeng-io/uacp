---
type: design
title: Work-Unit Status Tracking — Overview and Decision Log
description: >-
  Why re-derivable per-work_unit status tracking is needed, the seven decisions that
  define the approach (derivation from PIV + after_work_unit checkpoints, no stored
  status artifact, optional required flag, goal-driven track boundary), and the
  accepted-but-deferred backlog items (B1 no-checkpoint self-gate, B2 backward-compat).
tags: [piv, heartgate, execute, verify, work-unit, status, goal-driven]
timestamp: 2026-06-26
edges: []
---

# Work-Unit Status Tracking — Design Bundle (v2)

## Why

The current model has no per-task status signal: you can't tell whether
task 3B is done, in progress, or blocked without scanning checkpoint files
manually. Heartgate also only checks that a PIV exists, not that every
declared work_unit has a completion checkpoint — so a run that executed 2 of
5 work_units can legally transition to VERIFY.

**Re-derivability is the core constraint:** if an agent is interrupted
mid-EXECUTE and resumes, it must be able to reconstruct "where am I" from
existing artifacts without depending on a separate state file that may not
have been written. This rules out an explicit status index.

## Decision Log

| # | Decision | Rationale |
|---|---|---|
| D1 | Status is derived on-demand from PIV + checkpoints — no separate status artifact | An explicit file can drift if the agent is interrupted before the write; derivation from checkpoints is always consistent |
| D2 | `executed` is signalled by a checkpoint of type `after_work_unit` referencing the `work_unit_id` | `after_work_unit` is an existing checkpoint type; `next_phase_readiness: ready` is phase-level, not per-unit |
| D3 | Gate extends `forced_execute_evidence_blockers` in `heartgate.py` (standard track only) | Existing method is already the EXECUTE→VERIFY forced-path gate; goal-driven branch is already handled separately |
| D4 | Goal-driven track: wu-status derivation is N/A | Goal-driven runs use checkpoint-toward-goal + convergence budget, not PIV work_units; existing `_validate_goal_driven_checkpoint_gate` handles them |
| D5 | Add optional `required: boolean` to PIV `work_unit` schema | Allows PLAN to mark non-critical units as optional; gate only blocks on `required: true` units lacking completion |
| D6 | Resume: an agent scans PIV + after_work_unit checkpoints to know what to continue | No new protocol — the artifacts already contain the answer; skill docs add the resume procedure |
| D7 | Commit per-task when suite is green; batch constant-only tasks with first consuming task | Constant changes have no test signal; first task that exercises them is the natural commit boundary. Automated agents: commit on `keep` verdict only |

## Backlog (accepted, deferred — not in this change)

- **B1 — no-checkpoint self-gate.** A PIV declaring required work_units but with
  ZERO checkpoints passes `forced_execute_evidence_blockers` (returns `[]`). This
  is the pre-existing intentional adaptive boundary (D7): no checkpoint = bare /
  ungoverned EXECUTE. The agent-path adaptive gate (`validate_transition`) covers
  the PIV-with-no-checkpoints case separately. Tightening the forced path to also
  block a checkpoint-less PIV-bearing run is a possible follow-up; deferred to
  avoid changing established self-gate semantics. (Raised by cross-provider review.)
- **B2 — backward-compat for in-flight runs.** Any run already in EXECUTE with a
  PIV containing `work_units` but no `after_work_unit` checkpoints will be blocked
  at EXECUTE→VERIFY after this ships. New convention → no active runs expected to
  hit it. If one does, it must write the missing `after_work_unit` checkpoints or
  amend the PIV. No migration shim built; accepted.
