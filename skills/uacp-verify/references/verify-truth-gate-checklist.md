# VERIFY truth-gate checklist

Use this reference when authoring or reviewing UACP VERIFY artifacts, validators, or phase skills.

## Purpose

VERIFY is the lifecycle truth gate. It consumes proposal/plan/execute evidence and decides whether the run is ready for RESOLVE. It is not a generic test summary and not a self-repair phase.

## Required distinctions

Keep these separate in both machine artifacts and semantic packages:

- verified facts: claims supported by traceable evidence
- assumptions: accepted but not directly verified claims
- deferred items: unresolved work intentionally carried forward
- warnings: non-blocking risks or uncertainty
- blockers: hard stops
- PIV assessment: obligation-by-obligation judgment against PLAN-authored Phase Intent Verification contract
- resolve readiness: explicit conclusion about whether RESOLVE may close

## Must-block cases

Block VERIFY or VERIFY->RESOLVE readiness when:

- facts have no source evidence/source path/source locator
- assumptions or deferred items lack owner, accepted_by, residual risk, or next-phase obligation
- PIV was used but no PIV assessment exists
- any required PIV obligation is missing, duplicated, unknown, or blocked while overall status is pass
- open blockers remain
- council concerns are normalized into pass without disposition
- VERIFY remediates material findings and self-certifies without independent re-verification
- Heartgate coherence is required but missing, stale, unbound, or lacks required lenses
- readiness references unrelated verification packages, PIV assessments, cluster artifacts, or Heartgate artifacts

## Operator reporting

VERIFY reports should summarize decision, verified facts, assumptions/deferred items, blockers, residual risks, and next action. Do not dump raw artifacts unless asked.