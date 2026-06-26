---
type: design
title: Derivable Work-Unit Status Model
description: >-
  Defines the five per-work_unit status states (planned/in_progress/executed/verified/blocked),
  how each is derived on-demand from PIV + after_work_unit checkpoints, the resume procedure
  for interrupted EXECUTE runs, goal-driven track boundary, and the optional required field.
tags: [status, derivation, resume, work-unit]
timestamp: 2026-06-26
edges: []
---

# Derivable Work-Unit Status Model

## Status Derivation (standard track only)

Status is computed on-demand from existing artifacts — not stored. Given a
`run_id` and access to `governed_root`:

| Derived status | Evidence |
|---|---|
| `planned` | work_unit declared in PIV; no checkpoint with matching `work_unit_id` |
| `in_progress` | checkpoint exists with matching `work_unit_id`, type ≠ `after_work_unit` |
| `executed` | checkpoint of type `after_work_unit` exists with matching `work_unit_id` |
| `verified` | VERIFY assessment exists; all obligations for this unit have `state` ∈ {pass, warn, deferred} |
| `blocked` | any obligation for this unit has `state: block` |

**Key:** `after_work_unit` is an existing checkpoint type
(`_CHECKPOINT_TYPES` in `schema.py:47`). EXECUTE writes this checkpoint when
a work_unit is complete. No additional write obligation.

## Why Derivation, Not Storage

A stored status file can drift: if an agent is interrupted after writing the
checkpoint but before writing the status update, the file lies. Derivation
from checkpoints is always consistent because checkpoints are the primary
artifact — they're what EXECUTE is already obligated to write.

## Resume Procedure

When an agent is interrupted mid-EXECUTE and resumes:

1. Load the PIV contract (`plans/{run_id}-piv.yaml`) — this lists all
   declared `work_units`.
2. Scan `executions/{run_id}-checkpoint-*.yaml` — collect all
   `work_unit_id` values where `checkpoint_type == "after_work_unit"`.
3. The intersection gives `executed` units. The remainder are `planned` or
   `in_progress` (check for any non-`after_work_unit` checkpoint to
   distinguish).
4. Resume from the first `planned` or `in_progress` unit.

This procedure requires no additional state — the checkpoints are the record.

## Goal-Driven Track

The goal-driven track does not use PIV work_units. "Tasks" are checkpoint
iterations toward a persistent goal. Status is:
- Current checkpoint count vs `max_checkpoints` (convergence budget)
- Latest checkpoint verdict: `keep` / `roll_back` / `restart`
- Whether the final manifest entry is `keep` (ready to exit EXECUTE)

These are already tracked and gated by `_validate_goal_driven_checkpoint_gate`.
The wu-status derivation defined above does not apply. An interrupted
goal-driven agent resumes by reading the checkpoint manifest and continuing
from the last `keep` checkpoint.

## `required` Field on work_unit

Adding optional `required: boolean` to the PIV `work_unit` schema (default
`true`). The gate only blocks on units where `required` is `true` or absent.
PLAN sets this when a work_unit is known to be optional (e.g. a stretch goal
or a conditional path).
