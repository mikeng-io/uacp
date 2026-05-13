# 12 — Current Execution Posture After Kanban Dogfood

Status: active decision note  
Created: 2026-05-12T19:48:09.389044+00:00  
Scope: Current UACP reramp execution posture after repeated default-profile Kanban worker failures.

---

## Decision

For the current UACP reramp, continue remaining doctrine/design work primarily in the main session, using `delegate_task` for bounded same-profile critique/research when useful.

Pause further Kanban-worker dogfooding for UACP design tasks until the default-profile Kanban worker crash/protocol behavior is diagnosed.

## Rationale

Two consecutive UACP design tasks exposed Kanban worker reliability issues:

- `t_f66dbea8` — worker crashed once, then exited cleanly without calling `kanban_complete` or `kanban_block`.
- `t_7676ce1f` — worker crashed twice with `pid not alive`.

In both cases, main-session recovery was faster and more reliable than waiting for Kanban retries.

Because current UACP reramp work is still primarily doctrine/design/schema work, it does not yet require durable asynchronous worker execution. The main session can perform this work directly, with `delegate_task` scratch critique where useful.

## Current posture

```text
Main session:
  primary executor for remaining UACP design/docs/config work

delegate_task:
  optional same-profile scratch critique/research/review

Kanban:
  pause for UACP design dogfood until worker crash/protocol issue is diagnosed
  still documented as EXECUTE coordination adapter target
  not removed from architecture

External runtime:
  reserve for heavy code/runtime debugging or independent review
```

## What remains saved

The important architecture decisions are already captured in:

- `09-current-operating-model-and-future-slots.md`
- `10-execute-task-schema.md`
- `11-full-auto-execute-phase-controller.md`

This note adds only the operational decision: **do the rest in-session for now because Kanban worker execution is slower/less reliable for these design tasks.**

## Follow-up options

### Option A — Continue UACP reramp in-session

Use main session to finish remaining design artifacts and only use Kanban again after worker stability improves.

### Option B — Diagnose Kanban worker crash

Create a separate Hermes-runtime debugging task to investigate default-profile worker crashes and protocol violations.

This should be treated as Hermes core/runtime work, not UACP doctrine work.

### Option C — External runtime diagnostic

If debugging the crash is non-trivial, use Codex/Claude Code as an external runtime for independent code/runtime inspection.

## Locked statement

Until superseded:

```text
For the current UACP reramp, main-session execution is preferred over Kanban workers for doctrine/design tasks. Kanban remains the target coordination adapter for EXECUTE, but further dogfood should wait until worker crash/protocol reliability is diagnosed.
```
