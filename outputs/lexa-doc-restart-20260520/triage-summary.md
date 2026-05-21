---
kind: uacp.triage.summary
run_id: lexa-doc-restart-20260520
phase: TRIAGE
status: pass
created: 2026-05-20
owner: mike
subject: LEXA documentation restart
routing_outcome: standard_uacp
artifact_policy: standard
---

# LEXA Documentation Restart — TRIAGE Summary

## Request

Mike corrected that the LEXA documentation restart is inside the UACP lifecycle, and that no LEXA document should be treated as accepted/canonical before a from-the-beginning review.

## Admission

This work is admitted into UACP because it affects documentation authority, project artifact routing, private/public boundary semantics, and future runtime readiness for LEXA/Nora/Cortex integration.

## Routing outcome

`standard_uacp`.

Rationale:

- The current action is documentation and artifact routing, not runtime mutation.
- The blast radius is moderate because LEXA will later mediate private/public context retrieval.
- The work is reversible at the file level, but semantic mistakes can mislead future agents.
- Full runtime/protected-state UACP is not needed until implementation or boundary wiring begins.

## Phase obligations

Next phase is PROPOSE/PLAN combined as a documentation restart package:

1. treat all current LEXA docs as draft inputs;
2. define restart review order from `00-index.md`;
3. preserve evidence that no doc is accepted/canonical yet;
4. avoid creating runtime/API commitments;
5. produce an operator-facing summary instead of raw inventories.

## Current invariant

Vault remains a draft surface. Canonical acceptance must happen later through a chosen project docs or UACP artifact surface.
