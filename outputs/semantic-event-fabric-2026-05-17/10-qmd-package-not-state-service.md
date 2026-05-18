# Addendum: QMD as Protocol / Package, Not Central State Service

Date: 2026-05-17
Status: clarification addendum

## Correction

QMD should not be assumed to be a central service that owns everyone else's state.

Mike's clarified direction:

```text
Each service owns its own state.
QMD should be considered as a formal solution, package, library, or protocol layer for hybrid retrieval/search.
```

This is different from a monolithic retrieval service.

## Pattern observed

Several systems already implement their own evidence/hybrid search logic:

- MiniMax/Nimax-style systems using Trustless ACP concepts for evidence base.
- Trustless ACP evidence base with manual/custom hybrid search rather than QMD.
- UACP MEMEX/BES.
- Cortex recall/editorial evidence.
- Hermes memory/session search.
- Future SEF graph/events.

The problem is not only duplicated storage. The problem is duplicated **retrieval protocol**, **source contracts**, **ranking semantics**, and **recall packet shape**.

## Revised QMD framing

QMD should first be defined as:

```text
QMD = Query Mediation Design / Query Mediation Protocol
```

Possible deliverables:

1. **Specification**
   - query request schema;
   - source adapter contract;
   - result item schema;
   - score/ranking metadata;
   - recall packet schema;
   - privacy/scope fields.

2. **Library / package**
   - shared query planner;
   - fusion/ranking utilities;
   - source adapter base classes;
   - recall packet builder;
   - test fixtures and conformance tests.

3. **Optional daemon/service**
   - only for deployments that want central routing/caching;
   - must not be required for every service;
   - must not own canonical state by default.

## Ownership invariant

```text
Services own their state.
QMD owns the query/retrieval contract and reusable mediation logic.
Optional QMD service owns only routing/cache/index mirrors when explicitly deployed.
```

## Package-first architecture

```text
qmd-spec
  └── schemas and protocol docs

qmd-core
  ├── query models
  ├── result models
  ├── fusion/ranking
  ├── recall packet assembly
  └── conformance tests

qmd-adapters
  ├── qmd-adapter-uacp-memex
  ├── qmd-adapter-sef
  ├── qmd-adapter-cortex
  ├── qmd-adapter-trustless
  └── qmd-adapter-hermes-memory

qmd-daemon optional
  └── HTTP/gRPC server wrapping qmd-core + configured adapters
```

## Recommendation

Start with a **formal protocol + library/package**, not a mandatory central service.

A daemon can come later as an adapter host, cache, or broker, but the first-class abstraction should be portable and embeddable.
