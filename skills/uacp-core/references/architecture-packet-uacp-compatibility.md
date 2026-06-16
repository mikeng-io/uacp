# Architecture Packet UACP-Compatibility Pattern

Use this when Mike asks whether existing design/architecture documents need to be revisited so they comply with UACP, especially when the docs are not yet an active UACP run package.

## Core distinction

Do not force full UACP lifecycle machinery onto every draft architecture packet.

Classify the surface first:

- **Vault/private draft architecture packet**: should be UACP-compatible, but does not need `proposals/{run_id}`, `plans/{run_id}`, `executions/{run_id}`, Heartgate, or gate ledger artifacts yet.
- **Canonical project/repo docs surface**: should have explicit authority, status, non-goals, boundaries, and promotion/implementation stop rules before code/runtime work begins.
- **Active UACP run/package**: must follow the full lifecycle artifact contract and validator/Heartgate requirements.

Preferred phrase: **UACP-compatible documentation hygiene** for draft/candidate architecture docs; reserve **UACP-compliant lifecycle package** for real UACP runs.

## Review sequence

1. Identify the current authority surface and remove stale pointers to missing staging paths or obsolete proposal folders.
2. Classify each document by role:
   - conductor/index,
   - stable doctrine candidate,
   - draft implementation blocker,
   - historical review/audit evidence,
   - schema/fixture support.
3. Patch the index/conductor so future agents know what is authoritative, candidate, draft, historical, or non-authoritative.
4. Split promotion decisions from implementation decisions. A document may be ready for canonical docs but not ready for runtime/API implementation.
5. Add explicit stop rules for protected work: no daemon/API/runtime integration, public/private boundary change, memory indexing, LCP/Nora behavior change, Cortex dependency, or UACP mutation from draft docs alone.
6. Recommend the lightest correct promotion path:
   - keep in draft if still conceptual,
   - create/promote to canonical project docs if authority is the main problem,
   - open a UACP-governed proposal only when protected runtime, governance, public/private, memory, or agent-control surfaces change.

## Document cleanup targets

For each doc, make these fields or equivalents recoverable from the text/frontmatter:

- status: draft / candidate / accepted / historical / superseded,
- owner or decision authority,
- scope and boundary,
- relation to UACP,
- relation to adjacent systems,
- unresolved decisions,
- promotion readiness,
- implementation stop conditions.

## Operator-facing report

Report conclusion first, not a raw file inventory:

- whether full UACP lifecycle is required now,
- which docs need targeted revision,
- which docs should remain historical/draft,
- what must be true before promotion or implementation,
- recommended next action.

Raw document lists are acceptable only as compact grouped evidence, not as the main answer.

## LEXA example distilled

When reviewing LEXA architecture docs, the correct move was not immediate runtime work and not a full UACP run. The correct move was to classify the Vault packet as a draft architecture surface, correct stale authority pointers, add a routing/promotion plan, and recommend targeted revision into UACP-compatible candidate docs before choosing a canonical repo/docs surface or opening a UACP proposal.
