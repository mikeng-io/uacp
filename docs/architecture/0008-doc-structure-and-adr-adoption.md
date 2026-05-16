---
type: adr
status: accepted
---

# Adopt subdirectory + ADR documentation structure

## Metadata

- **Status**: accepted
- **Date**: 2026-05-17
- **Decision Makers**: operator
- **Consulted**: maintainer (cross-referenced trustless-acp doc pattern)
- **Informed**: future doc authors, Phase 5 implementer

## Context and Problem Statement

By the close of the UACP patch plan (Phases 0–4 + Resolve + Global Review = 7 commits), `docs/` contained 14 flat files totaling ~3,100 lines. The flat structure conflated four distinct concerns: foundational doctrine, lifecycle model, runtime enforcement, schemas. The single `decision-log.md` (26 entries) had no stable per-decision identity. The sibling project (Trustless ACP) demonstrated a working ADR + subdirectory pattern that solved both problems.

## Decision Drivers

- Cross-reference stability: ADRs are linkable by number; subdirectories make doc-class membership explicit.
- Authoring ergonomics: smaller, semantically-grouped indexes reduce cognitive load.
- Cross-project alignment: trustless-acp has demonstrated the pattern works at scale (15+ subdirectories, 156 docs).
- Phase 5 doctrine pass is upcoming; restructuring now avoids carrying technical debt forward.

## Considered Options

1. **Keep flat `docs/` and add cross-reference index** — rejected; doesn't solve the decision-log identity problem or the cognitive-load problem.
2. **Subdirectory restructure + ADR adoption (hybrid: ADRs for architecture, log for operational)** — selected.
3. **Full ARC42 mapping with all 12 sections** — partial adoption (see ADR-0009 if added later); UACP isn't a system architecture in the ARC42 sense, so partial mapping in `docs/arc42-index.md` is more honest than forcing the full template.

## Decision Outcome

Chosen option: **Option 2 with partial ARC42 mapping (option 3)**.

Subdirectories:

- `policy/` — constitution, first-principles, alignment-spec
- `lifecycle/` — lifecycle-reference, orchestration-model
- `runtime/` — runtime-enforcement, runtime-integration-guide, runtime-porting-and-version-control
- `reference/` — proposal-schema, skill-enforcement-spec, lifecycle-trace-table
- `architecture/` — ADRs (numbered, with template + status lifecycle)
- `decisions/` — operational decision-log
- `plans/` — phase5-reserved-slot, future phase plans
- `archived/` — superseded docs kept for traceability

Plus four new root-level docs (`PROJECT.md`, `ROADMAP.md`, `CONTRIBUTING.md`, `COMMANDS.md`) and an ARC42 mapping index (`docs/arc42-index.md`).

### Positive Consequences

- ADRs have stable linkable identity (`ADR-0005` not `decision-log.md#2026-05-15-section-3`).
- Subdirectory INDEX.md pages reduce navigation cognitive load.
- Each subdirectory's content is now scannable as a unit.
- Trustless-acp readers find a familiar pattern.

### Negative Consequences

- Migration touched ~50 files (every cross-reference path).
- Phase verify scripts and adapter handlers refer to docs by path; needed coordinated updates.

## Validation

- All 5 `phaseN_verify` scripts continue to pass after the restructure.
- Every doc moved via `git mv` to preserve history.
- `docs/INDEX.md` updated as the structural navigation map.

## Related ADRs

- Triggered by: [ADR-0007](0007-global-review-cross-phase-remediation.md) (global review surfaced accumulated doctrine drift as a recurring concern).
- Establishes: [ADR-0001](0001-record-architecture-decisions.md).

## References

- Restructure commits: this commit and the ones that follow (multi-commit per operator request).
- Cross-reference scan: `git grep -n "docs/" config/ scripts/ runtime-adapters/ outputs/ executions/ verification/`.
