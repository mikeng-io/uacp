---
type: adr
status: accepted
date: 2026-05-19
tags: [uacp, resolve, closure, lessons, operator-handoff]
---

# ADR 0014 — Adaptive RESOLVE Closure Gate

## Decision

UACP adds an adaptive RESOLVE closure gate for governed or non-trivial runs. RESOLVE is a closure phase, not a second VERIFY: it consumes VERIFY's run-bound readiness decision, preserves unresolved items, emits final closure, and records lesson/memory/skill/doc dispositions.

For selected work, RESOLVE produces a semantic closure package under `.outputs/{run_id}/` plus machine artifacts for resolve package selection and final closure.

## Rationale

VERIFY now proves whether a run is ready for closure. Without a RESOLVE gate, the lifecycle can still end with an output glob and a ledger entry while dropping residual risk, omitting lesson disposition, or returning a raw artifact inventory. Closure must preserve truth, not launder it.

## Model

RESOLVE consumes:

- `verification/{run_id}-resolve-readiness.yaml`,
- relevant VERIFY package and Heartgate coherence evidence,
- residual risks, assumptions, deferred items, warnings, and blockers,
- council/handled-finding artifacts when present.

RESOLVE produces:

- `.outputs/{run_id}-resolve-selection.yaml`,
- `.outputs/{run_id}-closure.yaml`,
- semantic package `.outputs/{run_id}/` with `00-index.md`, `closure-summary.md`, `final-decision.md`, `residual-risks.md`, `lessons-and-dispositions.md`, `state-and-memory-disposition.md`, and `operator-handoff.md`.

## Consequences

- RESOLVE blocks if VERIFY readiness is missing, stale, unbound, or not ready.
- RESOLVE blocks if open blockers remain.
- Residual risks and deferred items must be carried forward with owner and condition, not omitted.
- Lessons require explicit disposition: memory, skill, docs, knowledge, or no_action.
- Operator handoff is concise and decision-grade, not a raw file inventory.
