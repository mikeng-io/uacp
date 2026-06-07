# RESOLVE closure-gate checklist

Use this reference when closing UACP runs or maintaining the RESOLVE skill/validator.

## Purpose

RESOLVE is the closure phase. It is not a second VERIFY. It consumes `verification/{run_id}-resolve-readiness.yaml`, preserves unresolved items, emits final closure, and decides what belongs in memory, skills, docs, knowledge, or no-action.

## Required closure package

For governed/non-trivial work, expect:

- `..outputs/{run_id}-resolve-selection.yaml`
- `..outputs/{run_id}-closure.yaml`
- `..outputs/{run_id}/00-index.md`
- `closure-summary.md`
- `final-decision.md`
- `residual-risks.md`
- `lessons-and-dispositions.md`
- `state-and-memory-disposition.md`
- `operator-handoff.md`

## Must-block cases

Block closure when:

- VERIFY readiness is missing, stale, unrelated, or `ready_for_resolve` is not true
- open blockers remain in readiness or closure
- residual risks/deferred items from VERIFY are dropped instead of carried forward
- deferred items lack owner, accepted_by, condition, source, or next-phase obligation
- final decision lacks status/decision/rationale/accepted_by/evidence pointer
- lesson disposition is missing, ambiguous, or tries to write memory/skill/docs without rationale, durability, risk_if_persisted, accepted_by, and target artifact
- operator handoff is a raw file inventory instead of a decision-grade summary
- closed scope is not bound to evidence via source artifact and evidence reference
- state disposition has invalid run status or memory action

## Lesson disposition rule

Classify each lesson as exactly one of:

- `memory`
- `skill`
- `docs`
- `knowledge`
- `no_action`

Most run-specific noise should be `no_action` with rationale. Do not save task progress, PR IDs, transient tool failures, or stale artifact details to memory.

## Reporting discipline

RESOLVE should state conclusion, closed scope, residual risks, deferred items, lesson disposition, next/not-next, and evidence pointer. Raw artifact inventories stay in artifacts, not operator chat.