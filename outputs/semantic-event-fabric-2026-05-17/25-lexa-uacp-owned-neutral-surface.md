# Addendum: LEXA Ownership and Neutral Positioning

Date: 2026-05-17
Status: ownership/positioning refinement

## Clarification

Mike wants LEXA to be **owned by UACP**, while still appearing neutral and generic at first glance.

This is possible if we distinguish:

```text
Stewardship / ownership = UACP
Public abstraction / interface = neutral, generic, source-owned context framework
```

## Recommended framing

LEXA should be presented as a neutral semantic context framework, with UACP as the initial steward and first-class integrating system.

```text
LEXA is UACP-stewarded, not UACP-branded at the surface.
```

## Why this works

UACP ownership provides:

- governance discipline;
- lifecycle rigor;
- MEMEX/BES integration path;
- source-owned state invariants;
- policy/audit expectations;
- durable design stewardship.

Neutral positioning provides:

- reuse across SEF, Cortex, Trustless, Hermes, Nora/Norty, and future services;
- no impression that LEXA only works for UACP lifecycle data;
- cleaner external package/API surface;
- lower coupling to UACP terminology for non-UACP consumers.

## Boundary model

```text
UACP owns/stewards LEXA doctrine and governance.
LEXA exposes neutral API/SDK contracts.
Services retain canonical state ownership.
LEXA derived indexes remain workspace/service/source scoped.
```

## Naming / branding rule

Public-facing name:

```text
LEXA
```

Generic one-line public definition:

```text
LEXA is a universal semantic context framework: an API server and SDK for assembling agenda-shaped context packets across source-owned systems using hybrid retrieval, reranking, and scoped derived indexes.
```

Internal ownership note:

```text
LEXA is UACP-stewarded and designed as the future semantic context layer for MEMEX, while remaining generic enough for SEF, Cortex, Trustless, Hermes, and other services.
```

Avoid public definitions like:

```text
LEXA is the UACP search engine.
LEXA is MEMEX search.
LEXA is UACP-only retrieval.
```

## Repo/docs positioning

If the repo is under `nortrix-labs/lexa`, docs can include:

```text
Stewardship: UACP-governed design lineage
Scope: neutral source-owned semantic context framework
First integrations: UACP MEMEX, SEF, Cortex, Trustless, Hermes
```

Keep root README generic. Put UACP ownership/stewardship details in an `ARCHITECTURE.md`, `GOVERNANCE.md`, or `docs/lineage.md` file.

## Governance implication

Changes that alter LEXA's authority model, MEMEX integration, workspace/source boundaries, privacy model, or canonical state invariant should follow UACP governance discipline.

Ordinary SDK/API implementation changes can use normal repo workflow with tests and reviews.

## Design invariant

```text
Neutral surface, UACP stewardship.
Generic contracts, governed lineage.
Source-owned state, LEXA-owned derived context indexes.
```
