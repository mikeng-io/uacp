---
type: analysis
title: Graph Engine — Overview
description: The problem (relations-as-serialization-failure), the thesis (one serialize/deserialize graph engine), the semantic->structural gradient, and v1 scope (lookup not synthesis).
tags: [graph-engine, serialization, overview]
timestamp: 2026-06-19
edges:
  - {dst: 01-context-intent, rel: motivated_by, provenance: asserted}
---

# Manifest Graph Engine — Overview

## The problem in one sentence

UACP's cross-phase manifest relations (PROPOSE → PLAN → EXECUTE → VERIFY → RESOLVE) are
*partly* established **semantically** — an agent re-reads prose and re-interprets the linkage
each phase — and that is the source of phantom tasks, dropped intents, and "verified something
that does not exist / was skipped."

The deeper framing: this is a **serialization failure**. People serialize *content* (Markdown)
and drop the *edge*, then rent the edge back at query time with RAG / keyword / embedding search.

> **A relation that is not serialized as a typed key at write-time is a relation you have
> agreed to reconstruct semantically later.** RAG is the interest you pay on lossy serialization.

## The thesis

Build a **serialize/deserialize unified graph engine**:

1. **Serialize** every relation, at the moment it is born, as a typed edge record
   `{src, dst, rel_type, provenance}` — in the producing artifact's frontmatter, never as prose.
2. **Deserialize** all artifacts into one queryable graph spanning the planes — governance/relation,
   knowledge, and (later) code/reality.

The "engine" is not a new database. It is a deterministic **projection / read-model** over the
governed artifacts UACP already writes. Once edges are serialized uniformly, the engine collapses
to a *loader* — the cleverness is in the serialization discipline, not the query layer.

## Two planes, one wiki

A proposal, a spec, a manifest **is** knowledge — information about intent and rationale. From
UACP's perspective there is no reason it lives in a different store than a lesson. The
"relation plane" and the "knowledge plane" are the **same OKF wiki**; they differ only by edge
`provenance`. A manifest node is a wiki page that *additionally* carries hard edges in its
frontmatter. (See [01-context-intent](01-context-intent.md) for the reframe; [02-decisions](02-decisions.md) D1 for why this does **not** mean adopting OKF's link-based relation model.)

## The semantic → structural gradient

The phases are not uniform nodes. They sit on a gradient: a node's value starts in its **body**
(semantic intent) and migrates into its **frontmatter** (structural edges) as work descends, then
returns to body as knowledge.

| Phase | Node kind | Value lives in | semantic : structural |
|---|---|---|---|
| PROPOSE | scope_item | body (intent) | ~90 : 10 |
| PLAN | work_unit | both (the pivot) | ~50 : 50 |
| EXECUTE | checkpoint | frontmatter (edges) | ~20 : 80 |
| VERIFY | assessment | frontmatter | ~10 : 90 |
| RESOLVE | lesson | body (knowledge) | ~80 : 20 |

The only **semantic judgment edge** in the whole chain is the single PROPOSE → PLAN hop
(`derives_from`, provenance `asserted`). Everything else is `derived` or `parsed` — provable.

## v1 scope (a hard guard)

- **Lookup, not synthesis.** v1 deserializes and traverses; it does not generate explanations or
  decompositions. Lookup is replay of serialized keys — it cannot lie. Synthesis is where semantics
  re-enter; it is out of scope for v1.
- **Governance + knowledge planes.** The **code/reality** plane (`code_anchor`, a symbol indexer)
  is deferred to Slice 3 (see [20-slices-readiness](20-slices-readiness.md)).
- **Semantic search is demoted to entry-point resolution only** — resolve a fuzzy concept
  ("login") to a node id, then traverse deterministically (forward and reverse).
