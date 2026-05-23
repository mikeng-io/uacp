# Adaptive VERIFY Evidence Gate — Session Reference

Use this reference when hardening or operating UACP VERIFY/VERIFY→RESOLVE flows.

## Durable lesson

VERIFY is the truth boundary before RESOLVE. It must not pass on artifact existence, unsupported facts, unowned assumptions, unresolved findings, or self-remediation.

For VERIFY-level governance changes, do **not** jump straight into implementation. Use this order:

1. Retrieval-led gap audit against repo ground truth.
2. Pre-design council to define truth/evidence/self-approval constraints.
3. Implement docs/config/validator/fixtures/skills.
4. Deterministic validation.
5. Post-implementation council/audit.
6. Patch findings.
7. Focused adversarial follow-up.
8. Commit/push only after PASS.

## Required concepts

- Verified facts are evidence-grounded claims, not conclusions.
- Assumptions are accepted without direct proof and require owner, accepted_by, residual risk, and next-phase obligation.
- Deferred items require owner, revisit trigger, accepted_by, risk if delayed, and next-phase obligation.
- Warnings are non-blocking only when explicitly dispositioned and not hiding blockers.
- Blockers cannot coexist with `ready_for_resolve: true`.
- VERIFY must not remediate material findings and self-certify closure.
- Heartgate coherence is separate from phase-local council synthesis.

## Recommended artifact shape

Machine artifacts:

- `verification/{run_id}-verify-selection.yaml` with `kind: uacp.verification_package`
- `verification/{run_id}-piv-assessment.yaml` with `kind: uacp.piv_assessment` when EXECUTE used PIV
- `verification/{run_id}-resolve-readiness.yaml` with `kind: uacp.verify_resolve_readiness`

Semantic package:

- `verification/{run_id}/00-index.md`
- `verification/{run_id}/piv-assessment.md`
- `verification/{run_id}/verified-facts.md`
- `verification/{run_id}/assumptions-and-deferred-items.md`
- `verification/{run_id}/findings-and-dispositions.md`
- `verification/{run_id}/council-review.md`
- `verification/{run_id}/resolve-readiness.md`

## Must-block negative fixtures

Future validator changes should preserve negative fixtures for:

- fake facts or facts without source evidence/source path/source locator
- unowned assumptions
- invalid assumption disposition
- pass/readiness with open blockers
- accepted-risk/deferred blockers without acceptance fields
- missing/unknown/duplicate PIV obligation assessments
- PIV overall pass with blocked obligation
- missing/unbound Heartgate coherence
- self-remediation without independent re-verification
- readiness with no pass/warn evidence cluster
- unrelated verification package reused for readiness
- fact summaries not present in the verification package
- unbound PIV summaries or cluster artifacts

## Pitfall

A VERIFY gate that only checks file existence is a rubber stamp. Bind readiness artifacts to the current `run_id`, exact expected paths, package kind, PIV assessment kind, fact IDs, evidence cluster artifacts, and Heartgate run/lenses.
