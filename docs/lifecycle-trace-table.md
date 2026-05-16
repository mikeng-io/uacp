# UACP Lifecycle Trace Table

This document is the cross-phase artifact dependency map for UACP. For each phase transition, it lists required inputs, required outputs, Heartgate checks, and the gate-ledger entry that records the transition's evaluation.

The kernel reads this dependency model from `config/phase-transitions.yaml`, `config/artifact-schemas.yaml`, and `config/guardian-policy.yaml`. This document is the canonical reading-order narrative that humans use to verify the model is coherent end-to-end.

## Transitions

### `none → TRIAGE` (run start)

| Aspect | Detail |
|---|---|
| Required inputs | A request from the operator (chat, ticket, scheduled trigger) |
| Required outputs | `proposals/{run_id}-triage.yaml`, `state/runs/{run_id}-triage.yaml`, `state/current.yaml` updated |
| Heartgate checks | none (TRIAGE is the entry point) |
| Gate ledger | `gate: TRIAGE_COMPLETE` (optional; recorded by uacp-triage at end of phase) |

### `TRIAGE → PROPOSE`

| Aspect | Detail |
|---|---|
| Required inputs | Triage artifact at `proposals/{run_id}-triage*.yaml` |
| Required outputs | `proposals/{run_id}*.yaml` (the proposal), `proposals/{run_id}-intent.md` (Phase 2.3) |
| Heartgate checks | required_fields, transition_allowed, invariant_summary, cluster_summary, blockers, warnings, deferred_items, heartgate_coherence (when required), phase_exit_invariants, piv_record, **intent_doc** |
| Gate ledger | `gate: TRIAGE->PROPOSE` |

### `PROPOSE → PLAN`

| Aspect | Detail |
|---|---|
| Required inputs | Proposal artifact `proposals/{run_id}.yaml` matching `docs/proposal-schema.md` |
| Required outputs | `plans/{run_id}*` (plan artifacts), `plans/{run_id}-scope.yaml` (Phase 2.1) |
| Heartgate checks | all Phase 1 checks + phase_exit_invariants + piv_record |
| Gate ledger | `gate: PROPOSE->PLAN` |

### `PLAN → EXECUTE` (highest-cardinality enforcement boundary)

| Aspect | Detail |
|---|---|
| Required inputs | Plan artifacts + `plans/{run_id}-scope.yaml` |
| Required outputs | `executions/{run_id}*` (execute checkpoints) |
| Heartgate checks | all Phase 1 + phase_exit_invariants + piv_record + **scope_artifact** (Phase 2.1) + **plan_validation_gate** (Phase 3.1) + **run_registry_overlap** (Phase 3.2) |
| Gate ledger | `gate: PLAN_VALIDATION` (pre-execute), then `gate: PLAN->EXECUTE` (transition) |

**Scope artifact contract**: every entry in `scope.write_paths` must be reachable by at least one tool in `config/phase-transitions.yaml stages.execute.allowed_tools` per the `tool_path_capabilities` map. Unreachable write_paths block.

**Run registry contract**: `state/run-registry.yaml#active_runs[*]` lists in-progress runs. Heartgate blocks if any other active run's `write_paths` overlap this run's.

### `EXECUTE → VERIFY`

| Aspect | Detail |
|---|---|
| Required inputs | `executions/{run_id}*` checkpoints |
| Required outputs | `verification/{run_id}*` artifacts, including disposition pairs |
| Heartgate checks | all prior checks + phase_exit_invariants + piv_record |
| Gate ledger | `gate: EXECUTE->VERIFY` |

### `VERIFY → RESOLVE`

| Aspect | Detail |
|---|---|
| Required inputs | `verification/{run_id}*` artifacts |
| Required outputs | `outputs/{run_id}*` (resolution artifacts), `outputs/{run_id}-lessons.yaml` (Phase 2.4) |
| Heartgate checks | all prior checks + **evidence_dispositions** (Phase 2.2) + **lessons_artifact** (Phase 2.4) |
| Gate ledger | `gate: VERIFY->RESOLVE` |

**Evidence disposition contract**: for each cluster in `cluster_summary` with state not in `{deferred, not_applicable}`:
- `verification/{run_id}-{cluster}-verified-facts.md` must exist and contain the documented header substring `"Fact"`.
- `verification/{run_id}-{cluster}-assumptions.md` must exist and contain `"Disposition"`.
- No row in the assumptions table may have `pending` disposition without a non-empty Owner AND non-empty Next-phase obligation.
- `cluster_summary` must not be empty (Phase 3 pc_p2_t3).

**Lessons contract**: `outputs/{run_id}-lessons.yaml` must be a YAML mapping with `run_id` (string) and `lessons` (list).

### `RESOLVE → terminal` (run complete)

| Aspect | Detail |
|---|---|
| Required inputs | All RESOLVE outputs landed and committed |
| Required outputs | `state/current.yaml` updated to mark run resolved |
| Heartgate checks | all prior checks |
| Gate ledger | (none required; run-state pointer carries the final disposition) |

## Cross-phase dependency graph

```
TRIAGE                  triage artifact (proposals/{run_id}-triage*.yaml)
  │  intent doc        (proposals/{run_id}-intent.md)        ◄── Heartgate 2.3
  ▼
PROPOSE                 proposal artifact (proposals/{run_id}.yaml)
  │
  ▼
PLAN                    plan artifacts (plans/{run_id}/*)
  │  scope artifact    (plans/{run_id}-scope.yaml)            ◄── Heartgate 2.1
  │  PLAN_VALIDATION   (ledger entry)                          ◄── Heartgate 3.1
  ▼
EXECUTE                 execute checkpoints (executions/{run_id}*)
  │  guarded writes governed by scope.write_paths             ◄── Layer A + Layer B
  │  run_registry overlap check                                ◄── Heartgate 3.2
  ▼
VERIFY                  evidence + disposition pairs (verification/{run_id}-*)
  │  disposition pairs per non-NA non-deferred cluster        ◄── Heartgate 2.2
  ▼
RESOLVE                 outputs + structured lessons (outputs/{run_id}-*)
  │  lessons artifact with ledger_citations                   ◄── Heartgate 2.4
  ▼
terminal               state/current.yaml pointer updated
```

## Adaptive evidence selection

Heartgate does not enforce a fixed cluster set. The `cluster_summary` in the transition artifact is chosen by the meta-gate (TRIAGE) and may be revised at PROPOSE. The 15 cluster families in `config/evidence-clusters.yaml` are templates; concrete cluster IDs are picked per-run.

This trace table describes the **structural** dependency between phases. The **evidence** model is per-run.

## Authority cross-references

- `docs/skill-enforcement-spec.md` — what each skill may do
- `docs/proposal-schema.md` — uacp.propose artifact reference
- `docs/runtime-enforcement.md` — Guardian + Heartgate runtime design (with the full 16-step Heartgate check list)
- `config/phase-transitions.yaml` — phase admissibility, exit invariants, piv_rule, plan_validation_gate, run_registry_rule
- `config/artifact-schemas.yaml` — scope, intent, evidence_disposition, lessons
- `config/guardian-policy.yaml` — Layer A categories, self_attesting_tools, mode
