# Risks and Verification

## Risks

### Process theater

Risk: adaptive package becomes another document quota.

Mitigation: validate concerns and rationale, not fixed filenames.

### Phase collapse

Risk: PROPOSE demands PLAN-level details too early.

Mitigation: PROPOSE selects concern surfaces and transition readiness; PLAN owns detailed execution decomposition.

### Enforcement gap

Risk: skill prose changes but validator/Heartgate do not enforce.

Mitigation: PLAN must include config/validator/Heartgate patches and fixtures.

### OpenSpec overfit

Risk: UACP inherits coding-only assumptions.

Mitigation: package-selection must justify modules by work heart/context.

## Verification cases

Should block:

- YAML-only proposal for selected medium/high consequence work.
- Missing universal core concern.
- Selected module with no artifact.
- Weak `not_applicable` missing reason/accepted_by/residual_risk/revisit_phase.

Should pass:

- Non-OpenSpec filenames when concerns are covered.
- Domain-specific package shape with complete package-selection evidence.
