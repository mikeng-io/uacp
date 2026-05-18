# Package Selection Schema

`package-selection.yaml` is the bridge between human-readable proposal docs and machine-enforced lifecycle checks.

It records:

- run id and phase
- granularity and rationale
- work heart
- universal core concern coverage
- selected domain modules and reasons
- not-applicable modules and rationale
- artifact paths
- PLAN readiness status

## Required not-applicable fields

Every omitted concern/module that could affect review must include:

- `reason`
- `accepted_by`
- `owner`
- `residual_risk`
- `revisit_phase`

Blanket omission is forbidden. `not_applicable` means the omission has been evaluated, owned, and assigned a revisit point.

## Validator behavior

The validator should block when:

- package-selection is missing for selected medium/high consequence work;
- a universal core concern is missing;
- a selected module lacks reason or artifact;
- a selected artifact path does not exist;
- not-applicable rationale is incomplete;
- proposal YAML claims PLAN readiness while package selection is incomplete.
