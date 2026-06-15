# UACP Lifecycle Trace Table

This document is the cross-phase artifact dependency map for UACP. For each phase transition, it lists required inputs, required outputs, Heartgate checks, and the gate-ledger entry that records the transition's evaluation.

The kernel reads this dependency model from `config/phase-transitions.yaml` (doctrine + operator knobs; gate-rule grammar codified to `engines/domain/gate_rules.py` in Slice 4b), `engines/domain/artifact_schema.py` (`artifact_schemas_dict()`; `config/artifact-schemas.yaml` deleted Slice 5), and `config/uacp.toml [guardian]` (Guardian policy; collapsed from legacy guardian-policy.yaml in Slice 3). This document is the canonical reading-order narrative that humans use to verify the model is coherent end-to-end.

## Transitions

### `none → TRIAGE` (run start)

- Required inputs: operator request from chat, ticket, scheduled trigger, or governed runtime surface.
- Required outputs: `proposals/{run_id}-triage.yaml`, `state/runs/{run_id}-triage.yaml`, `state/current.yaml` updated.
- Heartgate checks: none; TRIAGE is the entry point.
- Gate ledger: `gate: TRIAGE_COMPLETE` optional.

### `TRIAGE → PROPOSE`

- Required inputs: triage artifact at `proposals/{run_id}-triage*.yaml`.
- Required outputs: proposal artifact, `proposals/{run_id}-intent.md`, and when adaptive packages are selected, `proposals/{run_id}-package-selection.yaml` plus `proposals/{run_id}/00-index.md` and selected semantic proposal package documents.
- Heartgate checks: required fields, transition allowance, invariant summary, cluster summary, blockers/warnings/deferred items, Heartgate coherence when required, phase exit invariants, legacy Post-Phase Verification ledger rule, intent doc, adaptive proposal package gate.
- Gate ledger: `gate: TRIAGE->PROPOSE`.

### `PROPOSE → PLAN`

- Required inputs: proposal artifact and adaptive proposal package when selected.
- Required outputs: plan artifacts, `plans/{run_id}-scope.yaml`, `plans/{run_id}-plan-selection.yaml`, `plans/{run_id}/00-index.md`, selected semantic plan package documents, and `plans/{run_id}-piv.yaml` when PLAN authorizes non-trivial EXECUTE work.
- Heartgate checks: phase exit invariants, legacy Post-Phase Verification ledger rule, adaptive plan package gate, scope artifact checks, plan validation gate, run-registry overlap.
- Gate ledger: `gate: PROPOSE->PLAN`; `gate: PLAN_VALIDATION` before execution when required.

### `PLAN → EXECUTE`

- Required inputs: plan package, scope artifact, selected runtime/tool policy, and Phase Intent Verification contract when required.
- Required outputs: bounded execution authorization and gate ledger entry; EXECUTE will later produce checkpoints and semantic evidence.
- Heartgate checks: scope artifact contract, plan validation, run registry overlap, phase tool admissibility.
- Gate ledger: `gate: PLAN->EXECUTE`.

### `EXECUTE → VERIFY`

- Required inputs: `executions/{run_id}-checkpoint-001.yaml` or selected checkpoint set, `executions/{run_id}/00-index.md`, semantic EXECUTE package documents, and the PLAN-authored Phase Intent Verification contract at `plans/{run_id}-piv.yaml` when selected.
- Required outputs: VERIFY intake artifacts under `verification/{run_id}*`.
- Heartgate checks: phase exit invariants, legacy Post-Phase Verification ledger rule, adaptive execute evidence gate, and runtime delegation to the canonical artifact validator for PIV/checkpoint semantics.
- Gate ledger: `gate: EXECUTE->VERIFY`.

**Phase Intent Verification contract**: PLAN declares work units, evidence obligations, checkpoint policy, intent drift conditions, and VERIFY handoff. EXECUTE checkpoints must prove required obligations. `next_phase_readiness.status: ready` requires required obligation evidence to be `pass`; `warn` or `deferred` required evidence requires owner, residual risk, next action, and a deferred-ready status.

### `VERIFY → RESOLVE`

- Required inputs: VERIFY package selection at `verification/{run_id}-verify-selection.yaml`, semantic verification package `verification/{run_id}/`, PIV assessment at `verification/{run_id}-piv-assessment.yaml` when EXECUTE used PIV, and resolve readiness at `verification/{run_id}-resolve-readiness.yaml`.
- Required outputs: RESOLVE artifacts under `.outputs/{run_id}*`, including `.outputs/{run_id}-lessons.yaml` where the lessons schema applies.
- Heartgate checks: evidence disposition pairs, lessons artifact, adaptive verify evidence gate, and runtime delegation to the canonical artifact validator for verified facts, assumptions, blockers, PIV assessment, self-approval guard, Heartgate coherence, and resolve readiness.
- Gate ledger: `gate: VERIFY->RESOLVE`.

**Verification package contract**: VERIFY separates verified facts from assumptions/deferred items, binds facts to source evidence, records blocker/warning dispositions, evaluates PIV satisfaction, guards against self-remediation/self-certification, and produces `verify_resolve_readiness` only when closure can safely proceed.

### `RESOLVE → terminal` (run complete)

- Required inputs: VERIFY resolve readiness, resolve package selection at `.outputs/{run_id}-resolve-selection.yaml`, semantic RESOLVE package `.outputs/{run_id}/`, and closure artifact `.outputs/{run_id}-closure.yaml`.
- Required outputs: final operator handoff, closure decision, residual-risk/deferred-item carry-forward, lessons/state/memory/skill disposition, and run state/registry updates through governed state surfaces.
- Heartgate checks: adaptive resolve closure gate and runtime delegation to the canonical artifact validator for readiness binding, residual-risk carry-forward, deferred-item preservation, final decision, closed scope, lesson dispositions, state/memory action, and concise operator handoff.
- Gate ledger: no new terminal gate required by default; `VERIFY->RESOLVE` plus RESOLVE closure artifacts carry final disposition.

**Resolve closure contract**: RESOLVE does not re-verify truth. It closes the governed run by preserving VERIFY readiness, carrying forward residual risks/deferred obligations, recording what was and was not closed, and emitting a concise operator handoff rather than raw inventories.

## Cross-phase dependency graph

```text
TRIAGE
  └─ proposals/{run_id}-triage.yaml
PROPOSE
  ├─ proposals/{run_id}.yaml
  ├─ proposals/{run_id}-package-selection.yaml
  └─ proposals/{run_id}/00-index.md + selected semantic docs
PLAN
  ├─ plans/{run_id}-scope.yaml
  ├─ plans/{run_id}-plan-selection.yaml
  ├─ plans/{run_id}/00-index.md + selected semantic docs
  └─ plans/{run_id}-piv.yaml        # Phase Intent Verification contract when required
EXECUTE
  ├─ executions/{run_id}-checkpoint-*.yaml
  └─ executions/{run_id}/00-index.md + work/evidence/drift/handoff docs
VERIFY
  ├─ verification/{run_id}-verify-selection.yaml
  ├─ verification/{run_id}-piv-assessment.yaml
  ├─ verification/{run_id}-resolve-readiness.yaml
  └─ verification/{run_id}/00-index.md + facts/assumptions/findings/readiness docs
RESOLVE
  ├─ .outputs/{run_id}-resolve-selection.yaml
  ├─ .outputs/{run_id}-closure.yaml
  └─ .outputs/{run_id}/00-index.md + closure/risk/lesson/state/handoff docs
terminal
  └─ governed state/registry disposition
```

## Escalation events (Phase 4.4 stub — parallel surface)

The `state/escalations/{run_id}.jsonl` ledger is a parallel, **non-blocking**, append-only surface separate from the gate ledger. Skills emit records via `uacp_escalation_event` when an escalation trigger in `config/uacp.toml [autonomy.escalation_triggers]` fires in the active operating mode.

Phase 4 status:
- `uacp_mode` remains a stub field with no full kernel reader.
- The kernel does not yet fully branch on mode.
- Operator engagement is via polling `state/escalations/`; push-notification is deferred.
- Trigger ID validation against the autonomy-policy registry is deferred.

## Adaptive evidence selection

Heartgate does not require a fixed evidence cluster set. TRIAGE/PROPOSE select evidence topology per run. The adaptive gates enforce that selected packages, semantic artifacts, and closure/readiness contracts are present and internally consistent. Deep artifact semantics are shared with `scripts/validate_uacp_artifacts.py` to avoid runtime/offline drift.

## Authority cross-references

- `docs/architecture/0011-semantic-package-artifacts.md`
- `docs/architecture/0012-phase-intent-verification.md`
- `docs/architecture/0013-adaptive-verify-evidence.md`
- `docs/architecture/0014-adaptive-resolve-closure.md`
- `docs/reference/skill-enforcement-spec.md`
- `docs/reference/proposal-schema.md`
- `docs/runtime/runtime-enforcement.md`
- `config/phase-transitions.yaml` (doctrine + operator knobs; gate-rule grammar codified to `engines/domain/gate_rules.py` Slice 4b)
- `engines/domain/artifact_schema.py` (`artifact_schemas_dict()` — artifact schemas codified Slice 4a; `config/artifact-schemas.yaml` deleted Slice 5)
- `config/uacp.toml` (`[guardian]` section — Guardian policy)
