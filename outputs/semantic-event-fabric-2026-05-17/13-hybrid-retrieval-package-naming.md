# Addendum: Naming Candidates for Hybrid Retrieval Package

Date: 2026-05-17
Status: naming exploration

## Naming criteria

The package should not sound like plain semantic search. It must cover:

- semantic/vector retrieval;
- keyword/full-text retrieval;
- query expansion;
- reranking;
- fusion/score normalization;
- optional source-owned BES weighting;
- recall packet assembly;
- source-owned state invariant.

It should also avoid overloading `QMD`, since QMD already refers to an external standalone package.

## Strong candidates

### 1. Recall Fabric

Best conceptual fit if the package is about building recall packets across source-owned systems.

Pros:
- broader than search;
- fits MEMEX/UACP language;
- captures retrieval + fusion + packet assembly;
- service-neutral.

Cons:
- may sound like a substrate/service rather than a library unless named `recall-fabric-kit` or `recall-fabric-core`.

### 2. Query Loom

Good metaphor for weaving multiple retrieval strands into one recall packet.

Pros:
- memorable;
- captures fusion;
- neutral and not over-branded.

Cons:
- less explicit for technical users.

### 3. Hybrid Recall Kit

Most literal and clear.

Pros:
- obvious scope;
- package/library-friendly;
- avoids semantic-only framing.

Cons:
- less distinctive as a proper name.

### 4. Retrieval Fabric

Broad technical umbrella.

Pros:
- generic;
- covers hybrid retrieval across sources.

Cons:
- may overlap with SEF “Fabric” naming and feel too infrastructure-like.

### 5. Memex Query Kit

Good if the package is primarily designed for UACP MEMEX-style recall.

Pros:
- close to current UACP terminology;
- communicates retrieval over memory/evidence.

Cons:
- risks implying MEMEX ownership or UACP-only scope; not ideal if generic/neutral.

### 6. Nortrix Recall Kit

Good branded package name.

Pros:
- broad enough for UACP, SEF, Cortex, Trustless;
- clearly owned by Nortrix ecosystem.

Cons:
- less neutral/generic if the package should be reusable outside Nortrix.

## Current recommendation

Use a two-level name:

```text
Concept name: Recall Fabric
Package name: recall-fabric
```

If a more explicit package name is needed:

```text
Concept name: Recall Fabric
Package name: hybrid-recall-kit
```

## One-line definition

```text
Recall Fabric is a source-owned hybrid retrieval library/protocol that combines semantic search, keyword search, query expansion, reranking, optional BES weighting, and recall packet assembly without centralizing canonical state.
```

## Integration phrase

```text
SEF uses Recall Fabric for candidate retrieval.
UACP MEMEX can expose a Recall Fabric source adapter.
Trustless/Cortex/Hermes can expose source adapters.
Each source owns its state.
Recall Fabric owns query/fusion/packet contracts.
```
