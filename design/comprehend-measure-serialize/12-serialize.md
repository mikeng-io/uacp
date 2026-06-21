---
type: analysis
title: Serialize — canonicalize a decision into durable state (many targets)
description: The third verb. Not "save" — canonicalize a decision into stable, durable state, as a typed key with provenance; the target is policy-routed and plural (memory/KG/event/vector/audit/search/API/git/drop). This breadth is why UACP is an information-processing architecture, not a memory system.
tags: [primitive, serialize, canonicalize, targets, information-processing]
timestamp: 2026-06-21
edges:
  - {dst: 00-the-axiom, rel: depends_on, provenance: derived}
---

# Serialize

**Question:** *what should persist?* **Output:** **durable, canonical state.**

## Not "save" — canonicalize

Serialize fixes a decision into a **stable, durable form** — a typed key in a *single* canonical shape (so diffs are minimal, writes reproducible, the projection sees no spurious churn). "Save to a DB" is one instance; the verb is broader.

## The targets are plural (policy-routed)

```
                    decision (routed by 21-decision-hinge)
                       │
   ┌───────────┬───────┼────────┬───────────┐
   ▼           ▼       ▼        ▼           ▼
workspace   user/    event    knowledge   audit
 memory    project    log      graph       trail
   ▼           ▼       ▼        ▼           ▼
 vector      SQL    git-commit  SCIP   metrics / search-index / API-response / DROP
```

Embedding, SQL, JSON, SCIP, Markdown, a git commit, an API response — **all are serialize**. So is "drop" ([21-decision-hinge](21-decision-hinge.md)).

## The reframe this forces

If the *same* comprehended-and-measured context can serialize to *any* of these, then **UACP is not a Memory framework — it is an information-processing architecture**, and Memory / KG / event-log / audit are **serialization targets**, not UACP itself. ([31-instantiations](31-instantiations.md) develops it.)

## Discipline: provenance separates canonicalize from dump

Every serialized state carries **what it derived from** (a `derived_from` / provenance edge), so any durable state traces back to the comprehension + measurement that produced it. A target without provenance is a leak. ([22-trustless-differentia](22-trustless-differentia.md).)

## To expand
- The target catalog as a typed registry (target → form → durability → provenance requirement).
- Idempotent canonicalization (`fmt(fmt(x)) == fmt(x)`) per target — the graph-engine `uacp-fmt` is one instance.
- Records (git-truth) vs rebuildable indexes (vector/search) — the files-are-truth line.
