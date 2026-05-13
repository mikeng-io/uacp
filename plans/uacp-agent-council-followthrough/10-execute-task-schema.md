# 10 — EXECUTE Task Schema And Examples

Status: draft-ready for review  
Created: 2026-05-12T19:24:05.929916+00:00  
Scope: Current manual/semi-auto UACP EXECUTE work units routed through a coordination adapter, currently Hermes Kanban.

---

## 1. Purpose

This document defines the concrete schema for bounded UACP `EXECUTE` work units.

It implements the locked current operating model:

```text
manual/semi-auto first
Kanban/coordination primarily for non-trivial EXECUTE
TRIAGE/PROPOSE/PLAN/VERIFY/RESOLVE orchestrator-led by default
Kanban is a replaceable coordination adapter, not UACP doctrine
```

An EXECUTE task is a bounded work unit inside the UACP `EXECUTE` phase. It may perform implementation, document/config changes, evidence collection, external runtime dispatch, or human checkpoint handling.

## 2. Non-goals

This schema does not:

- make Kanban mandatory for every UACP phase,
- make a Kanban task equal to a lifecycle phase,
- require named UACP profiles for ordinary work,
- create actual Hermes profiles,
- define a full-autonomous command-bot topology,
- replace UACP run/state artifacts.

## 3. Core distinction

```text
UACP phase = lifecycle envelope
EXECUTE task = bounded work unit inside EXECUTE
coordination adapter = storage/dispatch mechanism for tasks
worker runtime = actual executor/analyser/reviewer
```

Hermes Kanban is the current coordination adapter. Future adapters may implement the same contract with another queue, issue tracker, workflow engine, or command bot.

## 4. Required task fields

Every non-trivial EXECUTE task should declare these fields.

```yaml
schema_version: "0.1"
kind: uacp.execute_task
id: "T... or coordination-adapter task id"
title: "Short imperative title"

uacp:
  run_id: "..."
  phase: execute
  authority_artifact: "plans/... or proposals/..."
  policy_version: "0.1"
  guardian_policy_version: "0.1"
  domains: []
  operator_constraints: []
  carried_findings: []
  cross_phase_coupling: []
  granularity_reassessment:
    entry_estimate: null
    exit_actual: null
    delta_reason: ""
    downstream_projection: {}

objective: >
  Concrete bounded outcome. One task should have one primary deliverable.

scope:
  allowed_files: []        # UACP_ROOT-relative or symbolic paths
  forbidden_files: []      # explicit no-touch list
  allowed_surfaces: []     # tools/runtimes/apis/workdirs allowed
  forbidden_surfaces: []   # private dirs, external APIs, public posting, etc.

runtime:
  surface: hermes_profile_worker | delegate_task | external_runtime | tool_adapter | evidence_service | human_checkpoint
  profile_id: null         # optional; only if using a named Hermes profile/worker
  external_runtime: null   # claude_code | codex | opencode | kimi | gemini | other
  model_policy: inherit | specified | adapter_controlled
  timeout: "30m"
  retry_policy: "default | none | custom"

side_effects:
  declared: []
  reversibility: reversible | partially_reversible | irreversible
  external_visibility: none | internal | external | public
  public_visibility_triggered: false
  approval_required: true | false

dependencies:
  parents: []
  blocks: []
  required_inputs: []

execution_contract:
  steps: []                # high-level expected sequence, not hidden micromanagement
  may_use_delegate_task: true | false
  may_use_external_runtime: true | false
  may_create_child_tasks: true | false
  escalation_triggers: []

verification:
  required_checks: []
  evidence_outputs: []
  findings: []              # structured findings; see Section 8
  pass_conditions: []
  warn_conditions: []
  block_conditions: []

rollback:
  strategy: "none | revert_patch | restore_backup | replan | human_decision"
  notes: "..."

completion:
  required_summary_fields:
    - files_changed
    - checks_run
    - evidence_artifact
    - residual_risks
  conditional_summary_fields:
    external_runtime:
      - external_runtime_handle
      - external_runtime_findings
  output_artifact: "verification/... or executions/..."
```

## 5. Optional task fields

Use these when relevant:

```yaml
council:
  form: none | scratch_council | profile_council | cross_runtime_council
  mode: execute | verify | review | audit | research | brainstorm_design
  tier: tier_0_single | tier_1_bounded | tier_2_role_diverse | tier_3_cross_runtime | tier_4_deep_council
  roles: []
  coordinator_required: true | false
  rerun_policy: "..."
  council_synthesis_artifact: null

adapter_neutrality:
  coordination_adapter: hermes_kanban
  portable_contract_fields:
    - create_unit
    - assign_unit
    - declare_dependencies
    - attach_context
    - attach_artifact_or_comment
    - read_unit_outputs
    - mark_state
    - retry_or_rerun_unit
    - preserve_provenance

risk:
  phase_local_granularity_entry: 1-10
  risk_level: low | medium | high | critical
  trust_boundary: local | workspace | external | public | private_data
  human_involvement_reason: null

observability:
  notify_targets: []
  heartbeat_expected: true | false
  log_artifacts: []
```

## 6. Runtime surface rules

### `delegate_task`

Use only for same-profile scratch branches inside a worker.

Appropriate for:

- quick analysis,
- local critique,
- small file inspection,
- brainstorming alternatives,
- provisional second checks.

Not appropriate for:

- true profile isolation,
- profile-local doctrine or memory,
- durable council participants,
- long-running execution,
- auditable profile ownership.

### `hermes_profile_worker`

Use when named profile identity matters or when the coordination adapter dispatches to a Hermes profile.

Appropriate for:

- durable profile-specific workers,
- profile-specific prompts/models/tools,
- async execution,
- formal profile council participants,
- worker ownership and audit trail.

Current-stage note: named UACP profiles are optional/future execution identities unless async profile-specific work is justified.

### `external_runtime`

Use when a different runtime/toolchain materially improves execution or verification.

Appropriate for:

- heavy coding/refactor/debugging,
- independent model/runtime review,
- external coding-agent environment,
- long-running runtime-specific workflows.

External runtime must state:

- escalation reason,
- runtime name,
- command/session/thread handle where available,
- changed files or produced artifacts,
- tests/checks/evidence,
- unresolved risks.

On an `external_runtime` surface, `may_use_external_runtime: true` means the controller may continue or manage the declared external runtime session. It does not permit unbounded nested runtime fan-out unless explicitly declared in `execution_contract.steps` or `escalation_triggers`.

### `tool_adapter` / `evidence_service`

Use when the work is primarily observation or actuation through tools rather than agent reasoning.

Examples:

- web extraction,
- browser automation,
- OCR/transcript extraction,
- static analysis,
- schema validation,
- local command execution.

### `human_checkpoint`

Use when authority, risk, irreversible action, private data, or external visibility requires Mike's decision.

A human-checkpoint task should ask one concrete decision question and include enough evidence to answer it.

## 7. Escalation triggers

An EXECUTE task should escalate or pause when:

- scope exceeds allowed files/surfaces,
- a protected or irreversible side effect appears,
- external/public visibility changes,
- private data or credentials appear,
- required evidence cannot be produced,
- tests/checks fail in a way requiring judgment,
- the worker needs a different runtime than declared,
- phase-local granularity materially increases,
- HIGH/CRITICAL findings remain unresolved.

Escalation options:

```text
same worker replan
child task
scratch delegate critique
profile worker
external runtime
human checkpoint
block task
```


## 8. Structured findings schema

When an EXECUTE task produces review, audit, verification, or external-runtime critique findings, use this structure under `verification.findings` or in the completion metadata.

```yaml
findings:
  - id: "F001"
    severity: info | low | medium | high | critical
    summary: "..."
    evidence: "..."
    affected_artifact: "..."
    recommended_action: "..."
    owner: "..."
    state: open | resolved | accepted_risk | not_applicable | deferred
```

Raw logs, transcripts, command output, and files remain `evidence_outputs`. Findings are adjudicated review objects.

## 9. Default profile semantics

`runtime.surface: hermes_profile_worker` with `profile_id: null` means the current/default Hermes profile worker under the selected coordination adapter.

Use a named `profile_id` only when profile-specific prompt, model, tool, memory, or worker identity matters. In the current manual/semi-auto stage, named UACP profiles are role templates and optional/future execution identities unless async profile-specific work is explicitly justified.

## 10. Schema stability and migration notes

Schema version `0.1` is draft-ready and suitable for current manual/semi-auto EXECUTE task specification. Stable field groups are:

- `uacp`,
- `objective`,
- `scope`,
- `runtime`,
- `side_effects`,
- `dependencies`,
- `execution_contract`,
- `verification`,
- `rollback`,
- `completion`.

Provisional fields likely to evolve in `0.2`:

- `council`,
- `adapter_neutrality`,
- `granularity_reassessment`,
- structured findings integration with validators,
- runtime-specific conditional completion fields.

A future migration should preserve backward compatibility by accepting missing optional blocks and warning rather than blocking unless the task explicitly selects a council, external runtime, or public/external side effect.

## 11. Completion contract

Every EXECUTE task completion summary should include:

```yaml
files_changed: []
artifacts_created: []
checks_run: []
checks_passed: []
checks_failed: []
evidence_artifact: "..."
side_effects_performed: []
residual_risks: []
follow_up_recommended: []
```

Do not mark complete with only prose like "done". Completion must be auditable.

## 12. Examples

### Example A — docs/config edit task

```yaml
kind: uacp.execute_task
title: Define EXECUTE task schema
objective: Create a schema doc and align routing config.
scope:
  allowed_files:
    - plans/uacp-agent-council-followthrough/**
    - docs/orchestration-model.md
    - config/review-routing.yaml
    - verification/**
  forbidden_files:
    - HERMES_ROOT/hermes-agent/**
    - PRIVATE_ROOT/**
runtime:
  surface: hermes_profile_worker
  profile_id: default
  model_policy: inherit
  timeout: 45m
side_effects:
  declared:
    - write UACP docs/config/verification artifacts
  reversibility: reversible
  external_visibility: none
  approval_required: false
execution_contract:
  may_use_delegate_task: true
  may_use_external_runtime: false
  may_create_child_tasks: false
verification:
  required_checks:
    - YAML files parse
    - schema doc exists
    - canonical docs align with current operating model
  evidence_outputs:
    - verification/uacp-execute-task-schema-verify.yaml
rollback:
  strategy: revert_patch
completion:
  required_summary_fields:
    - files_changed
    - checks_run
    - evidence_artifact
    - residual_risks
```

### Example B — code implementation task

```yaml
kind: uacp.execute_task
title: Add runtime_surface field to task metadata
objective: Implement runtime_surface metadata plumbing without changing dispatch behavior.
scope:
  allowed_files:
    - hermes_cli/kanban.py
    - tests/hermes_cli/test_kanban*.py
  forbidden_files:
    - PRIVATE_ROOT/**
runtime:
  surface: external_runtime
  external_runtime: codex
  profile_id: uacp-adapter-codex   # current-stage: future/optional slot unless async profile-specific work is justified
  model_policy: adapter_controlled
  timeout: 2h
side_effects:
  declared:
    - modify Hermes runtime code
    - run tests
  reversibility: reversible
  external_visibility: none
  approval_required: true
execution_contract:
  may_use_delegate_task: false
  may_use_external_runtime: true
  escalation_triggers:
    - test failures needing design decision
    - schema migration required
verification:
  required_checks:
    - targeted pytest passes
    - existing Kanban task creation still works
rollback:
  strategy: revert_patch
completion:
  required_summary_fields:
    - files_changed
    - checks_run
    - external_runtime_handle
    - evidence_artifact
    - residual_risks
```

### Example C — verification/evidence task

```yaml
kind: uacp.execute_task
title: Verify EXECUTE schema alignment
objective: Check schema doc, config, and orchestration model for consistency.
runtime:
  surface: hermes_profile_worker
  profile_id: null
  model_policy: inherit
scope:
  allowed_files:
    - plans/uacp-agent-council-followthrough/**
    - docs/orchestration-model.md
    - config/review-routing.yaml
    - verification/**
side_effects:
  declared:
    - write verification artifact
  reversibility: reversible
  external_visibility: none
verification:
  required_checks:
    - YAML parses
    - required schema fields are present
    - Kanban adapter neutrality is explicit
completion:
  output_artifact: verification/uacp-execute-task-schema-review.yaml
```

### Example D — external-runtime adapter task

```yaml
kind: uacp.execute_task
title: Ask Claude Code to review execution schema edge cases
objective: Obtain independent runtime critique of schema completeness.
runtime:
  surface: external_runtime
  profile_id: uacp-adapter-claude-code
  external_runtime: claude_code
  model_policy: adapter_controlled
side_effects:
  declared:
    - run external coding/review agent
  reversibility: not_applicable
  external_visibility: external
  approval_required: false
execution_contract:
  may_use_external_runtime: true
  escalation_triggers:
    - external agent recommends runtime code change
verification:
  evidence_outputs:
    - external runtime summary
    - findings disposition
completion:
  required_summary_fields:
    - external_runtime_handle
    - findings
    - accepted_or_rejected_recommendations
```

### Example E — human-checkpoint task

```yaml
kind: uacp.execute_task
title: Confirm whether to create actual UACP profiles
objective: Ask Mike whether to implement named profiles now or keep them as future slots.
runtime:
  surface: human_checkpoint
side_effects:
  declared: []
  reversibility: not_applicable
  external_visibility: none
  approval_required: true
completion:
  required_summary_fields:
    - decision_question
    - options_presented
    - selected_option
    - rationale
```

## 13. Adapter-neutral Kanban mapping

When implemented through Hermes Kanban:

- task title maps to `title`,
- schema body maps to task `body`,
- `runtime.profile_id` maps to `assignee` when a named profile is used,
- `dependencies.parents` maps to Kanban parents,
- `scope` and `side_effects` stay in task body / UACP context JSON,
- completion contract maps to `kanban_complete(summary=..., metadata=...)`,
- verification evidence maps to comments or artifact paths,
- blocked human decisions map to `kanban_block(...)`.

Portable adapter requirement: the schema must remain understandable outside Hermes Kanban.

## 14. Review checklist

For machine-readable specs, these checks may also appear as `execution_contract.pre_dispatch_checks`.

Before dispatching an EXECUTE task, check:

- Is this truly EXECUTE work, not PLAN/VERIFY that can be synchronous?
- Is the objective bounded?
- Are allowed and forbidden surfaces explicit?
- Are side effects declared?
- Is the runtime/profile choice justified?
- Are verification outputs specified?
- Is rollback or escape path specified?
- Is human approval required?
- Can another coordination adapter implement this task without losing core meaning?

## 15. Current-stage recommendation

For current manual/semi-auto UACP:

```text
Use this schema for non-trivial EXECUTE tasks.
Do not force non-EXECUTE phases into this schema unless they become durable/full-autonomy controller tasks.
Keep named profiles optional until actual profile-based automation is intentionally implemented.
```
