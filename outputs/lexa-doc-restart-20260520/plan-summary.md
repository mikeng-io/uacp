---
kind: uacp.plan.summary
run_id: lexa-doc-restart-20260520
phase: PLAN
status: pass
created: 2026-05-20
owner: mike
subject: LEXA documentation restart
---

# LEXA Documentation Restart — PROPOSE/PLAN Summary

## Intent

Restart the LEXA documentation set from the beginning under UACP lifecycle discipline. No existing LEXA document is to be treated as accepted, canonical, locked, or implementation-ready.

## Scope

In scope:

- demote all LEXA Vault packet documents to draft input;
- add an explicit draft restart guard to every LEXA document;
- preserve the current Vault packet as evidence/input, not canonical truth;
- prepare a clean review order starting from `00-index.md`;
- avoid runtime/API implementation commitments.

Out of scope:

- creating a LEXA daemon/API;
- wiring Nora/Cortex to LEXA;
- accepting source registry, query contract, or event graph schema;
- mutating UACP protected runtime/state beyond this documentation artifact record.

## Review order

1. Conductor and status model.
2. Layer model.
3. Authority/privacy/system boundaries.
4. SEF/SGRN integration assumption.
5. Workspace/peer/source/scope model.
6. Source registry contract.
7. Query/event/schema drafts.
8. Runtime boundary sketch.
9. Examples and historical council notes.

## Phase intent verification contract

VERIFY should check:

- all LEXA docs involved in this restart have `status: draft`;
- all have an explicit draft restart guard;
- no document claims accepted/canonical/locked/implementation-ready status except as negated warning text;
- links remain resolvable;
- operator-facing output is summary-first.
