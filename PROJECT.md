# UACP — Project Identity

**Universal Agent Control Plane** — a runtime-neutral governance framework for AI agent work.

## What UACP is

UACP separates four cognitive planes that agent work routinely conflates:

| Plane | Owns |
|---|---|
| **Governance** | Authority, side-effect declaration, write containment, evidence honesty |
| **Deliberation** | Strategy, design, council debate, finding synthesis |
| **Coordination** | Durable task state, dependencies, assignment, provenance storage |
| **Execution** | Bounded work performed by runtimes and tools |

This separation is a reasoning invariant, not just a wiring preference. It determines which plane is authoritative for which class of decision, and prevents category errors from propagating silently through a run.

## What UACP enforces

| Surface | Mechanism |
|---|---|
| Every tool call | **Guardian** (pre-tool-call) evaluates the call against declared policy (Layer A: category-level allowed_tools; Layer B: per-phase admissibility). |
| Every phase transition | **Heartgate** (transition validator) runs 18 deterministic checks against the transition artifact + supporting evidence (gate ledger, run registry, scope, intent, evidence-disposition pairs, lessons). |
| Every authority delegation | Declared in `proposals/{run_id}.yaml` per `docs/reference/proposal-schema.md`. Not inferred from context. |
| Every evidence obligation | Selected adaptively per-run (by domain, risk, reversibility, artifact type) — not prescribed by a fixed checklist. |

The goal is not to add overhead. It is to ensure that when something goes wrong, the record shows exactly what was authorized, what evidence was produced, and where the boundary was crossed.

## Lifecycle (six phases)

```
TRIAGE → PROPOSE → PLAN → EXECUTE → VERIFY → RESOLVE
```

Each transition is gated. PIV (Post-Phase Verification) runs at the end of every phase with per-check pass evidence. PLAN→EXECUTE additionally requires a `PLAN_VALIDATION` ledger entry covering all six pv_ids and a check against `state/run-registry.yaml` for cross-run write-path overlap.

See [`docs/lifecycle/lifecycle-reference.md`](docs/lifecycle/lifecycle-reference.md) for the canonical phase semantics.

## Operating modes (Phase 4 stub; Phase 5 activation)

| Mode | Posture | Phase 4 status |
|---|---|---|
| `manual` | Operator confirms every transition. Safe default. | Active. |
| `semi_auto` | Operator confirms transitions; within-phase work autonomous. | Stub-only (no kernel reader yet). |
| `supervised_auto` | UACP autonomous; operator engaged via `state/escalations/{run_id}.jsonl` polling. | Stub-only. |
| `full_auto` | End-to-end autonomous; operator engaged only on explicit triggers. | Stub-only. Phase 5 prerequisite: three verified supervised-auto runs. |

See [`docs/plans/phase5-reserved-slot.md`](docs/plans/phase5-reserved-slot.md) for the activation roadmap.

## Current objectives

- **Phases 0–4**: complete. Six ADRs ([ADR-0002](docs/architecture/0002-phase0-policy-mode-and-classification.md) through [ADR-0007](docs/architecture/0007-global-review-cross-phase-remediation.md)) record the evolution.
- **Phase 5**: reserved slot. Activation deferred pending three verified supervised-auto runs and explicit operator authorization. See [ROADMAP.md](ROADMAP.md) for the Phase 5 backlog.
- **Doc structure**: subdirectory + ADR adoption complete ([ADR-0008](docs/architecture/0008-doc-structure-and-adr-adoption.md)).

## Entry points by audience

| If you are… | Start here |
|---|---|
| New to UACP | [README.md](README.md), then [`docs/policy/constitution.md`](docs/policy/constitution.md) |
| Authoring a UACP change | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Building a runtime adapter | [`docs/runtime/runtime-integration-guide.md`](docs/runtime/runtime-integration-guide.md) |
| Investigating runtime enforcement | [`docs/runtime/runtime-enforcement.md`](docs/runtime/runtime-enforcement.md) (Guardian + Heartgate full check list) |
| Looking up UACP doctrine vocabulary | [`docs/policy/first-principles.md`](docs/policy/first-principles.md) + [`docs/reference/skill-enforcement-spec.md`](docs/reference/skill-enforcement-spec.md) (Phase 5 will add `docs/policy/glossary.md`) |
| Authoring a proposal | [`docs/reference/proposal-schema.md`](docs/reference/proposal-schema.md) |
| Investigating an architectural decision | [`docs/architecture/INDEX.md`](docs/architecture/INDEX.md) |
| Running tests / verify scripts | [COMMANDS.md](COMMANDS.md) |
| Planning Phase 5 work | [`docs/plans/phase5-reserved-slot.md`](docs/plans/phase5-reserved-slot.md) and [ROADMAP.md](ROADMAP.md) |
