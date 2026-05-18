# PLAN Selection Schema

Draft machine bridge. This is a schema target for PLAN/EXECUTE to harden; placeholders below are examples and must not appear in accepted PLAN artifacts.

```yaml
kind: uacp.plan_package_selection
phase: plan
run_id: <run_id>
work_heart:
  primary: lifecycle_semantics | runtime_enforcement | implementation | docs | ...
  rationale: <specific topology reason>
universal_core:
  work_breakdown:
    status: covered
    artifact: plans/<run_id>/work-packages.md
  dependencies:
    status: covered
    artifact: plans/<run_id>/dependencies.md
selected_modules:
  guardian_heartgate_plan:
    reason: <specific selected-surface reason>
    artifact: plans/<run_id>/guardian-heartgate-plan.md
not_applicable:
  migration_plan:
    reason: <specific reason this work has no migration/data/state-schema effect>
    accepted_by: PLAN
    owner: main_session
    residual_risk: <specific condition that would invalidate the N/A>
    revisit_phase: execute
    revisit_trigger: <observable event that forces replan>
transition_readiness:
  status: ready_for_execute | ready_with_conditions | blocked
  conditions: []
```

## N/A standard
N/A entries are invalid if they are generic boilerplate. Each N/A must be falsifiable: it must say what observation would make the N/A wrong and which phase must revisit it.

## Validator target
Validator must reject missing universal core, missing selected artifacts, weak N/A entries, invalid phase/kind, and absent package directory when adaptive PLAN package is selected.
