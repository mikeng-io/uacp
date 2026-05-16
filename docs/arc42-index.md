---
type: index
tags: [index, arc42, architecture]
status: living-document
arc42_version: "8.0"
project_version: post-phase-4
---

# UACP ARC42 Architecture Documentation Index

**Project:** UACP — Universal Agent Control Plane
**Status:** Living Document — partial mapping
**Last Updated:** 2026-05-17
**Documentation Standard:** ARC42 v8.0 (partial — see honesty note below)

## Honesty note

ARC42 is a template for documenting **software/system architectures**. UACP is a **governance framework** — closer to a policy-and-enforcement layer than a deployable system. Several ARC42 sections (deployment view, runtime view diagrams, technology constraints) map only partially. This index uses the ARC42 skeleton where it fits and explicitly marks sections that don't.

Coverage assessment:
- ✅ **Complete**: §1 Introduction & Goals, §2 Constraints, §3 Context, §8 Concepts (governance, enforcement, lifecycle), §9 Decisions (ADRs).
- ⚠️ **Partial**: §5 Building Block View, §6 Runtime View, §10 Quality Requirements.
- ❌ **N/A or deferred**: §4 Solution Strategy (covered by ADRs instead), §7 Deployment View (UACP is runtime-neutral; deployment is deployer-specific), §11 Risks & Tech Debt (lives in ROADMAP.md propagated constraints), §12 Glossary (deferred — Phase 5 doctrine pass).

---

## §1 — Introduction & Goals

| What | Where |
|---|---|
| Project identity, scope | [`/PROJECT.md`](../PROJECT.md) |
| Quality goals (mechanical governance, traceability, runtime-neutrality) | [`policy/first-principles.md`](policy/first-principles.md) |
| Non-waivable invariants | [`policy/constitution.md`](policy/constitution.md) |
| Audience entry points | [`/PROJECT.md`](../PROJECT.md) "Entry points by audience" table |

## §2 — Architecture Constraints

| Constraint type | Where |
|---|---|
| Runtime-neutrality requirement | [`policy/constitution.md`](policy/constitution.md), [`runtime/runtime-integration-guide.md`](runtime/runtime-integration-guide.md) |
| Operator authorization model | [`/CONTRIBUTING.md`](../CONTRIBUTING.md) "What requires operator authorization" |
| Deployment-specific notes (Hermes/Norty) | [`policy/alignment-spec.md`](policy/alignment-spec.md) — labeled deployment-specific |

## §3 — System Scope and Context

| Context | Where |
|---|---|
| Cognitive-plane separation diagram (governance / deliberation / coordination / execution) | [`/README.md`](../README.md), [`lifecycle/orchestration-model.md`](lifecycle/orchestration-model.md) |
| External actors (operator, runtimes, coordination adapters) | [`lifecycle/orchestration-model.md`](lifecycle/orchestration-model.md) |
| Cross-runtime integration contract | [`runtime/runtime-integration-guide.md`](runtime/runtime-integration-guide.md) |

## §4 — Solution Strategy

UACP's solution strategy is encoded as a sequence of ADRs rather than a single solution-strategy doc. See [`architecture/INDEX.md`](architecture/INDEX.md).

| Strategic decision | ADR |
|---|---|
| Adopt record-of-architecture-decisions format | [ADR-0001](architecture/0001-record-architecture-decisions.md) |
| Phase-by-phase mechanical enforcement (vs big-bang) | [ADR-0002](architecture/0002-phase0-policy-mode-and-classification.md) onwards |
| Stub-and-defer for autonomous mode | [ADR-0006](architecture/0006-phase4-autonomous-mode-stub.md) |
| Hybrid ADR + decision-log structure | [ADR-0008](architecture/0008-doc-structure-and-adr-adoption.md) |

## §5 — Building Block View

### Black-box (level 0)

UACP comprises four planes (per [`policy/first-principles.md`](policy/first-principles.md)):

```
  ┌─────────────┐      ┌────────────────┐
  │ Governance  │◄────►│ Deliberation   │
  │ (Heartgate, │      │ (Agent Council │
  │  Guardian)  │      │  protocol)     │
  └──────┬──────┘      └────────┬───────┘
         │                      │
         ▼                      ▼
  ┌─────────────┐      ┌────────────────┐
  │ Coordination│◄────►│ Execution      │
  │ (adapter:   │      │ (runtimes,     │
  │  Hermes Kan-│      │  tools)        │
  │  ban etc.)  │      │                │
  └─────────────┘      └────────────────┘
```

### White-box: governance plane

| Component | Source | Reference |
|---|---|---|
| Guardian (per-tool-call enforcement) | `runtime-adapters/hermes/plugins/uacp_guardian/kernel.py#class Guardian` | [`runtime/runtime-enforcement.md`](runtime/runtime-enforcement.md) Guardian section |
| Heartgate (transition validator) | `kernel.py#class Heartgate` | [`runtime/runtime-enforcement.md`](runtime/runtime-enforcement.md) Heartgate section |
| Governed writers | `__init__.py#_handle_uacp_*` | [`reference/skill-enforcement-spec.md`](reference/skill-enforcement-spec.md) |
| Config layer | `config/{guardian-policy,phase-transitions,artifact-schemas,state,autonomy-policy}.yaml` | [`/docs/INDEX.md`](INDEX.md) inventory |

## §6 — Runtime View

Per-transition flow: see [`reference/lifecycle-trace-table.md`](reference/lifecycle-trace-table.md).
Per-tool-call flow: Guardian decision diagram in [`runtime/runtime-enforcement.md`](runtime/runtime-enforcement.md).

## §7 — Deployment View

⚠️ N/A at the framework level. UACP is runtime-neutral and ships no deployment configuration of its own. Deployment-specific notes (the Hermes adapter binding) are in [`policy/alignment-spec.md`](policy/alignment-spec.md) and [`runtime/runtime-porting-and-version-control.md`](runtime/runtime-porting-and-version-control.md).

## §8 — Cross-Cutting Concepts

| Concept | Where |
|---|---|
| Governance vs deliberation vs coordination vs execution | [`policy/first-principles.md`](policy/first-principles.md) |
| Six-phase lifecycle | [`lifecycle/lifecycle-reference.md`](lifecycle/lifecycle-reference.md) |
| Authority chain (spec → config → SKILL.md mirror) | [`reference/skill-enforcement-spec.md`](reference/skill-enforcement-spec.md) |
| Mechanical-over-prose enforcement | [`policy/first-principles.md`](policy/first-principles.md) |
| Agent Council protocol (tier_1 / tier_2 / heartgate) | [`lifecycle/orchestration-model.md`](lifecycle/orchestration-model.md) |
| Append-only ledger (gate ledger, escalations) with PIPE_BUF atomicity | [`runtime/runtime-enforcement.md`](runtime/runtime-enforcement.md) |
| Operating modes (manual / semi_auto / supervised_auto / full_auto) | `config/autonomy-policy.yaml`, [`/PROJECT.md`](../PROJECT.md) |
| Drift propagation between phases | [ADR-0007](architecture/0007-global-review-cross-phase-remediation.md), [`/ROADMAP.md`](../ROADMAP.md) |
| `_advisory` suffix convention | `config/autonomy-policy.yaml#advisory_field_convention` |
| `enforcement_status` tagging | [ADR-0006](architecture/0006-phase4-autonomous-mode-stub.md) |

## §9 — Architecture Decisions

Full ADR registry: [`architecture/INDEX.md`](architecture/INDEX.md).
Operational decisions log: [`decisions/decision-log.md`](decisions/decision-log.md).

## §10 — Quality Requirements

| Quality | How enforced |
|---|---|
| **Traceability** | Every transition leaves a gate-ledger entry; every artifact cites its authority; every PIV record carries per-check evidence (Phase 3 R1 / global review SKEP-G-002) |
| **Mechanical enforcement** | Heartgate's 18 checks + Guardian's two layers; no policy field is load-bearing unless a kernel reader consumes it (the `_advisory` / `enforcement_status` convention) |
| **Containment** | Per-phase Layer B allowed_tools; per-tool path refusals (state/gate-ledger, state/run-registry.yaml, state/escalations); scope.write_paths cross-check |
| **Caller-binding** | `uacp_run_registry_update` and `uacp_state_write` (for state/current.yaml) bind mutations to the caller's `uacp_run_id` |
| **Atomicity** | PIPE_BUF (3584-byte) per-record bound on JSONL ledgers; UTF-8 encoded before measurement |
| **Honesty** | Stub surfaces tagged `enforcement_status: stub_only_phase_N`; drift YAML uses explicit REMEDIATED / DEFERRED / DOCUMENTED_NOT_ENFORCED keys; lessons ledger_citations tagged `_advisory` when not byte-offset backed |

## §11 — Risks and Technical Debt

⚠️ Forward debt lives in:
- [`/ROADMAP.md`](../ROADMAP.md) — Phase 5 backlog organized by theme.
- `verification/uacp-patch-plan-20260515-phase3-codex-review.yaml#propagated_constraints.to_phase_4`, `verification/uacp-patch-plan-20260515-phase4-codex-review.yaml#propagated_constraints.to_phase_5`, and `verification/uacp-patch-plan-20260515-global-review.yaml#deferred_to_phase_5_with_evidence_pointer` — canonical evidence-pointer lists.
- [`plans/phase5-reserved-slot.md`](plans/phase5-reserved-slot.md) — Phase 5 prerequisites and activation procedure.

## §12 — Glossary

❌ Not yet authored. Phase 5 doctrine pass deliverable: `docs/policy/glossary.md` covering UACP-specific vocabulary (Heartgate, Guardian, PIV, Layer A / Layer B, council tier_1 / tier_2 / heartgate, cluster_summary, scope.write_paths, etc.). Until landed, defer to inline definitions in [`policy/first-principles.md`](policy/first-principles.md) and [`reference/skill-enforcement-spec.md`](reference/skill-enforcement-spec.md).
