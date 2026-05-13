# 11 — Full-Auto EXECUTE Phase Controller

Status: draft-ready for review  
Updated: 2026-05-12T19:45:32.085632+00:00  
Scope: Current UACP reramp; full-auto `EXECUTE` phase only, not full lifecycle autonomy.

---

## 1. Purpose

This document defines how the current UACP reramp can run an entire `EXECUTE` phase autonomously using:

```text
EXECUTE phase controller
  + coordination adapter task graph
  + worker runtimes
  + evidence/verification artifacts
```

Hermes Kanban is the current coordination adapter, but the controller logic must stay adapter-neutral.

## 2. Boundary

This design is only for `EXECUTE`.

It does not make `TRIAGE`, `PROPOSE`, `PLAN`, `VERIFY`, or `RESOLVE` full-auto by default.

Current locked mode remains:

```text
TRIAGE / PROPOSE / PLAN / VERIFY / RESOLVE:
  main-orchestrator-led by default
  may use delegate_task or external runtime when justified

EXECUTE:
  may be full-auto through phase controller + coordination adapter
```

## 3. Why this is needed

The current UACP reramp needs a way to run non-trivial implementation work without keeping the Telegram/chat session as the synchronous execution loop.

The first dogfood task (`t_f66dbea8`) exposed a real failure mode: the worker exited cleanly without calling `kanban_complete` or `kanban_block`. The controller must handle this explicitly instead of assuming worker success.

## 4. Core distinction

```text
Phase controller = active control loop for EXECUTE
Coordination adapter = creates/assigns/records task units
Worker runtime = performs bounded task work
Evidence artifact = canonical phase record
```

Kanban is not the controller. Kanban is only the current adapter.

## 5. Controller responsibilities

The EXECUTE controller is responsible for:

1. Reading the approved PLAN / authority artifact.
2. Deriving bounded EXECUTE work units using `10-execute-task-schema.md`.
3. Creating tasks through the coordination adapter.
4. Assigning each task to a runtime surface/profile when justified.
5. Monitoring task state and worker runs.
6. Reading worker summaries, metadata, artifacts, and findings.
7. Detecting incomplete, weak, missing, or invalid evidence.
8. Creating fix, rerun, regroup, or follow-up tasks.
9. Escalating to external runtime or human checkpoint when rules trigger.
10. Recording crash/timeout/protocol-violation evidence.
11. Writing the EXECUTE evidence artifact.
12. Declaring EXECUTE phase readiness for VERIFY as `pass`, `warn`, or `block`.

## 6. Required inputs

```yaml
controller_input:
  run_id: "..."
  phase: execute
  authority_artifact: "plans/... or proposals/..."
  execute_task_schema: "plans/uacp-agent-council-followthrough/10-execute-task-schema.md"
  coordination_adapter: hermes_kanban | other
  allowed_files: []
  forbidden_files: []
  allowed_surfaces: []
  forbidden_surfaces: []
  side_effect_boundaries: []
  verification_expectations: []
  human_checkpoint_triggers: []
  external_runtime_policy: []
```

## 7. Required outputs

```yaml
controller_output:
  task_graph: []
  task_results: []
  worker_failures: []
  rerun_decisions: []
  escalation_decisions: []
  evidence_artifact: "verification/... or executions/..."
  execute_readiness: pass | warn | block
  residual_risks: []
  recommended_next_phase: verify | replan | human_checkpoint
```

## 8. Controller state model

```yaml
execute_controller_state:
  run_id: "..."
  controller_id: "..."
  phase: execute
  status: initializing | dispatching | monitoring | adjudicating | closing | blocked
  tasks:
    - task_id: "..."
      status: ready | running | done | blocked | crashed | timed_out | protocol_violation | accepted | rejected | rerun_requested
      runtime_surface: hermes_profile_worker | delegate_task | external_runtime | tool_adapter | evidence_service | human_checkpoint
      profile_id: null
      external_runtime: null
      evidence_artifacts: []
      findings: []
      failure_count: 0
      last_error: null
  phase_findings: []
  open_decisions: []
```

## 9. Task graph lifecycle

```text
approved PLAN
  -> controller derives EXECUTE work units
  -> controller creates coordination-adapter tasks
  -> workers execute bounded tasks
  -> workers complete/block with evidence
  -> controller reads outputs
  -> controller adjudicates pass/warn/block per task
  -> controller creates fix/rerun/regroup tasks if needed
  -> controller writes EXECUTE evidence artifact
  -> controller declares VERIFY readiness
```

## 10. Worker state handling

### `ready`

Task is queued but not started.

Controller action:

- wait or dispatch depending on adapter mode,
- verify dependencies are satisfied,
- flag stale ready tasks if they exceed queue SLA.

### `running`

Task has active worker claim.

Controller action:

- monitor heartbeat/runtime cap,
- avoid duplicate work unless claim expires,
- collect live logs only if adapter supports it.

### `done`

Task completed.

Controller action:

- read completion summary and metadata,
- verify required completion fields,
- inspect evidence artifacts,
- mark accepted, warn, or rejected.

### `blocked`

Worker explicitly blocked.

Controller action:

- read block reason,
- classify as scope ambiguity, missing input, protected action, tool/runtime failure, or human decision,
- create unblock/fix task or human checkpoint.

### `crashed`

Worker process died unexpectedly.

Controller action:

- record crash evidence,
- inspect run error and partial artifacts if available,
- retry only if failure appears transient and retry budget remains,
- otherwise create diagnostic/fix task or block phase.

### `timed_out`

Worker exceeded max runtime.

Controller action:

- record timeout evidence,
- decide whether to split task, extend timeout, or escalate runtime,
- never blindly retry indefinite long-running tasks.

### `protocol_violation`

Worker exited without a valid terminal action such as complete/block, or completion lacks required evidence.

Controller action:

- record as explicit failure class,
- do not treat exit code 0 as success,
- retry once only if no artifacts were written and task is idempotent,
- otherwise create recovery task or escalate to human/controller review.

## 11. Retry and rerun policy

```yaml
retry_policy:
  default_max_attempts: 2
  retryable:
    - transient_crash
    - tool_timeout_with_no_side_effects
    - missing_optional_evidence
  not_retryable_without_review:
    - protected_action_block
    - irreversible_side_effect_started
    - private_data_boundary_hit
    - repeated_protocol_violation
    - ambiguous_scope
  rerun_requires_new_task_when:
    - original task changed files
    - reviewer requested changes
    - evidence is incomplete but side effects occurred
    - task needs a different runtime/profile
```

Important rule:

```text
Reviewer or verifier feedback creates a new linked fix/rerun task; do not simply rerun the same task with a sterner prompt when artifacts already changed.
```

## 12. Escalation rules

Escalate from ordinary worker execution when:

- the task exceeds allowed files/surfaces,
- side effects become external/public/irreversible,
- private data or credentials are encountered,
- a required runtime/tool is unavailable,
- repeated crashes or protocol violations occur,
- evidence cannot satisfy pass conditions,
- HIGH/CRITICAL findings remain unresolved,
- worker requests a decision outside approved scope.

Escalation targets:

```text
scratch delegate critique
profile worker
external runtime
human checkpoint
replan
block phase exit
```

## 13. Human checkpoint triggers

Human involvement is required when:

- authority is unclear,
- irreversible or public/external side effects are proposed,
- private data boundary is touched,
- worker asks for a decision not covered by the approved plan,
- repeated failures imply design ambiguity,
- unresolved HIGH/CRITICAL finding needs risk acceptance,
- Guardian/Heartgate cannot classify the action safely.

Human checkpoint task must present one concrete decision question and options.

## 14. External runtime escalation

Use external runtime when:

- implementation is heavy or repo-wide,
- debugging requires a coding-agent environment,
- independent runtime/model perspective materially improves confidence,
- a worker repeatedly fails due to local runtime/tool limits,
- verification requires cross-runtime confidence.

External runtime evidence must include:

```yaml
external_runtime_handle: "session/thread/process id when available"
runtime_name: claude_code | codex | opencode | kimi | other
escalation_reason: "..."
files_changed: []
checks_run: []
findings: []
residual_risks: []
```

## 15. Adapter-neutral coordination contract

The controller requires any coordination adapter to support:

```yaml
create_unit: required
assign_unit: required
declare_dependencies: required
attach_context: required
attach_artifact_or_comment: required
read_unit_outputs: required
mark_state: required
retry_or_rerun_unit: required
preserve_provenance: required
watch_or_poll_state: optional
notify: optional
```

Hermes Kanban mapping:

- `create_unit` -> `hermes kanban create`
- `assign_unit` -> `--assignee`
- `declare_dependencies` -> `--parent`
- `attach_context` -> task body + UACP context JSON
- `read_unit_outputs` -> `show`, comments, latest summary, run metadata
- `mark_state` -> complete/block/unblock/archive
- `retry_or_rerun_unit` -> new linked task or reclaim/reassign depending on side effects
- `preserve_provenance` -> Kanban events/runs/comments

## 16. EXECUTE evidence artifact format

```yaml
kind: uacp.execute_evidence
schema_version: "0.1"
run_id: "..."
phase: execute
timestamp: "..."
authority_artifact: "..."
controller:
  id: "..."
  coordination_adapter: hermes_kanban
  task_schema: plans/uacp-agent-council-followthrough/10-execute-task-schema.md
task_graph:
  - task_id: "..."
    title: "..."
    runtime_surface: "..."
    profile_id: null
    status: accepted | warned | rejected | deferred | blocked
    evidence_artifacts: []
    findings: []
worker_failures:
  - task_id: "..."
    failure_type: crashed | timed_out | protocol_violation | blocked
    evidence: "..."
    disposition: retried | fix_task_created | accepted_risk | blocked
checks:
  - id: "..."
    state: pass | warn | block
    evidence: "..."
readiness:
  decision: pass | warn | block
  ready_for: verify | replan | human_checkpoint
residual_risks: []
```

## 17. Phase exit rule

EXECUTE may exit to VERIFY when:

- all required task units are accepted, warned, deferred with rationale, or explicitly blocked with accepted disposition,
- no unresolved CRITICAL finding remains,
- unresolved HIGH findings are resolved, deferred with owner, or accepted by the correct authority,
- evidence artifact is written,
- side effects match declared scope,
- controller records readiness decision.

EXECUTE must not exit when:

- required task is still running/ready without disposition,
- protocol violation is unresolved,
- private/irreversible/public side effect lacks approval,
- evidence artifact is missing,
- findings block phase exit.

## 18. Implementation prerequisites

Before implementing this controller in runtime code, UACP should have:

1. Reviewed `10-execute-task-schema.md`.
2. Reviewed this controller design.
3. Defined where controller state lives: UACP `state/runs/`, Kanban metadata, or both.
4. Decided retry defaults and failure limits.
5. Added lightweight validators for task schema and execute evidence artifact.
6. Confirmed Kanban worker protocol violations can be detected reliably.

## 19. Current recommendation

For current UACP reramp:

```text
Use the full-auto EXECUTE controller as the next design target.
Do not implement full lifecycle autonomy yet.
Dogfood controller behavior manually through one or two EXECUTE graphs before coding automation.
```
