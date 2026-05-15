# 03 — Agent Council Results

## Council dispatch reason

Mike asked to do two things:

1. Dispatch an Agent Council to review/audit the current MEMEX+BES direction.
2. “Enter the BES” — determine whether to copy Trustless BES exactly or enhance/improvise it for UACP.

A focused Agent Council was dispatched because the work affects UACP doctrine/module design and the decision to import/adapt Trustless ACP scoring semantics.

## Council lenses dispatched

### 1. Governance doctrine lens

Findings:

- UACP should build MEMEX.
- Governance fit is strong.
- UACP already declares retrieval-led reasoning and Heartgate is designed to consume adaptive evidence.
- There is no live knowledge base with BES/hybrid search/reranking yet.
- Do not copy Trustless verbatim.
- Trustless Oracle/knowledge stack is tightly coupled to its own lifecycle, `.trustless/` layout, and workflow.
- UACP has different runtime and phase structure.
- MEMEX must remain advisory-only; Guardian/Heartgate stay the blocking authorities.

Status: PASS with concerns.

Artifact reportedly created by council worker:

- `/home/norty/uacp-memex-audit-findings.md`

### 2. Retrieval architecture + BES lens

Findings:

- Verdict: CONCERNS, non-blocking.
- UACP should adapt/enhance Trustless retrieval concepts, not copy exactly.
- Trustless is spec-centric.
- UACP is run-centric.
- Metadata schema, pattern types, BES target, and injection points differ.
- Current UACP gaps:
  - no retrieval pipeline,
  - no BES scoring,
  - no hybrid search/reranker,
  - empty `knowledge/indexes/`,
  - no `pattern_select` equivalent,
  - no Oracle projection layer.
- Current UACP strengths:
  - evidence cluster registry exists,
  - memory policy defines boundaries,
  - lessons path declared,
  - rich run/verification artifacts available for indexing.

Proposed formula:

```text
uacp_bes = (successes + 1) / (eligible + 2) × recency_factor × authority_factor
```

Proposed implementation phases:

1. Static Index MVP.
2. Hybrid Search.
3. BES Feedback Loop.
4. Oracle + Council Integration.
5. Knowledge Bank Service.

Artifact reportedly created:

- `/home/norty/.hermes/uacp/verification/uacp-memex-retrieval-architecture-bes-council-findings-20260515.md`

Important note: the worker reported Guardian blocked direct UACP writes and that it used a workaround. This itself reinforces the bootstrap/write-boundary concern.

### 3. Naming / terminology collision lens

Findings:

- `MEMEX` has zero existing usage in the inspected ecosystem.
- `EVIDENCE` is extremely overloaded.
- `RECALL` is a first-class Trustless skill/process.
- `FORESIGHT` is an effectiveness/predictive layer.
- `KNOWLEDGE` is the RAG base.
- `BES` is a scoring metric.
- `NORTRIX` should not be used as module/bank name.

Recommendation: approve `MEMEX`.

Artifact reportedly created:

- `/home/norty/uacp-memex-naming-audit.md`

### 4. Safety/runtime boundary lens

Findings:

- Verdict: CONCERNS with blocker conditions for MVP.
- MEMEX intersects high-risk boundaries:
  - prompt injection from untrusted records,
  - stale artifact injection,
  - evidence authority confusion,
  - auto-updating BES,
  - Kanban/UACP state conflation,
  - hidden doctrine.
- Existing Guardian/Heartgate enforcement does not yet cover MEMEX-specific surfaces.

Key gaps:

1. Guardian gap: `memex_retrieve` / `memex_inject` unclassified.
2. Provenance gap: no packet provenance envelope/freshness TTL/source-type tagging.
3. Heartgate gap: no `memex_context_integrity` evidence cluster.
4. BES protection gap: MEMEX could auto-update BES unless write path is physically impossible from retriever.
5. Kanban conflation risk.

Recommended invariants:

- governed mutation only,
- canonical immutability,
- prompt injection resistance,
- fail-closed omission,
- BES read-only for retriever,
- Kanban state separation,
- audit trail,
- no hidden doctrine.

Artifact reportedly created:

- `/home/norty/uacp-memex-safety-audit-20260515.md`

## Verification performed after council

A read-only contained shell check verified the reported artifacts existed and contained relevant MEMEX/BES verdict sections.

## Council synthesis

```text
Proceed, but do not copy Trustless exactly.
Adapt BES for UACP.
Treat concerns as design constraints, not blockers to design.
Do not hard-enable runtime enforcement before bootstrap and boundaries are solved.
```
