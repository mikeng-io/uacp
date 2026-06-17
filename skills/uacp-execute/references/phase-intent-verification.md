# Phase Intent Verification — Contract and Evidence Reference

Use this reference for PLAN/EXECUTE/VERIFY work involving PIV.

## Terminology: Phase Intent Verification

PIV means **Phase Intent Verification**, not Phase Implementation Verification.

The term must stay work-type neutral because EXECUTE is not always code implementation. EXECUTE may produce docs, config, artifacts, council dispatches, migrations, dry-runs, runtime probes, state updates, communication packages, or handoffs.

## Ownership model

- PLAN authors the PIV contract: phase intent, neutral work units, evidence obligations, checkpoint policy, drift conditions, and VERIFY handoff criteria.
- EXECUTE records against the contract: checkpoints, decisions, produced outputs, evidence obligation results, intent drift, invariants, and next-phase readiness.
- VERIFY judges PIV satisfaction: pass, pass with deferred items, return to EXECUTE, or return to PLAN.

This is a hybrid pattern. The PIV contract prevents semantic execution packages from becoming narrative fluff; the Markdown evidence package prevents YAML-only checkpoints from losing why/how/decision context.

## Preferred vocabulary

Use neutral phase-work terms:

- `work_units`, not `implementation_units`
- `phase_intent`, not implementation goal
- `produced_outputs`, not implemented outputs
- `intent_drift`, not implementation drift
- `next_phase_readiness`, not deployment readiness
- `work_narrative`, not `implementation_narrative`

## Artifact pattern

PLAN-authored machine contract:

```text
plans/{run_id}-piv.yaml
kind: uacp.phase_intent_verification_contract
phase: plan
applies_to_phase: execute
```

Optional PLAN semantic companion:

```text
plans/{run_id}/piv-contract.md
```

Required contract concepts: phase intent, work units, evidence obligations, checkpoint policy, intent drift conditions, escalation/re-plan conditions, next-phase handoff.

EXECUTE machine checkpoint:

```text
executions/{run_id}-checkpoint-*.yaml
kind: uacp.execution_checkpoint
```

Checkpoint must reference: PIV contract path, work unit ID, evidence obligation IDs, decisions and rationale, intent drift and disposition, invariants, next-phase readiness.

Semantic EXECUTE package for selected non-trivial/governed work:

```text
executions/{run_id}/00-index.md
executions/{run_id}/work-narrative.md
executions/{run_id}/decision-log.md
executions/{run_id}/evidence-map.md
executions/{run_id}/intent-drift-and-deviations.md
executions/{run_id}/verify-handoff.md
```

## PLAN obligations

For non-trivial/governed work, PLAN should define: objectives, work units, checkpoint cadence, evidence obligations, semantic recovery obligations, drift conditions, and VERIFY handoff criteria.

## EXECUTE obligations

EXECUTE should not invent an ad hoc checkpoint shape. Write YAML checkpoints and a semantic execution package under `executions/{run_id}/`, mapping actual work to the PLAN-authored PIV contract. Preserve why choices were made, how work maps to the plan, which invariants held, which assumptions changed, and which evidence VERIFY should consume.

## VERIFY obligations

VERIFY consumes the proposal, plan, PLAN-authored PIV contract, EXECUTE checkpoints/package, diffs/tests/probes, council synthesis, and handled findings. Outcomes: PIV satisfied, satisfied with deferred items, failed/return to EXECUTE, or PLAN invalidated/return to PLAN.

## Validator hardening: bypass classes to block

- Missing or malformed PIV contract
- Checkpoint `work_unit_id` not declared in PIV
- Unknown `evidence[].obligation_id`
- Required evidence missing while `next_phase_readiness.status: ready`
- Blank or invalid `checkpoint_type`
- Invalid `next_phase_readiness.status`
- `next_phase_readiness.target_phase` not equal to `verify`
- Non-boolean `intent_drift.detected`
- `intent_drift.detected: false` with non-empty deviations
- Drift deviations without `id`, `description`, `owner`, and valid `disposition`
- Semantic EXECUTE package missing `00-index.md` or required evidence modules
- YAML-only checkpoint for selected medium/high consequence EXECUTE work

## Expected-fail fixtures

Maintain negative fixtures for each validator bypass class. A good patch includes a positive PIV/checkpoint fixture and expected-fail fixtures for malformed PIV, unknown obligations, missing evidence, invalid checkpoint/readiness states, and drift inconsistencies.

Run pattern:

```bash
python -m py_compile scripts/validate_uacp_artifacts.py
python scripts/validate_uacp_artifacts.py --root .
python scripts/validate_uacp_artifacts.py --root . plans/fixture-execute-pass-piv.yaml executions/fixture-execute-pass-checkpoint-001.yaml
for f in verification/fixtures/adaptive-execute-evidence/negative/*.yaml; do
  python scripts/validate_uacp_artifacts.py --root . "$f" && exit 9
done
```

## Adaptive gate boundary

Do not force PIV packages onto trivial/direct work. The adaptive EXECUTE evidence gate applies when PLAN explicitly creates a PIV contract or when risk/domain predicates justify it. Low-risk/direct tasks remain lightweight unless selected into the gate.

## Pitfall: code-bias

Do not let PIV become code-biased. If a design says "implementation unit" or treats tests/diffs as the only proof shape, correct it back to Phase Intent Verification and intent-specific evidence obligations. A plain Markdown execution package without a PLAN-authored contract can become narrative fluff that is not answerable to pre-declared criteria.

## Operator presentation

Operator returns should summarize meaning: conclusion, what changed, why it matters, decision, invariants, risks, next. Raw file lists and complete artifact inventories belong in UACP artifacts and are shown only on request.
