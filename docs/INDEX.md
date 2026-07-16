---
type: index
tags: [index, navigation, documentation]
status: living-document
---

# UACP Documentation Index

Structural navigation map for `docs/`. For project overview, see [`/PROJECT.md`](../PROJECT.md). For ARC42 mapping, see [`arc42-index.md`](arc42-index.md). For roadmap and Phase 5 backlog, see [`/ROADMAP.md`](../ROADMAP.md).

## Root-level entry points

| File | Purpose |
|---|---|
| [`/README.md`](../README.md) | Public-facing overview (lifecycle + cognitive-plane diagrams). |
| [`/PROJECT.md`](../PROJECT.md) | Project identity, current state, audience-keyed entry points. |
| [`/ROADMAP.md`](../ROADMAP.md) | Completed phases (ADRs + commit hashes), Phase 5 reserved-slot backlog, speculative items. |
| [`/CONTRIBUTING.md`](../CONTRIBUTING.md) | Authoring contract: how to open / propose / plan / execute / verify / resolve a run. |
| [`/COMMANDS.md`](../COMMANDS.md) | Verify scripts, live probe, validator, Heartgate one-off check. |

## Documentation subdirectories

| Directory | Index | Purpose |
|---|---|---|
| [`policy/`](policy/INDEX.md) | [INDEX.md](policy/INDEX.md) | Foundational doctrine — constitution, first-principles, alignment-spec. |
| [`lifecycle/`](lifecycle/INDEX.md) | [INDEX.md](lifecycle/INDEX.md) | Six-phase lifecycle model + orchestration. |
| [`runtime/`](runtime/INDEX.md) | [INDEX.md](runtime/INDEX.md) | Guardian + Heartgate enforcement; runtime adapter integration; porting. |
| [`guides/`](guides/INDEX.md) | [INDEX.md](guides/INDEX.md) | Curated human/agent reading paths that explain how canonical docs, config, runtime, validator, skills, and fixtures fit together. |
| [`reference/`](reference/INDEX.md) | [INDEX.md](reference/INDEX.md) | Schemas + per-skill authority records (proposal-schema, skill-enforcement-spec, lifecycle-trace-table). |
| [`architecture/`](architecture/INDEX.md) | [INDEX.md](architecture/INDEX.md) | ADRs (numbered, with template + status lifecycle). |
| [`decisions/`](decisions/INDEX.md) | [INDEX.md](decisions/INDEX.md) | Operational decision-log (lighter than ADRs). |
| [`plans/`](plans/INDEX.md) | [INDEX.md](plans/INDEX.md) | Forward-looking plans only. Completed phase/feature plans were archived to `archived/`; `plans/` now holds the reserved slot (`phase5-reserved-slot.md`). |
| [`archived/`](archived/INDEX.md) | [INDEX.md](archived/INDEX.md) | Superseded docs + completed plans/designs kept for traceability. |
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
| `config/uacp.toml` (`[guardian]`) | schema_config | canonical | Guardian policy (Layer A categories, tool_classification, self_attesting_tools) — collapsed from legacy guardian-policy.yaml in Slice 3 | Update on new tool/category |
| `config/phase-transitions.yaml` | schema_config | doctrine | Adaptive-gate doctrine only (5 gate blocks: descriptions, `selected_when_any`, `block_when`, `required_*`) + unconsumed schema-doctrine remnants (`artifact_schema.fields` map, `council_synthesis_schema`). Consumed grammar (phase graph, stage/transition-artifact schema, gate/rule grammar) is codified in `skills/uacp-core/scripts/engines/domain/` (`phase_graph.py`, `phase_transitions.py`, `gate_rules.py`); operator knobs live in `config/uacp.toml [heartgate.*]`. | Update on adaptive-gate doctrine or schema-doctrine change; do NOT add grammar consumed by engine code |
| `config/state.yaml` | schema_config | generated | State pointer schema, gate-ledger schema, escalations schema, run-manifest schema, current-pointer schema | Update on new state field |
| `config/uacp.toml` (`[autonomy]`) | schema_config | canonical | Phase 4.2 stub: operating modes + escalation triggers + canonical_state_paths + advisory_field_convention — collapsed from legacy autonomy-policy.yaml in Slice 3 | Update when activating modes |
| `config/evidence-clusters.yaml` | schema_config | canonical | Adaptive evidence-cluster registry (15 cluster families) consulted by TRIAGE/PROPOSE for gate selection | Update when adding cluster families |
| `config/gate-selection.yaml` | schema_config | canonical | Phase-to-gate / cluster-to-gate mapping; selection routing rules | Update on routing-rule change |
| `config/uacp.toml` (`[memory]`) | schema_config | canonical | Memory/knowledge-bank propagation policy (Phase 2 lessons → knowledge/ promotion) — collapsed from legacy memory-policy.yaml in Slice 3 | Update on memory-policy change |
| `config/review-routing.yaml` | schema_config | canonical | Review-routing rules consumed by uacp-triage skill (council tier selection) | Update on routing-rule change |
| `config/uacp.toml` (`[runtime_bindings]`) | schema_config | canonical | Runtime-adapter binding declarations (which adapter handles which Guardian/Heartgate event class) — collapsed from legacy runtime-bindings.yaml in Slice 3 | Update on new runtime-adapter binding |
| `config/uacp.toml` (`[version_control]`) | schema_config | canonical | UACP repository, branch/worktree, remote-backup, and commit-boundary policy — collapsed from legacy version-control.yaml in Slice 3 | Keep aligned with runtime-porting policy and state/version-control docs |
| `.uacp/` | runtime_state | canonical | Governed namespace root (`config/uacp.toml [paths] base`); runtime-created — missing in a fresh clone means "no active run" | Mutate through governed writers only |
| `.uacp/state/` | runtime_state | canonical | Mutable run state layer | Mutate through governed writers only |
| `.uacp/state/current.yaml` | runtime_state | canonical | Active-run pointer (caller-bound) | Mutate through `uacp_state_write` with caller binding |
| `.uacp/state/kanban.yaml` | runtime_state | canonical | Active coordination-adapter binding | Update when board slug changes; no dedicated writer — mutated via the generic `uacp_state_write` |
| `.uacp/state/runs/` | runtime_state | canonical | Per-run manifests + checkpoint records | Append-only; exclusive owners: the `uacp_run_*` lifecycle writers |
| `docs/guides/` | documentation | explanatory | Human/agent reading paths for cross-cutting topics | Guides explain and route; they do not own canonical rules |
| `.uacp/state/gate-ledger/` | runtime_state | canonical | Append-only JSONL ledger per run | Written exclusively through `uacp_gate_ledger_append` |
| `.uacp/state/run-registry.yaml` | runtime_state | canonical | Phase 3.2 active-run registry | Exclusive mutator: `uacp_run_registry_update` |
| `.uacp/state/escalations/` | runtime_state | canonical | Phase 4.4 stub: append-only JSONL per run | Exclusive writer: `uacp_escalation_event`. Operator-polls; push-notify is Phase 5. |
| `runtime-adapters/` | runtime_adapter_source | canonical | UACP-owned runtime adapter / plugin source | Source changes require binding verification + rollback evidence |
| `scripts/` | verification_tooling | canonical | Phase verify (`phase{0..4}_verify.py`) + live probe scripts that lock in propagated-constraint remediations as machine-checked invariants | Every fail-closed kernel branch needs a paired check |
| `.uacp/plans/`, `.uacp/proposals/`, `.uacp/executions/`, `.uacp/verification/`, `.uacp/resolutions/`, `.uacp/knowledge/`, `.uacp/lessons/`, `.uacp/brainstorm/` | run_artifact_roots | canonical | Per-run lifecycle artifact directories (`config/uacp.toml [paths]`; `resolutions/` replaces the old `.outputs/`) | Append-only per-run state; do not overwrite historical |
| `UACP.md` | entry_point | canonical | The injected cognition preamble (comprehend → measure → serialize) named by AGENTS.md | Update when the core principle changes |
| `skills/` | skill_source | canonical | Authority Layer 5 — the `skills/uacp-*` governed family implementing the documented rules | Changes follow the skill convention ([ADR-0017](architecture/0017-skill-authoring-convention.md)) |
| `codeflair/` | witness_source | canonical | Deterministic code-plane witness; the cascade-witness gate execs it via `config/uacp.toml [witness] codeflair_cli` (unconfigured → inert) | Source changes require witness parity evidence |
| `config/verification-floor.yaml` | schema_config | canonical | Verification-floor policy consumed by `engines/domain/verification_floor.py` | Update on floor-policy change |
| `design/` | design_source | explanatory | Decomposed design bundles (one topic per directory) — pre-build rationale, not canonical policy | Design-convention lint enforced (`design_lint.py`) |
| `tests/` | verification_tooling | canonical | Unit/integration/e2e/acceptance suites — the final arbiter for kernel behavior | Every fail-closed kernel branch needs a paired test |
| `acceptance/` | verification_tooling | canonical | Containerized plugin-conformance harness (`make acceptance`) | Update when the plugin surface changes |

## Read-order for most work

When approaching UACP cold, this order minimizes back-tracking:

1. [`/PROJECT.md`](../PROJECT.md) — what UACP is.
2. [`policy/first-principles.md`](policy/first-principles.md) ("The Conformance Loop for Semantic Work") + [`architecture/0021-telos-conformance-loop.md`](architecture/0021-telos-conformance-loop.md) — **why UACP exists** (bedrock, canonical): the telos (reduce the long-run friction of cooperation on semantic work), the conformance loop it governs, and how CMS / gates / lifecycle / the memory substrate derive from it. Design rationale trail: [`design/telos/`](../design/telos/00-telos.md) (non-canonical, explanatory).
3. [`policy/constitution.md`](policy/constitution.md) — non-negotiables (derives from the first principles above).
4. [`lifecycle/lifecycle-reference.md`](lifecycle/lifecycle-reference.md) — phase semantics + the **single source of truth for the verification & review model** (six mechanisms / three layers: Guardian, Agent Council, exit invariants/PLAN_VALIDATION, Heartgate, PIV, the VERIFY phase; plus the PIV-acronym disambiguation).
5. [`reference/proposal-schema.md`](reference/proposal-schema.md) + [`reference/skill-enforcement-spec.md`](reference/skill-enforcement-spec.md) + [`reference/lifecycle-trace-table.md`](reference/lifecycle-trace-table.md) — canonical schemas.
6. [`runtime/runtime-enforcement.md`](runtime/runtime-enforcement.md) — how Guardian + Heartgate enforce.
7. [`guides/lifecycle-hardening/00-index.md`](guides/lifecycle-hardening/00-index.md) — readable guide to semantic packages, PIV, VERIFY/RESOLVE, runtime parity, and full-lineage audit remediation.
8. [`architecture/INDEX.md`](architecture/INDEX.md) — historical decisions.

For runtime adapter authors, add: [`runtime/runtime-integration-guide.md`](runtime/runtime-integration-guide.md), [`runtime/runtime-porting-and-version-control.md`](runtime/runtime-porting-and-version-control.md).

For Phase 5 planners, add: [`plans/phase5-reserved-slot.md`](plans/phase5-reserved-slot.md), [`/ROADMAP.md`](../ROADMAP.md).

## Document hygiene rules

- Every new top-level doc must appear in this index AND its appropriate subdirectory INDEX.md.
- ADR status lifecycle is enforced: `proposed → accepted → (deprecated | superseded by ADR-NNNN)`. Never edit accepted ADRs in place; supersede them.
- The `_advisory` suffix or `enforcement_status: stub_only_phase_N` is mandatory for any YAML field that LOOKS like enforcement but has no kernel reader (introduced [ADR-0006](architecture/0006-phase4-autonomous-mode-stub.md), reinforced [ADR-0007](architecture/0007-global-review-cross-phase-remediation.md)).
- Superseded docs move to `docs/archived/` with a first-paragraph supersession notice, not deleted.
