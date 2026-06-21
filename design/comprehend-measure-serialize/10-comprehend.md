---
type: analysis
title: Comprehend — unstructured input → a computable context
description: The first verb. Not "understand text" — build a COMPUTABLE context model (entities, relations, timeline, intent, constraints, current state) from unstructured input. The only semantic touch; bounded and recorded.
tags: [primitive, comprehend, context-model]
timestamp: 2026-06-21
edges:
  - {dst: 00-the-axiom, rel: depends_on, provenance: derived}
---

# Comprehend

**Question:** *what is this?* **Output:** a **computable context model.**

Comprehend is *not* "read the prose." It is the conversion **unstructured → structured**: a Slack message / PR / log / CI run / prompt becomes a model an operation can compute over —

```
input  →  Workspace
            ├── Entities
            ├── Relations
            ├── Timeline
            ├── Intent
            ├── Constraints
            └── Current State
```

## Who does it

Not only an LLM. Comprehend is *multi-source*: LLM (intent/meaning) + parser/AST/SCIP (structure) + the existing graph (prior state) co-produce the model. The LLM is one contributor, not the whole step.

## Discipline

It is the **only semantic touch** in the cycle, so it must be **bounded** (one act of understanding, not pervasive interpretation) and **recorded** (the produced model is an artifact, auditable) — so everything downstream (`measure`, `serialize`) operates on a *fixed* model, not a re-interpreted one. This is what keeps the semantic step from leaking into the deterministic ones.

## To expand
- The context-model schema (what fields are mandatory vs optional per operation).
- How comprehend reuses an existing graph (incremental, not from-scratch each time).
- The boundary with `measure`: comprehend builds the model; it does not yet judge it.
