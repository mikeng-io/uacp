# Architecture Decision Records — Index

UACP adopts the ADR (Architecture Decision Record) format for durable architectural decisions. Each ADR is a single file with stable identity, status lifecycle, and explicit superseded relationships. Lighter operational decisions live in [`../decisions/decision-log.md`](../decisions/decision-log.md).

## ADR Lifecycle

```
proposed → accepted → (deprecated | superseded by ADR-NNNN)
```

The template is at [0000-template.md](0000-template.md). Numbering is sequential; superseded ADRs are kept (not deleted) and linked from their successor.

## ADRs

| ID | Title | Status |
|---|---|---|
| [0000](0000-template.md) | ADR Template | template |
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | accepted |
| [0002](0002-phase0-policy-mode-and-classification.md) | Phase 0 — wire filesystem_guard_verified, real policy.mode, classify governed tools | accepted |
| [0003](0003-phase1-gate-ledger-layer-b-piv.md) | Phase 1 — mechanical pre-flight contracts (gate ledger, Layer B, phase exit invariants, PIV) | accepted |
| [0004](0004-phase2-artifact-schemas.md) | Phase 2 — structured artifact schemas with Heartgate enforcement | accepted |
| [0005](0005-phase3-plan-validation-gate-and-run-registry.md) | Phase 3 — plan_validation_gate, run_registry, authority docs | accepted |
| [0006](0006-phase4-autonomous-mode-stub.md) | Phase 4 — uacp_mode, autonomy-policy, escalation-event stub | accepted |
| [0007](0007-global-review-cross-phase-remediation.md) | Global review — cross-phase audit and R1/R2 remediation | accepted |
| [0008](0008-doc-structure-and-adr-adoption.md) | Adopt subdirectory + ADR documentation structure | accepted |
| [0009](0009-adaptive-proposal-and-plan-packages.md) | Adaptive PROPOSE and PLAN documentation packages | accepted |
| [0010](0010-operator-phase-return-presentation.md) | Separate operator phase returns from raw evidence | accepted |
| [0011](0011-semantic-package-artifacts.md) | Treat UACP package Markdown as semantic substrate | accepted |
| [0012](0012-phase-intent-verification.md) | Phase Intent Verification | accepted |
| [0013](0013-adaptive-verify-evidence.md) | Adaptive VERIFY evidence gate | accepted |
| [0014](0014-adaptive-resolve-closure.md) | Adaptive RESOLVE closure gate | accepted |
| [0015](0015-web-backends-separate-from-bridge-adapters.md) | Web backends remain separate from bridge-* runtime adapters | accepted |
| [0016](0016-goal-driven-track.md) | Goal-driven track — second lifecycle track for semantic/exploratory work | accepted |
| [0017](0017-skill-authoring-convention.md) | UACP skill-authoring convention | accepted |
| [0018](0018-cms-semantic-thinking-principle.md) | CMS — comprehend → measure → serialize as the principle for semantic thinking | accepted |
| [0019](0019-pretooluse-hook-narrow-scope-and-invariant-3-clarification.md) | PreToolUse hook narrow scope and Invariant #3 clarification | proposed |
| [0020](0020-runtime-adapters-regroup-by-runtime.md) | Regroup runtime-adapters by runtime with a shared layer | proposed |

## Related

- Operational decisions (lighter weight): [`../decisions/decision-log.md`](../decisions/decision-log.md).
- ARC42 mapping of UACP architecture: [`../arc42-index.md`](../arc42-index.md).
