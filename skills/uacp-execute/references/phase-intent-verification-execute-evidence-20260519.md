# Phase Intent Verification (PIV) for EXECUTE Evidence — 2026-05-19

## Lesson

For UACP, **PIV means Phase Intent Verification**, not Phase Implementation Verification. EXECUTE is not always code implementation; it may produce documentation, configuration, generated artifacts, council synthesis, runtime probes, dry-run evidence, state updates, migration preparation, or handoff packages.

The durable pattern is:

```text
PLAN drafts the PIV contract.
EXECUTE records evidence against the PIV contract.
VERIFY assesses PIV satisfaction.
```

This is a hybrid fix: not just “add Markdown to EXECUTE,” and not just “add more YAML.” The PIV contract prevents semantic execution packages from becoming narrative fluff, while the Markdown package prevents YAML-only checkpoints from losing why/how/decision context.

## Target artifacts

PLAN-authored contract:

```text
plans/{run_id}-piv.yaml
kind: uacp.phase_intent_verification_contract
```

Optional PLAN semantic companion:

```text
plans/{run_id}/piv-contract.md
```

EXECUTE machine checkpoint:

```text
executions/{run_id}-checkpoint-*.yaml
kind: uacp.execution_checkpoint
```

EXECUTE semantic package for selected non-trivial work:

```text
executions/{run_id}/00-index.md
executions/{run_id}/work-narrative.md
executions/{run_id}/decision-log.md
executions/{run_id}/evidence-map.md
executions/{run_id}/intent-drift-and-deviations.md
executions/{run_id}/verify-handoff.md
```

## Neutral vocabulary

Use neutral phase-work terms:

- `work_units`, not `implementation_units`
- `work_narrative`, not `implementation_narrative`
- `produced_outputs`, not `implemented_outputs`
- `phase_intent`, not code/task-only objective
- `intent_drift`, not only scope creep or test failure

## Validator hardening checklist

When adding or reviewing PIV/EXECUTE validation, block these bypasses:

- missing or malformed `piv_contract`
- checkpoint `work_unit_id` not declared in PIV
- unknown `evidence[].obligation_id`
- required evidence missing while `next_phase_readiness.status: ready`
- blank or invalid `checkpoint_type`
- invalid `next_phase_readiness.status`
- `next_phase_readiness.target_phase` not equal to `verify`
- non-boolean `intent_drift.detected`
- `intent_drift.detected: false` with non-empty deviations
- drift deviations without `id`, `description`, `owner`, and valid `disposition`
- semantic EXECUTE package missing `00-index.md` or required evidence modules

## Expected-fail fixtures

Maintain negative fixtures for each validator bypass class. A good patch should include a positive PIV/checkpoint fixture and expected-fail fixtures for malformed PIV, unknown obligations, missing evidence, invalid checkpoint/readiness states, and drift inconsistencies.

Run pattern:

```bash
python -m py_compile scripts/validate_uacp_artifacts.py
python scripts/validate_uacp_artifacts.py --root .
python scripts/validate_uacp_artifacts.py --root . plans/fixture-execute-pass-piv.yaml executions/fixture-execute-pass-checkpoint-001.yaml
for f in verification/fixtures/adaptive-execute-evidence/negative/*.yaml; do
  python scripts/validate_uacp_artifacts.py --root . "$f" && exit 9
done
```

## Council pattern

For lifecycle-semantic changes like this, implement first, then run focused council on concrete artifacts. Useful roles:

- lifecycle semantics reviewer
- validator compatibility auditor
- execution practitioner reviewer
- devil's advocate

If council finds concrete bypasses, patch them and rerun a focused adversarial follow-up. Do not stop at initial CONCERNS when the findings are mechanical validator gaps.

## Boundary

Do not force PIV packages onto trivial/direct work. The adaptive EXECUTE evidence gate should apply when PLAN explicitly creates a PIV contract or when risk/domain predicates justify it. Low-risk/direct tasks remain lightweight unless selected into the gate.
