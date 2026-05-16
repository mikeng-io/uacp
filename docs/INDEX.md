---
type: index
tags: [index, navigation, documentation]
status: living-document
---

# UACP Documentation Index

Structural navigation map for `docs/`. For project overview, see [`/PROJECT.md`](/PROJECT.md). For ARC42 mapping, see [`arc42-index.md`](arc42-index.md). For roadmap and Phase 5 backlog, see [`/ROADMAP.md`](/ROADMAP.md).

## Root-level entry points

| File | Purpose |
|---|---|
| [`/README.md`](/README.md) | Public-facing overview (lifecycle + cognitive-plane diagrams). |
| [`/PROJECT.md`](/PROJECT.md) | Project identity, current state, audience-keyed entry points. |
| [`/ROADMAP.md`](/ROADMAP.md) | Completed phases (ADRs + commit hashes), Phase 5 reserved-slot backlog, speculative items. |
| [`/CONTRIBUTING.md`](/CONTRIBUTING.md) | Authoring contract: how to open / propose / plan / execute / verify / resolve a run. |
| [`/COMMANDS.md`](/COMMANDS.md) | Verify scripts, live probe, validator, Heartgate one-off check. |

## Documentation subdirectories

| Directory | Index | Purpose |
|---|---|---|
| [`policy/`](policy/INDEX.md) | [INDEX.md](policy/INDEX.md) | Foundational doctrine — constitution, first-principles, alignment-spec. |
| [`lifecycle/`](lifecycle/INDEX.md) | [INDEX.md](lifecycle/INDEX.md) | Six-phase lifecycle model + orchestration. |
| [`runtime/`](runtime/INDEX.md) | [INDEX.md](runtime/INDEX.md) | Guardian + Heartgate enforcement; runtime adapter integration; porting. |
| [`reference/`](reference/INDEX.md) | [INDEX.md](reference/INDEX.md) | Schemas + per-skill authority records (proposal-schema, skill-enforcement-spec, lifecycle-trace-table). |
| [`architecture/`](architecture/INDEX.md) | [INDEX.md](architecture/INDEX.md) | ADRs (numbered, with template + status lifecycle). |
| [`decisions/`](decisions/INDEX.md) | [INDEX.md](decisions/INDEX.md) | Operational decision-log (lighter than ADRs). |
| [`plans/`](plans/INDEX.md) | [INDEX.md](plans/INDEX.md) | Forward-looking phase plans, reserved slots. |
| [`archived/`](archived/INDEX.md) | [INDEX.md](archived/INDEX.md) | Superseded docs kept for traceability. |
| [`arc42-index.md`](arc42-index.md) | — | Partial ARC42 mapping of UACP architecture. |

## Repository inventory (non-docs)

The canonical inventory of UACP-owned files outside `docs/`. Every file here MUST appear; orphaned files are a doc-staleness signal.

| Path | Class | Status | Purpose | Update rule |
|---|---|---|---|---|
| `README.md` | entry_point | canonical | Public-facing project overview | Update on major doctrine change |
| `PROJECT.md` | entry_point | canonical | Project identity + state | Update when phase complete |
| `ROADMAP.md` | entry_point | canonical | Phase status + Phase 5 backlog | Update when phase complete or constraints propagated |
| `CONTRIBUTING.md` | entry_point | canonical | Authoring contract | Update when contract changes |
| `COMMANDS.md` | entry_point | canonical | Build/run/test commands | Update when scripts change |
| `config/guardian-policy.yaml` | schema_config | generated | Guardian policy seed (Layer A categories, tool_classification, self_attesting_tools) | Update on new tool/category |
| `config/phase-transitions.yaml` | schema_config | generated | Phase-stage admissibility + Heartgate gates (incl. plan_validation_gate, run_registry_rule, piv_rule) | Update on new phase or transition rule |
| `config/state.yaml` | schema_config | generated | State pointer schema, gate-ledger schema, escalations schema, run-manifest schema, current-pointer schema | Update on new state field |
| `config/artifact-schemas.yaml` | schema_config | generated | Phase-2 artifact schemas (scope, intent, evidence_disposition, lessons) + Phase-3 run_registry schema + cross_checks (handler_refusals, tool_path_capabilities) | Update on new artifact class |
| `config/autonomy-policy.yaml` | schema_config | generated | Phase 4.2 stub: operating modes + escalation triggers + canonical_state_paths + advisory_field_convention | Update when activating modes |
| `config/evidence-clusters.yaml` | schema_config | canonical | Adaptive evidence-cluster registry (15 cluster families) consulted by TRIAGE/PROPOSE for gate selection | Update when adding cluster families |
| `config/gate-selection.yaml` | schema_config | canonical | Phase-to-gate / cluster-to-gate mapping; selection routing rules | Update on routing-rule change |
| `config/memory-policy.yaml` | schema_config | canonical | Memory/knowledge-bank propagation policy (Phase 2 lessons → knowledge/ promotion) | Update on memory-policy change |
| `config/review-routing.yaml` | schema_config | canonical | Review-routing rules consumed by uacp-triage skill (council tier selection) | Update on routing-rule change |
| `config/roots.yaml` | schema_config | canonical | Canonical UACP_ROOT-relative path roots + symbolic root declarations | Rarely changes; coordinate with runtime adapters |
| `config/runtime-bindings.yaml` | schema_config | canonical | Runtime-adapter binding declarations (which adapter handles which Guardian/Heartgate event class) | Update on new runtime-adapter binding |
| `config/version-control.yaml` | schema_config | canonical | UACP repository, branch/worktree, remote-backup, and commit-boundary policy | Keep aligned with runtime-porting policy and state/version-control docs |
| `state/` | runtime_state | canonical | Mutable run state layer | Mutate through governed writers only |
| `state/current.yaml` | runtime_state | canonical | Active-run pointer (caller-bound) | Mutate through `uacp_state_write` with caller binding |
| `state/kanban.yaml` | runtime_state | canonical | Active coordination-adapter binding | Update when board slug changes |
| `state/runs/` | runtime_state | canonical | Per-run manifests + checkpoint records | Append-only; do not overwrite |
| `state/gate-ledger/` | runtime_state | canonical | Append-only JSONL ledger per run | Written exclusively through `uacp_gate_ledger_append` |
| `state/run-registry.yaml` | runtime_state | canonical | Phase 3.2 active-run registry | Exclusive mutator: `uacp_run_registry_update` |
| `state/escalations/` | runtime_state | canonical | Phase 4.4 stub: append-only JSONL per run | Exclusive writer: `uacp_escalation_event`. Operator-polls; push-notify is Phase 5. |
| `runtime-adapters/` | runtime_adapter_source | canonical | UACP-owned runtime adapter / plugin source | Source changes require binding verification + rollback evidence |
| `scripts/` | verification_tooling | canonical | Phase verify (`phase{0..4}_verify.py`) + live probe scripts that lock in propagated-constraint remediations as machine-checked invariants | Every fail-closed kernel branch needs a paired check |
| `plans/`, `proposals/`, `executions/`, `verification/`, `outputs/`, `knowledge/` | run_artifact_roots | canonical | Per-run lifecycle artifact directories | Append-only per-run state; do not overwrite historical |

## Read-order for most work

When approaching UACP cold, this order minimizes back-tracking:

1. [`/PROJECT.md`](/PROJECT.md) — what UACP is.
2. [`policy/constitution.md`](policy/constitution.md) + [`policy/first-principles.md`](policy/first-principles.md) — non-negotiables.
3. [`lifecycle/lifecycle-reference.md`](lifecycle/lifecycle-reference.md) — phase semantics.
4. [`reference/proposal-schema.md`](reference/proposal-schema.md) + [`reference/skill-enforcement-spec.md`](reference/skill-enforcement-spec.md) + [`reference/lifecycle-trace-table.md`](reference/lifecycle-trace-table.md) — canonical schemas.
5. [`runtime/runtime-enforcement.md`](runtime/runtime-enforcement.md) — how Guardian + Heartgate enforce.
6. [`architecture/INDEX.md`](architecture/INDEX.md) — historical decisions.

For runtime adapter authors, add: [`runtime/runtime-integration-guide.md`](runtime/runtime-integration-guide.md), [`runtime/runtime-porting-and-version-control.md`](runtime/runtime-porting-and-version-control.md).

For Phase 5 planners, add: [`plans/phase5-reserved-slot.md`](plans/phase5-reserved-slot.md), [`/ROADMAP.md`](/ROADMAP.md).

## Document hygiene rules

- Every new top-level doc must appear in this index AND its appropriate subdirectory INDEX.md.
- ADR status lifecycle is enforced: `proposed → accepted → (deprecated | superseded by ADR-NNNN)`. Never edit accepted ADRs in place; supersede them.
- The `_advisory` suffix or `enforcement_status: stub_only_phase_N` is mandatory for any YAML field that LOOKS like enforcement but has no kernel reader (introduced [ADR-0006](architecture/0006-phase4-autonomous-mode-stub.md), reinforced [ADR-0007](architecture/0007-global-review-cross-phase-remediation.md)).
- Superseded docs move to `docs/archived/` with a first-paragraph supersession notice, not deleted.
