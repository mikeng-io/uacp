# UACP — Project Identity

**Universal Agent Control Plane** — a runtime-neutral governance framework for AI agent work.

## What UACP is

UACP separates six cognitive planes that agent work routinely conflates:

| Plane | Owns |
|---|---|
| **Governance** | Authority, side-effect declaration, write containment, evidence honesty |
| **Deliberation** | Strategy, design, council debate, finding synthesis |
| **Coordination** | Durable task state, dependencies, assignment, provenance storage |
| **Execution** | Bounded work performed by runtimes and tools |
| **Guardian + Heartgate** | Boundary enforcement — tool calls and phase transitions |
| **Tool Adapters** | Actuation and observation — web search, browser, scraping |

This separation is a reasoning invariant, not just a wiring preference. It determines which plane is authoritative for which class of decision, and prevents category errors from propagating silently through a run.

## What UACP enforces

| Surface | Mechanism |
|---|---|
| Every tool call | **Guardian** (pre-tool-call) evaluates the call against declared policy (Layer A: category-level allowed_tools; Layer B: per-phase admissibility). |
| Every phase transition | **Heartgate** (transition validator) runs deterministic checks against the transition artifact + supporting evidence (gate ledger, run registry, scope, intent, evidence-disposition pairs, lessons). |
| Every authority delegation | Declared in `.uacp/proposals/{run_id}.yaml` per `docs/reference/proposal-schema.md`. Not inferred from context. |
| Every evidence obligation | Selected adaptively per-run (by domain, risk, reversibility, artifact type) — not prescribed by a fixed checklist. |

The goal is not to add overhead. It is to ensure that when something goes wrong, the record shows exactly what was authorized, what evidence was produced, and where the boundary was crossed.

## Lifecycle (seven phases)

```
(optional) BRAINSTORM → TRIAGE → PROPOSE → PLAN → EXECUTE → VERIFY → RESOLVE
```

BRAINSTORM is pre-governance exploration (research, sketching, option enumeration). It must exit to TRIAGE before any governed work begins; it never skips TRIAGE. All other phases are mandatory and gated.

Each transition is validated by Heartgate. PIV (Phase Intent Verification, ADR-0012) is the cross-phase verification spine: PLAN authors a `uacp.phase_intent_verification_contract`, EXECUTE produces evidence against it, VERIFY judges whether the intent was met. PLAN→EXECUTE additionally requires a `PLAN_VALIDATION` ledger entry and a check against `.uacp/state/run-registry.yaml` for cross-run write-path overlap.

UACP supports two lifecycle tracks: the **standard track** (the phase sequence above) and the **goal-driven track** (ADR-0016) for semantic or exploratory work. Both tracks share the same phase sequence and governance kernel; the goal-driven track adds a persistent goal artifact and checkpoint manifest.

See [`docs/lifecycle/lifecycle-reference.md`](docs/lifecycle/lifecycle-reference.md) for canonical phase semantics and the Verification & Review Model.

## Operating modes

| Mode | Posture | Status |
|---|---|---|
| `manual` | Operator confirms every transition. Safe default. | Active. |
| `semi_auto` | Operator confirms transitions; within-phase work autonomous. | Stub-only (no kernel reader yet). |
| `supervised_auto` | UACP autonomous; operator engaged via `.uacp/state/escalations/{run_id}.jsonl` polling. | Stub-only. |
| `full_auto` | End-to-end autonomous; operator engaged only on explicit triggers. | Stub-only. Prerequisite: three verified supervised-auto runs. |

See [`docs/plans/phase5-reserved-slot.md`](docs/plans/phase5-reserved-slot.md) for the activation roadmap.

## Current objectives (June 2026)

- **Phases 0–4 kernel**: complete. [ADR-0002](docs/architecture/0002-phase0-policy-mode-and-classification.md)–[ADR-0006](docs/architecture/0006-phase4-autonomous-mode-stub.md) record the phase build; [ADR-0007](docs/architecture/0007-global-review-cross-phase-remediation.md) global remediation; [ADR-0008](docs/architecture/0008-doc-structure-and-adr-adoption.md) doc restructure.
- **Adaptive / semantic / verification series**: complete. [ADR-0009](docs/architecture/0009-adaptive-proposal-and-plan-packages.md) (adaptive PROPOSE/PLAN packages), [ADR-0010](docs/architecture/0010-operator-phase-return-presentation.md) (operator phase-return presentation), [ADR-0011](docs/architecture/0011-semantic-package-artifacts.md) (semantic-package artifacts), [ADR-0012](docs/architecture/0012-phase-intent-verification.md) (Phase Intent Verification), [ADR-0013](docs/architecture/0013-adaptive-verify-evidence.md) (adaptive VERIFY evidence), [ADR-0014](docs/architecture/0014-adaptive-resolve-closure.md) (adaptive RESOLVE closure).
- **Architecture and skill convention**: complete. [ADR-0015](docs/architecture/0015-web-backends-separate-from-bridge-adapters.md) (web-backends separate from bridge adapters), [ADR-0016](docs/architecture/0016-goal-driven-track.md) (goal-driven track), [ADR-0017](docs/architecture/0017-skill-authoring-convention.md) (skill-authoring convention).
- **Config-collapse**: complete. Phase-transition grammar codified into `skills/uacp-core/scripts/engines/domain/`; knobs in `config/uacp.toml`; doctrine stays YAML.
- **Oracle retrieval engine + lesson/knowledge corpus + BRAINSTORM phase**: built and merged. Oracle ships inert (`[oracle] enabled = false` in `config/uacp.toml`).
- **docs/ architecture refresh**: in progress. OKF enforcement + pointer hygiene across canonical docs.
- **Phase 5**: reserved slot. Activation deferred pending three verified supervised-auto runs and explicit operator authorization. See [ROADMAP.md](ROADMAP.md).

## Entry points by audience

| If you are… | Start here |
|---|---|
| New to UACP | [README.md](README.md), then [`docs/policy/constitution.md`](docs/policy/constitution.md) |
| Authoring a UACP change | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Building a runtime adapter | [`docs/runtime/runtime-integration-guide.md`](docs/runtime/runtime-integration-guide.md) |
| Investigating runtime enforcement (Guardian + Heartgate) | [`docs/runtime/runtime-enforcement.md`](docs/runtime/runtime-enforcement.md) |
| Understanding the verification and review model | [`docs/lifecycle/lifecycle-reference.md`](docs/lifecycle/lifecycle-reference.md) § Verification & Review Model |
| Looking up UACP doctrine vocabulary | [`docs/policy/first-principles.md`](docs/policy/first-principles.md) + [`docs/reference/skill-enforcement-spec.md`](docs/reference/skill-enforcement-spec.md) |
| Authoring a proposal | [`docs/reference/proposal-schema.md`](docs/reference/proposal-schema.md) |
| Using the BRAINSTORM phase or goal-driven track | [`docs/architecture/0016-goal-driven-track.md`](docs/architecture/0016-goal-driven-track.md); skill: `uacp-brainstorm` |
| Authoring or reviewing skills | [`docs/architecture/0017-skill-authoring-convention.md`](docs/architecture/0017-skill-authoring-convention.md); skill: `uacp-skills` |
| Using the Oracle / lesson-knowledge corpus | [`docs/archived/2026-06-17-oracle-engine-design.md`](docs/archived/2026-06-17-oracle-engine-design.md) (design); `config/uacp.toml` `[oracle]` section; implementation: `skills/uacp-core/scripts/engines/oracle/` |
| Investigating an architectural decision | [`docs/architecture/INDEX.md`](docs/architecture/INDEX.md) |
| Running tests / verify scripts | [COMMANDS.md](COMMANDS.md) |
| Planning Phase 5 work | [`docs/plans/phase5-reserved-slot.md`](docs/plans/phase5-reserved-slot.md) and [ROADMAP.md](ROADMAP.md) |
