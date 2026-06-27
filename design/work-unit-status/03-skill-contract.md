---
type: design
title: Skill Contract Changes
description: >-
  The changes to uacp-plan, uacp-execute, and uacp-verify skill docs required to support
  work-unit status derivation: PLAN declares work_units + optional required flag, EXECUTE
  writes after_work_unit checkpoints, VERIFY surfaces the derived status per unit.
tags: [skill, plan, execute, verify, resume]
timestamp: 2026-06-26
edges: []
---

# Skill Contract Changes

## uacp-plan/SKILL.md — Mark work_unit `required`

Add to the PIV authoring section:

> Each `work_unit` may carry an optional `required: false` flag to mark it
> as non-blocking for the EXECUTE→VERIFY gate. Omit `required` or set it to
> `true` for units that must be completed before VERIFY. Mark stretch goals,
> conditional paths, or best-effort units as `required: false`.

## uacp-execute/SKILL.md — Completion checkpoint + resume

Add to the checkpoint section:

> **Completion signal:** When a work_unit is finished, write a checkpoint of
> type `after_work_unit` with the `work_unit_id` field set. This checkpoint
> is the sole signal that a unit is complete — Heartgate derives coverage from
> it directly. No separate state write is needed.
>
> **Resume after interruption:** To reconstruct where execution left off:
> 1. Load `plans/{run_id}-piv.yaml` — lists all declared `work_units`.
> 2. Scan `executions/{run_id}-checkpoint-*.yaml` for checkpoints where
>    `checkpoint_type == "after_work_unit"` — these are the executed units.
> 3. Resume from the first work_unit with no matching `after_work_unit` checkpoint.
>
> Do not re-execute units that already have an `after_work_unit` checkpoint.

## uacp-verify/SKILL.md — No change

VERIFY already reads the PIV + checkpoints. No write-back required.

## Goal-Driven Track — No change

Goal-driven EXECUTE does not use work_units or `after_work_unit` checkpoints.
Resume on goal-driven: read the checkpoint manifest, find the last `keep`
verdict checkpoint, continue the probe loop from there.
