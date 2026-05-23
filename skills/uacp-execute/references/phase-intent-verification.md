# Phase Intent Verification — Session Reference

Use this reference for PLAN/EXECUTE/VERIFY work involving PIV.

## Durable correction

PIV means **Phase Intent Verification**, not Phase Implementation Verification.

The term must stay work-type neutral because EXECUTE is not always code implementation. EXECUTE may produce docs, config, artifacts, council dispatches, migrations, dry-runs, runtime probes, state updates, communication packages, or handoffs.

## Ownership model

- PLAN authors the PIV contract.
- EXECUTE records checkpoints and semantic evidence against the PIV contract.
- VERIFY assesses whether PIV evidence satisfies phase intent.

## Preferred vocabulary

Use:

- `work_units`, not `implementation_units`
- `phase_intent`, not implementation goal
- `produced_outputs`, not implemented outputs
- `intent_drift`, not implementation drift
- `next_phase_readiness`, not deployment readiness

## PIV contract shape

Typical artifact:

- `plans/{run_id}-piv.yaml`
- optional semantic companion: `plans/{run_id}/piv-contract.md`

Required concepts:

- `kind: uacp.phase_intent_verification_contract`
- `phase: plan`
- `applies_to_phase: execute`
- phase intent
- work units
- evidence obligations
- checkpoint policy
- intent drift conditions
- next-phase handoff

## EXECUTE checkpoint shape

Typical artifact:

- `executions/{run_id}-checkpoint-*.yaml`

Should reference:

- PIV contract path
- work unit ID
- evidence obligation IDs
- decisions and rationale
- intent drift and disposition
- invariants
- next phase readiness

## Pitfall

Do not let PIV become code-biased. If a future design says “implementation unit” or treats tests/diffs as the only proof shape, correct it back to Phase Intent Verification and intent-specific evidence obligations.
