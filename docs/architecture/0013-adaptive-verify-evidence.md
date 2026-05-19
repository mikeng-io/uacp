---
type: adr
status: accepted
date: 2026-05-19
tags: [uacp, verify, evidence, resolve-readiness, heartgate]
---

# ADR 0013 — Adaptive VERIFY Evidence Gate

## Decision

UACP adds an adaptive VERIFY evidence gate for governed or non-trivial runs. VERIFY is the phase that judges truth: it must not merely check that artifacts exist, and it must not remediate material findings then self-certify closure.

For selected work, VERIFY produces a semantic verification package under `verification/{run_id}/` plus machine artifacts for verification package selection, PIV assessment, and resolve readiness. The gate separates verified facts from assumptions/deferred items, records finding dispositions, and proves whether RESOLVE may safely close the run.

## Rationale

PROPOSE, PLAN, and EXECUTE now have semantic packages and PIV-backed execution evidence. Without an equivalent VERIFY gate, a run can still pass on YAML-only verification, raw summaries, unsupported facts, unowned assumptions, or unresolved council concerns. VERIFY must be stricter than EXECUTE because it is the truth boundary before RESOLVE.

## Model

VERIFY consumes:

- proposal and PLAN packages,
- PLAN-authored PIV contract when present,
- EXECUTE checkpoints and semantic package,
- deterministic validation evidence,
- council synthesis and handled findings,
- verified facts and assumptions/deferred items,
- Heartgate coherence when the transition risk requires it.

VERIFY produces:

- `verification/{run_id}-verify-selection.yaml`,
- `verification/{run_id}-piv-assessment.yaml` when EXECUTE used PIV,
- `verification/{run_id}-resolve-readiness.yaml`,
- semantic package `verification/{run_id}/` with `00-index.md`, `piv-assessment.md`, `verified-facts.md`, `assumptions-and-deferred-items.md`, `findings-and-dispositions.md`, `council-review.md`, and `resolve-readiness.md`.

## Consequences

- Facts require source evidence and must not be assumption prose.
- Assumptions/deferred items require owner, accepted_by, residual risk, and next-phase obligation.
- Open blockers or unresolved material findings block resolve readiness.
- VERIFY self-remediation of material findings blocks unless routed back to EXECUTE/PLAN or independently re-verified.
- Heartgate coherence remains distinct from phase-local council synthesis.
