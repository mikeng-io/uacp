---
type: analysis
title: Serialize Targets — canonicalize to durable state, many destinations
description: Serialize is not "save to a database" — it is canonicalize a decision into stable durable state, and the target is policy-routed. Memory is just ONE target; this is the reframe of UACP as an information-processing pipeline whose outputs are many.
tags: [primitive, serialize, canonicalize, targets, information-processing]
timestamp: 2026-06-21
edges:
  - {dst: 00-the-axiom, rel: depends_on, provenance: derived}
---

# Serialize Targets

**`serialize` = canonicalize a decision into stable, durable state.** Not "write to a DB" — the *form* and the *destination* are policy-routed.

## The targets are plural

```
                    decision
                       │
   ┌───────────┬───────┼────────┬───────────┐
   ▼           ▼       ▼        ▼           ▼
workspace   user/    event    knowledge   audit
 memory    project    log      graph       trail
              memory
   ▼           ▼       ▼        ▼           ▼
 vector      SQL    git-commit  SCIP      metrics / search-index / API-response / DROP
```

Embedding, SQL, JSON, SCIP, Markdown, a git commit, an API response — **all are serialize**. So is "drop" ([02](02-decision-hinge.md)).

## The reframe this forces

If the *same* comprehended-and-measured context can serialize to *any* of these, then **UACP is not a Memory framework** — it is an **information-processing pipeline**, and Memory / KG / Event-log / Audit are **serialization targets**, not UACP itself. ([06-instantiations](06-instantiations.md) develops the reframe.)

## The discipline that keeps it trustless

A target without provenance is a leak. Every serialized state carries **what it derived from** (the `derived_from` / provenance edge) — so any durable state traces back to the comprehension + measurement that produced it. That is what separates *canonicalize* from *dump*. ([04-trustless-differentia](04-trustless-differentia.md).)

## To expand
- The target catalog as a typed registry (target → form → durability → provenance requirement).
- Idempotent canonicalization (`fmt(fmt(x)) == fmt(x)`) per target — the graph-engine `uacp-fmt` is one instance.
- Which targets are *records* (git-truth) vs *rebuildable indexes* (vector/search) — the files-are-truth line.
