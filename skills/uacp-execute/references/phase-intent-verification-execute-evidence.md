# Phase Intent Verification EXECUTE evidence pattern

Use when UACP EXECUTE work needs recoverable evidence for VERIFY.

## Core concept

PIV means **Phase Intent Verification**, not Phase Implementation Verification. EXECUTE work is not always code implementation; it may be docs, config, generated artifacts, council dispatch, runtime probes, dry-runs, state updates, migrations, or handoffs.

## Ownership split

- PLAN authors the PIV contract: phase intent, neutral work units, evidence obligations, checkpoint policy, drift conditions, and VERIFY handoff.
- EXECUTE records against the contract: checkpoints, decisions, produced outputs, evidence obligation results, intent drift, invariants, and next-phase readiness.
- VERIFY judges PIV satisfaction: pass, pass with deferred items, return to EXECUTE, or return to PLAN.

## Artifact pattern

Machine contract:

- `plans/{run_id}-piv.yaml`
- `kind: uacp.phase_intent_verification_contract`

Machine checkpoint:

- `executions/{run_id}-checkpoint-*.yaml`
- `kind: uacp.execution_checkpoint`
- references `piv_contract`
- uses `work_unit_id`, not implementation-only language

Semantic EXECUTE package when selected:

- `executions/{run_id}/00-index.md`
- `work-narrative.md`
- `decision-log.md`
- `evidence-map.md`
- `intent-drift-and-deviations.md`
- `verify-handoff.md`

## Validator pitfalls to preserve

Block or explicitly handle:

- malformed or missing PIV contract
- checkpoint not bound to PIV
- work unit not declared in PIV
- unknown evidence obligation IDs
- missing required evidence while claiming ready
- blank or invalid checkpoint type
- non-boolean `intent_drift.detected`
- `detected: false` with non-empty deviations
- drift deviations without disposition/id/description/owner
- invalid `next_phase_readiness.status`
- `next_phase_readiness.target_phase` not equal to `verify`
- YAML-only checkpoint for selected medium/high consequence EXECUTE work

## Operator presentation

Operator returns should summarize meaning: conclusion, what changed, why it matters, decision, invariants, risks, next. Raw file lists and complete artifact inventories belong in UACP artifacts and are shown only on request.
