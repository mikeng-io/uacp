# Addendum: Own Semantic Search Package / Library

Date: 2026-05-17
Status: correction addendum

## Correction

QMD is already a standalone GitHub package. The design question is not whether to create QMD as a central service.

Mike's clarified direction:

```text
Create our own package/library for semantic search mediation, similar in spirit to Key/Deeper patterns, while each service continues to own its own state.
```

This package is a shared semantic-search layer/contract, not a state-owning service.

## Revised framing

Use a neutral package/library abstraction for semantic and hybrid retrieval across Nortrix systems.

Possible working names:

- `nortrix-search`
- `semantic-search-kit`
- `hybrid-recall-kit`
- `query-fabric`
- `sef-search`
- `memex-search-kit`

Avoid overloading `QMD` if QMD already refers to an external/standalone GitHub package.

## Ownership invariant

```text
Each service owns its canonical state.
The search package owns reusable query contracts, adapter interfaces, ranking/fusion utilities, and recall packet schemas.
Optional service wrappers may exist, but state ownership remains with the source service.
```

## Package responsibilities

The package should provide:

1. Query schema
   - text query;
   - source scopes;
   - privacy view;
   - filters;
   - desired retrieval modes.

2. Source adapter contract
   - `search(query) -> results`;
   - `get(id) -> source item`;
   - optional graph-neighborhood expansion;
   - optional embedding/full-text hooks.

3. Result item schema
   - source;
   - item id;
   - type;
   - score components;
   - provenance;
   - freshness;
   - authority/privacy metadata.

4. Fusion/ranking utilities
   - BM25 + dense vector + sparse vector + graph prior fusion;
   - RRF / weighted merge / source normalization;
   - reranker hook interface.

5. Recall packet builder
   - provenance-preserving result bundle;
   - source-specific evidence excerpts;
   - inclusion rationale;
   - scope/privacy metadata.

6. Conformance tests
   - adapter contract tests;
   - score normalization tests;
   - privacy/scope propagation tests;
   - recall packet schema validation.

## Relationship to existing systems

```text
UACP MEMEX/BES:
  owns UACP evidence, patterns, recall, scoring;
  can expose an adapter to the package.

SEF:
  owns semantic events, graph references, authority proofs;
  can use the package for semantic resolution candidates.

Cortex:
  owns editorial recall/evidence;
  can expose a source adapter.

Trustless:
  owns evidence base / ACP-derived evidence state;
  can expose a source adapter.

Hermes memory/session search:
  remains Hermes-owned;
  can expose a source adapter if useful.
```

## Design direction

Start with a package/library plus schemas and tests, not a central daemon.

A daemon may be useful later as:

- adapter host;
- local HTTP/gRPC wrapper;
- cache layer;
- cross-service query coordinator.

But the daemon is optional. The package/protocol is the core deliverable.

## Updated phrase

Use this phrase going forward:

```text
Nortrix semantic search package: a reusable hybrid retrieval contract and library for source-owned systems, providing adapter interfaces, fusion/ranking utilities, and recall packet schemas without centralizing canonical state.
```
