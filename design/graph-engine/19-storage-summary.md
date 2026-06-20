---
type: analysis
title: Graph Engine — Storage Engine (the short version)
description: "SUPERSEDED by D29/D32 — body describes the abandoned single-SQLite model. CURRENT: structure = plain YAML files (truth) + in-memory projection (NO database); semantics = LanceDB only. Build per D29."
tags: [graph-engine, storage, summary]
timestamp: 2026-06-19
edges:
  - {dst: 14-projection-engine, rel: depends_on, provenance: derived}
---

# Storage Engine — the short version

> ⚠️ **SUPERSEDED by D29/D32 (final-review T1).** This node was written for the abandoned **single-SQLite**
> model. **CURRENT — build per this:** structure = **plain YAML files (truth) + an in-memory projection,
> NO database**; semantics = **LanceDB** (knowledge/lessons only); no `sqlite-vec`, no Index port in v1
> (SQLite is a *deferred* scale-cache, never a source). Everything below mentioning "one SQLite / sqlite-vec"
> is **historical**. See [02-decisions](02-decisions.md) D29/D32.

Two things. Files, and one index database. That's it.

```
        WRITE (only through the engine, validated)
                       │
   ┌───────────────────▼───────────────────┐
   │  TRUTH  —  files (YAML / OKF)           │   one file per entity, git-tracked
   │     nodes + edges stored as keys        │   ← the ONLY source of truth
   └───────────────────┬───────────────────┘
                       │  project (rebuildable; .gitignore'd; delete & rebuild anytime)
   ┌───────────────────▼───────────────────┐
   │  INDEX  —  ONE SQLite database          │   accessed via the Index engine (D14)
   │   • exact edges   → recursive CTE       │   "what connects to what" (provable)
   │   • vectors       → sqlite-vec          │   "what is this about" (fuzzy)
   │   • keyword       → FTS5                │   exact + fuzzy in ONE file, ACID
   └────────────────────────────────────────┘
```

## What lives where

| Layer | Plain question | Where | Holds |
|---|---|---|---|
| **Truth** | "what's actually committed" | YAML/OKF **files** (git) | every node + edge, as keys |
| **Index** | "what connects to what" + "what's this about" | **one SQLite** (CTE + sqlite-vec + FTS5) | edges, vectors, full-text |

## Rules of thumb

1. **Files are truth; the DB is a throwaway index.** Rebuilt from files; `.gitignore`d; never edited
   directly; git diffs/reviews the *files*. The DB holds nothing authoritative. (A DB-as-truth design
   *would* kill git — rejected: D2/D11.)
2. **Exact → recursive CTE, fuzzy → sqlite-vec/FTS5 — same database.** Fuzzy finds the door; the walk
   is exact. The Index engine (D14) hides which one served a result.
3. **Nothing is written raw** — every write goes through the engine, validated by `uacp-schema` first.
4. **One DB ⇒ atomicity is free.** One file, one ACID transaction; no cross-store sync (D16).

## Inputs

- **`uacp-schema`** — validates every file on write (closed-world, enums). Nothing malformed lands.
- **SCIP** — extracts precise code links (`defines`/`references`/`calls`) into the SQLite edges.

## Why one DB (and not several)

SQLite+sqlite-vec is the only **mature in-process** engine doing **both** graph (CTE) **and** vector+FTS.
`zvec` does vectors+FTS but **no graph**; DuckDB's vector ext is experimental; SurrealDB/Kùzu/Cozo are
abandoned/immature (see [17-codeplane-substrate-bakeoff](17-codeplane-substrate-bakeoff.md)). So one
SQLite holds it all. **LanceDB** is retired pending an Oracle recall bake-off (`sqlite-vec`+Qwen3 vs
LanceDB+Qwen3); it remains only as a fallback if that fails. A dedicated vector engine (`zvec`) is added
as a 2nd store **only** if the Oracle corpus outgrows brute-force speed — and the Index port makes that a
localized swap (D14/D16).

> One sentence: **write to validated files; project them into one SQLite (edges + vectors + full-text);
> answer exact questions by walking it and fuzzy questions by searching it — and never sync anything,
> just rebuild the one DB from the files.**
