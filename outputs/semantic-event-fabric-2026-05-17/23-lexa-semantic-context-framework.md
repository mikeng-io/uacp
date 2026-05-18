# Addendum: LEXA as Multi-Type Semantic Context Framework

Date: 2026-05-17
Status: terminology refinement

## Clarification

LEXA is better framed as a **multi-type semantic context framework** or **context retrieval suite**, not just search engine, semantic search engine, CodeGraph clone, or Graphiti clone.

It standardizes retrieval and recall across multiple context types while respecting source-owned canonical state.

## Why this framing fits

LEXA must handle multiple kinds of context:

- document context;
- evidence context;
- event context;
- graph/entity context;
- code context;
- workflow/state context;
- conversation/session context;
- policy/authority context;
- BES/pattern context.

Search is only one operation. The output is not just ranked documents; it is a provenance-preserving context/recall packet suitable for agents, governance flows, and semantic event/entity resolution.

## Layered positioning

```text
LEXA = multi-type semantic context retrieval framework
SEF  = semantic event/entity/authority fabric
SGRN = graph registry / authority graph
MEMEX = UACP governed memory/evidence module
BES = source-owned scoring/effectiveness feature
```

## What LEXA is

```text
LEXA is a source-owned semantic context API server + SDK that indexes, retrieves, fuses, reranks, weights, and packages multiple context types across services/workspaces.
```

It includes:

- hybrid lexical + semantic retrieval;
- source adapters;
- graph/source adapters;
- code/source adapters;
- event/source adapters;
- reranking;
- query expansion;
- BES/authority/recency ranking features;
- workspace/service/source isolation;
- durable derived indexes;
- recall/context packet assembly;
- SDK + API server.

## What LEXA is not

- Not a central canonical state database.
- Not only semantic search.
- Not only RAG.
- Not only CodeGraph.
- Not only Graphiti.
- Not an agent SDK like Strands.
- Not UACP MEMEX itself.
- Not SEF authority logic.

## Context type examples

### Document context

Markdown docs, ADRs, specs, proposals, notes.

### Evidence context

UACP/Trustless evidence records, validation outputs, audit findings.

### Event context

SEF events, dispatch receipts, workflow events, chronology.

### Graph/entity context

SGRN entities, aliases, relationships, authority path evidence, graph neighborhoods.

### Code context

CodeGraph-derived symbols, call graphs, dependency graph, code chunks, architectural references.

### Workflow/state context

Temporal/Cortex/UACP workflow state, phase records, proposal state, checkpoints.

### Conversation context

Hermes sessions, public/private conversation snippets, scoped memory stores.

### Pattern/BES context

Pattern registry entries, recurrence, effectiveness scores, source-owned BES ranking features.

## Better class name

Use this phrase in design docs:

```text
LEXA is a semantic context framework.
```

If precision is needed:

```text
LEXA is a multi-source, multi-type semantic context retrieval framework with API server + SDK.
```

## SRE/product positioning

LEXA is closer to a context/retrieval control plane than a search database.

It should expose SRE-grade operations:

- source health;
- index freshness;
- rebuild status;
- query audit;
- backend status;
- workspace isolation checks;
- adapter conformance tests;
- backup/restore for expensive derived indexes.

## Canonical phrase

```text
LEXA is a source-owned multi-type semantic context framework: an API server and SDK for hybrid retrieval, fusion, reranking, optional BES weighting, and context packet assembly across documents, evidence, events, graphs, code, workflows, and conversations, without centralizing canonical state.
```
