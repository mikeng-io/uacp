# Enforcement Surfaces

This PROPOSE package defines **required future enforcement outcomes**. It does not claim those PLAN-specific validator, Heartgate, or Guardian paths already exist.

## Validator — required outcome
PLAN must add deterministic validation for `kind: uacp.plan_package_selection`.

Acceptance checks:
- `kind == uacp.plan_package_selection`
- `phase == plan`
- `run_id` exists
- universal PLAN core complete
- selected module artifacts exist
- N/A entries include `reason`, `accepted_by`, `owner`, `residual_risk`, `revisit_phase`
- `transition_readiness.status` valid
- scope artifact exists
- plan package directory exists

Implementation details such as function names are suggestions for EXECUTE, not PROPOSE authority. PLAN must name exact implementation tranches before code/config mutation.

## Heartgate — required outcome
PLAN must require a PLAN→EXECUTE adaptive package gate when adaptive PLAN package selection is active.

Required blocking behavior:
- missing plan-selection
- missing plan package directory
- missing universal core
- missing selected module artifact
- weak N/A
- YAML-only plan for selected high-consequence work

Function names such as `_validate_adaptive_plan_package_gate()` and `_validate_plan_na()` are candidate EXECUTE names only. PLAN may choose different names if the behavior and tests are equivalent.

## Guardian — required outcome
Guardian policy must recognize these as UACP artifacts:

- `plans/{run_id}/`
- `plans/{run_id}-plan.yaml`
- `plans/{run_id}-scope.yaml`
- `plans/{run_id}-plan-selection.yaml`

Policy recognition is not the same as proven live interception. VERIFY must separate:

1. policy/config recognition,
2. source-level runtime logic,
3. live plugin/runtime reload proof,
4. actual hard-interception behavior for ordinary write paths.
