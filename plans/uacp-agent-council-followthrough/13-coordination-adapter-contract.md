# 13 — Coordination Adapter Contract

Status: draft-ready for review  
Created: 2026-05-12T19:55:41.570731+00:00  
Scope: Substrate-neutral coordination contract for UACP EXECUTE task graphs and future phase controllers.

---

## 1. Purpose

This document defines the contract between UACP/Agent Council phase controllers and any coordination substrate used to persist, assign, and observe work units.

Hermes Kanban is the current implementation target, but the contract is intentionally adapter-neutral.

```text
UACP / phase controller = decides topology, authority, reruns, escalation, and phase outcome
Coordination adapter = persists and dispatches work units
Worker runtime = performs bounded work
UACP artifacts = canonical evidence and state
```

## 2. Non-goals

The coordination adapter does not:

- decide UACP phase transitions,
- own governance policy,
- replace Agent Council deliberation,
- decide whether evidence is sufficient,
- silently broaden side-effect authority,
- become the source of truth for UACP state.

## 3. Required capabilities

Every adapter used for UACP EXECUTE coordination must support these operations.

```yaml
coordination_adapter_contract:
  create_unit: required
  assign_unit: required
  declare_dependencies: required
  attach_context: required
  attach_artifact_or_comment: required
  read_unit_outputs: required
  mark_state: required
  retry_or_rerun_unit: required
  preserve_provenance: required
```

Optional but useful:

```yaml
optional_capabilities:
  watch_or_poll_state: optional
  notify: optional
  heartbeat: optional
  reclaim_or_cancel_claim: optional
  priority_queueing: optional
  tenant_or_workspace_partition: optional
```

## 4. Core data objects

### Work unit

A work unit is the adapter representation of a bounded UACP EXECUTE task.

```yaml
work_unit:
  unit_id: "adapter-specific id"
  title: "..."
  body: "human-readable task body"
  status: todo | ready | running | done | blocked | crashed | timed_out | archived
  assignee: "profile/runtime/worker id or null"
  priority: 0
  parents: []
  workspace: "scratch | dir:<path> | worktree | adapter-specific"
  context_ref: "UACP context payload or artifact path"
  created_by: "..."
  created_at: "..."
```

### UACP context payload

```yaml
uacp_context:
  uacp_run_id: "..."
  uacp_phase: execute
  policy_version: "0.1"
  guardian_policy_version: "0.1"
  authority_artifact: "..."
  declared_authority: "..."
  declared_side_effects: []
  workspace_policy: "..."
  runtime_surface: "..."
  profile_id: null
  task_manifest_id: "..."
```

### Unit output

```yaml
unit_output:
  unit_id: "..."
  status: done | blocked | crashed | timed_out | protocol_violation
  summary: "..."
  metadata: {}
  artifacts: []
  findings: []
  error: null
  completed_at: "..."
```

### Provenance event

```yaml
provenance_event:
  unit_id: "..."
  event_kind: created | assigned | claimed | spawned | heartbeat | completed | blocked | crashed | timed_out | retried | commented | archived
  actor: "adapter/controller/worker id"
  timestamp: "..."
  payload: {}
```

## 5. Operation semantics

### `create_unit`

Creates a bounded work unit from an EXECUTE task schema.

Must preserve title, body/context, allowed/forbidden surfaces, authority artifact reference, side-effect declarations, runtime/profile selection, and verification/completion contract.

### `assign_unit`

Assigns a work unit to a profile, runtime, worker queue, or human lane.

Assignment is not authority. The UACP context still controls what the worker may do.

### `declare_dependencies`

Declares parent/child readiness relationships.

A child must not become runnable until required parent units are complete or explicitly accepted/deferred by the controller.

### `attach_context`

Attaches UACP context payload and task schema data to the work unit.

Context must be retrievable by workers and by the controller after the fact.

### `attach_artifact_or_comment`

Stores supplementary evidence, findings, review notes, diagnostics, or human decisions.

Comments/artifacts are evidence surfaces, not authority by themselves.

### `read_unit_outputs`

Returns summaries, metadata, artifacts, findings, errors, and latest state.

The controller uses this to adjudicate pass/warn/block and decide reruns.

### `mark_state`

Marks a unit complete, blocked, archived, or otherwise terminal.

Adapters must distinguish successful completion from process exit. A worker exiting without required completion/block is a protocol violation, not success.

### `retry_or_rerun_unit`

Supports safe retry or rerun semantics.

Rules:

- If no side effects occurred and failure appears transient, adapter may reclaim/retry the same unit.
- If artifacts changed or reviewer feedback exists, create a new linked fix/rerun unit.
- Repeated protocol violations should block or escalate rather than loop forever.

### `preserve_provenance`

Records event history sufficient for audit and debugging.

Minimum provenance:

- created,
- assigned,
- claimed/spawned where relevant,
- completed/blocked/crashed/timed_out,
- actor/profile/runtime,
- timestamps,
- error payloads.

## 6. Failure states

Adapter-visible failures must be normalized for the controller.

```yaml
failure_states:
  blocked:
    meaning: worker explicitly requested input/decision or hit declared blocker
    controller_action: classify and unblock/fix/human-checkpoint
  crashed:
    meaning: worker process died unexpectedly
    controller_action: record crash, retry if safe, otherwise diagnostic/fix/block
  timed_out:
    meaning: worker exceeded runtime cap
    controller_action: split, extend, escalate, or block
  protocol_violation:
    meaning: worker exited or claimed success without required complete/block/evidence contract
    controller_action: do not treat as success; retry once if idempotent, otherwise recovery/escalation
```

## 7. Hermes Kanban mapping

```yaml
hermes_kanban_mapping:
  create_unit: hermes kanban create
  assign_unit: --assignee
  declare_dependencies: --parent / link
  attach_context: --body and --uacp-context-json
  attach_artifact_or_comment: comment fields / metadata / artifact paths
  read_unit_outputs: hermes kanban show --json
  mark_state: complete / block / unblock / archive
  retry_or_rerun_unit: reclaim / reassign / create linked follow-up task
  preserve_provenance: task events and runs
  notify: notify-subscribe
```

Current known issue:

```text
Default-profile workers have crashed or protocol-violated during UACP design dogfood. The adapter contract must expose this clearly to controllers instead of hiding it behind generic failure.
```

## 8. Portability requirements

A future custom UACP queue, Linear, GitHub Issues, Notion, or workflow engine can implement the contract if it can preserve:

- bounded work unit identity,
- assignment,
- dependencies,
- UACP context,
- output/evidence metadata,
- state transitions,
- failure classification,
- provenance events.

Adapter-specific fields are allowed, but UACP-owned fields must remain portable.

## 9. UACP-owned versus adapter-owned

### UACP-owned

- lifecycle phase,
- authority and side effects,
- phase-local/composite granularity,
- human checkpoint policy,
- evidence obligations,
- phase exit decision,
- canonical artifacts/state,
- Agent Council protocol.

### Adapter-owned

- queue mechanics,
- task IDs,
- assignment plumbing,
- dependency activation mechanics,
- worker spawn/claim mechanics,
- notifications,
- event storage implementation.

## 10. Controller usage pattern

```text
controller reads approved plan
  -> compiles EXECUTE task schemas
  -> adapter.create_unit for each bounded unit
  -> adapter.declare_dependencies
  -> adapter.assign_unit
  -> adapter.watch_or_poll_state
  -> adapter.read_unit_outputs
  -> controller adjudicates outcome
  -> adapter.retry_or_rerun_unit or create follow-up units
  -> controller writes UACP evidence artifact
```

The controller never delegates phase-exit judgment to the adapter.

## 11. Verification checklist

An adapter is suitable for UACP EXECUTE coordination only if:

- it preserves UACP context with each work unit,
- it exposes terminal and failure states distinctly,
- it preserves worker/runtime provenance,
- it can attach or reference evidence artifacts,
- it supports dependencies or equivalent gating,
- it supports safe retry/rerun semantics,
- it does not own UACP phase state,
- it can be replaced without rewriting UACP doctrine.

## 12. Current recommendation

For the current UACP reramp:

```text
Use Hermes Kanban as the reference adapter once worker reliability is diagnosed.
Continue doctrine/design in-session until then.
Design all controller/task schemas against this adapter-neutral contract.
```
