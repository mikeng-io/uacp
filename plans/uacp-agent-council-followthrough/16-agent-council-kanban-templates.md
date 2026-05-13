# 16 — Agent Council To Kanban Task Templates

Status: design-complete  
Scope: reusable templates for council-mode execution through a coordination adapter.

## Principle

Kanban stores and dispatches work units. Agent Council performs deliberation. UACP owns authority and phase state.

## Template: EXECUTE council task

```yaml
kind: uacp.execute_task
schema_version: "0.1"
id: "adapter-task-id"
title: "Implement bounded artifact change"
uacp:
  run_id: "..."
  phase: execute
  authority_artifact: "plans/..."
  policy_version: "0.1"
  guardian_policy_version: "0.1"
  domains: [governance]
objective: "One concrete deliverable."
scope:
  allowed_files: []
  forbidden_files: ["PRIVATE_ROOT"]
  allowed_surfaces: ["file", "terminal"]
  forbidden_surfaces: ["public_posting"]
runtime:
  surface: hermes_profile_worker
  profile_id: "uacp-implementer"
  external_runtime: null
  model_policy: inherit
side_effects:
  declared: ["local file writes"]
  reversibility: reversible
  external_visibility: none
  approval_required: false
verification:
  required_checks: []
  evidence_outputs: []
  pass_conditions: []
completion:
  required_summary_fields: [files_changed, checks_run, evidence_artifact, residual_risks]
  output_artifact: "executions/...yaml"
```

## Template: VERIFY council task

Use `runtime.surface: delegate_task` or `hermes_profile_worker` depending on whether profile isolation is required. Required roles: `verification_reviewer`, `devils_advocate`, `integrator_critic`.

## Template: AUDIT council task

Use for compliance/security/process review. Minimum fields: authority, trust boundary, selected audit dimensions, allowed read surfaces, forbidden mutation surfaces, finding schema, and synthesis artifact path.

## Required council metadata

- `council.mode`
- `council.tier`
- `council.roles`
- `phase_local_granularity`
- `dispatch_surfaces`
- `authority_artifact`
- `declared_side_effects`
- `expected_artifact`
- `verification_gates`

## Failure semantics

A worker exiting without `complete`/`block` metadata is a protocol violation, not success. Repeated protocol violations should block or escalate instead of retrying forever.
