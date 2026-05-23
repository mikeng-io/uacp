# UACP PIV and execution evidence contract

Session lesson: do not fix EXECUTE semantic-loss by merely adding another Markdown package. The durable pattern is a hybrid PLAN/EXECUTE/VERIFY contract.

## Ownership split

- PLAN drafts the PIV/evidence contract before implementation starts.
- EXECUTE records checkpoints, decisions, deviations, tests, and evidence against that contract while performing work.
- VERIFY judges whether the completed PIV evidence is sufficient, truthful, and aligned with proposal/plan.

## PLAN obligations

For non-trivial/governed work, PLAN should create an execution observability contract such as `plans/{run_id}-piv.yaml` plus semantic Markdown under `plans/{run_id}/`. It should define objectives, implementation units, checkpoint cadence, evidence obligations, semantic recovery obligations, drift conditions, escalation/re-plan conditions, and VERIFY handoff criteria.

## EXECUTE obligations

EXECUTE should not invent an ad hoc checkpoint shape. It should write YAML checkpoints and a semantic execution evidence trail under `executions/{run_id}/`, mapping actual work to the PLAN-authored PIV contract. The package should preserve why choices were made, how work maps to the plan, which invariants held, which assumptions changed, and which evidence VERIFY should consume.

## VERIFY obligations

VERIFY should consume the proposal, plan, PLAN-authored PIV contract, EXECUTE checkpoints/package, diffs/tests/probes, council synthesis, and handled findings. Outcomes should include PIV satisfied, satisfied with deferred items, failed/return to EXECUTE, or PLAN invalidated/return to PLAN.

## Pitfall

A plain execution Markdown package can become narrative fluff. A PIV contract makes the execution record answerable to pre-declared criteria and prevents raw diff dumps, YAML-only checkpoints, and post-hoc verification improvisation.