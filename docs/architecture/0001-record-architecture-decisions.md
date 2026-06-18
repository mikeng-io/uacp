---
type: adr
title: Record architecture decisions
description: Adopt the ADR format for architectural decisions alongside the existing operational decision-log.
tags: [adr, documentation, governance, process]
timestamp: 2026-05-17
status: accepted
---

# Record architecture decisions

## Metadata

- **Status**: accepted
- **Date**: 2026-05-17
- **Decision Makers**: operator
- **Consulted**: Codex council (governance reviewer)
- **Informed**: future maintainers, Phase 5 implementer

## Context and Problem Statement

UACP's `docs/decision-log.md` was a single growing file (26 entries by 2026-05-17). The continuous-log format made decisions easy to add but hard to (a) reference stably from other docs, (b) track lifecycle (proposed → accepted → superseded), (c) link related decisions, and (d) audit at scale. The Phase 4 R0 governance review and the global review both flagged accumulating doctrine drift as a recurring failure mode.

## Decision Drivers

- Decisions need stable identity (link to `ADR-0005` not `decision-log.md#2026-05-15-section-3`).
- Decisions need a lifecycle (accepted → superseded; preserve history).
- Cross-doc references need durable targets that don't drift when adjacent content is edited.
- Sibling project (Trustless ACP) successfully uses the ADR format — adopting the same convention reduces author cognitive load.

## Considered Options

1. **Keep `decision-log.md` as a single file** — minimal change, but doesn't solve stable-identity / lifecycle problems.
2. **Split every decision into a numbered ADR** — strong stable identity but heavy ceremony for minor operational decisions.
3. **Hybrid: ADRs for architectural decisions; `decision-log.md` for operational decisions** — selected.

## Decision Outcome

Chosen option: **Hybrid (option 3)**, because ADRs carry real cost (numbered file, status lifecycle, template) and most operational entries in the old log don't warrant that ceremony. The split lets each format serve its strength: ADRs for architecture, the log for daily decisions.

### Positive Consequences

- Architectural decisions are stably linkable.
- ADR lifecycle (accepted → superseded) is enforced by the template's Status field.
- The operational log keeps its low-ceremony append-only shape.

### Negative Consequences

- Authors must decide which format applies. The `docs/decisions/INDEX.md` "When to log here vs author an ADR" table mitigates.

## Validation

This ADR is itself the first artifact of the new format. Subsequent ADRs (0002–0008) record Phases 0–4 of the UACP patch plan and the global-review cross-phase remediation.

## Related ADRs

- Related: [ADR-0008](0008-doc-structure-and-adr-adoption.md) — the parent restructure that adopted ADRs as part of a wider doc reorganization.

## References

- ADR template: [`0000-template.md`](0000-template.md).
- Operational log: [`../decisions/decision-log.md`](../decisions/decision-log.md).
- Inventory entry: [`../INDEX.md`](../INDEX.md).
