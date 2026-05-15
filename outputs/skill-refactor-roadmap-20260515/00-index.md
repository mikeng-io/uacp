# UACP Skill Refactor Roadmap Capture — 2026-05-15

Purpose: preserve the complete refactor intent before implementation. This is not a UACP lifecycle run and does not claim UACP authority. It is a split planning capture for rebuilding UACP skills because the current UACP skill layer is structurally broken.

## File map

- `01-rationale.md` — why this refactor exists and why one document is insufficient.
- `02-current-failure-analysis.md` — what is broken in current UACP skill/docs structure.
- `03-operating-method.md` — the required Explore → Determine → Decision → Review → Audit → Implement loop.
- `04-skill-order-and-scope.md` — exact one-skill-at-a-time sequence and boundaries.
- `05-phase-contract-template.md` — detailed contract each skill phase must produce before implementation.
- `06-target-skill-module-shape.md` — ACP/Anthropic modular skill package target shape.
- `07-measurement-and-audit.md` — measurements, pass/fail checks, context hygiene metrics.
- `08-variants-and-decision-space.md` — acceptable variants and rejected approaches.
- `09-memory-and-recall-rules.md` — rules for looking back into memory/session history during determinations.
- `10-implementation-roadmap.md` — concrete phase list in execution order.
- `11-risk-register.md` — risks, failure modes, mitigations.
- `12-non-goals.md` — things explicitly not to do.

## Canonical short rule

One skill at a time. For each skill: Explore, Determine, Decision, Review, Audit, Implement. Do not bulk-enrich, do not centralize into one mega-SOP, and do not use broken UACP machinery to govern this refactor.
