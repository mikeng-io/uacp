---
type: reference
title: Graph Engine — Glossary, Terminology & Topology (canonical)
description: The single authoritative naming for planes, engines, gates, stores, modules, and core data-model terms — plus the topology and a deprecated-terms map — to prevent cognition drift. Reflects D1–D29.
tags: [graph-engine, glossary, terminology, topology, reference]
timestamp: 2026-06-20
edges: []
---

# Glossary, Terminology & Topology (canonical)

> **Anti-drift rules.** One name per concept. **Planes = WHAT** (kinds of data). **Engines = WHO**
> (components that act). **Gates = enforcement** (governance checkpoints). **Stores = WHERE** (truth vs
> derived indexes). If a term isn't here, it isn't canonical. Old/confusing names are mapped at the bottom.

> **SCOPE (2026-06-22) — this node is partly SUPERSEDED.** It holds *design-era* vocabulary (D1–D29).
> Authoritative references now:
> - **Component / engine names → [28-component-registry](28-component-registry.md)** — this node's
>   "Engines — WHO" + "Topology" sections invented "manifest engine" / "indexer engine" that **do not
>   exist as code**; node 28 is the grounded truth (e.g. *manifest engine ≡ state engine ≡ `uacp-state`*).
> - **Artifact KINDS → [26-nomenclature](26-nomenclature.md)** (this node's "node kinds" list is the *spike* form).
> - **Directory & file layout → [27-directory-taxonomy](27-directory-taxonomy.md)**.
>
> 18-glossary remains useful only for the **abstract vocabulary** (planes-as-data-categories, stores,
> OKF, DDD/CQRS terms) — NOT for component names.

## Topology (the whole system on one screen)

```
                  ┌───────────────────────────────────────────────────────────┐
  agent ─CRUD──►  │  MANIFEST ENGINE  (write-model)                            │
                  │   create / edit / delete / supersede                       │
                  │   → uacp-fmt → uacp-lint(uacp-schema) → Guardian → WRITE   │
                  └──────────────────────────┬────────────────────────────────┘
                                             │ writes
                  ┌──────────────────────────▼────────────────────────────────┐
                  │  FILES = TRUTH   (per-node OKF, git-versioned)             │  ← relation plane
                  │   each node owns its fields + outbound `edges:` key        │     (structural; NO vectors)
                  └──────────────────────────┬────────────────────────────────┘
                       projects (read)       │            embeds (knowledge/lessons ONLY)
                  ┌──────────────────────────▼─────────┐   ┌────────────────────────────┐
                  │  INDEXER ENGINE  (read-model)       │   │  ORACLE  (semantic index)   │
                  │   v1 = in-memory projector          │   │   LanceDB (BGE-M3+Qwen3)    │  ← knowledge plane
                  │   resolve / search / walk / closure │   │   semantic search           │     (semantic; vectors)
                  │   QUERY-ONLY (no write authority)   │   └────────────────────────────┘
                  └──────────────────────────┬─────────┘
                     closure queries (re-verified vs truth)
                  ┌──────────────────────────▼─────────┐
                  │  GATES                              │
                  │   Guardian  = write-time            │
                  │   Heartgate = phase-transition      │
                  │   Council   = semantic judgment     │
                  └─────────────────────────────────────┘
```

*Deferred (NOT in v1): the **code plane** (SCIP graph + code semantic search); the **Index port** + a
SQLite cache; the constraints/metrics plane.*

## Planes — WHAT (kinds of data)

- **relation plane** — the manifest's **structural** data: nodes + typed edges (FKs). **No vectors.**
  Truth = per-node OKF files; queried by the Indexer engine via in-memory graph walk.
- **knowledge plane** — **knowledge + lessons** (the Oracle corpus): **semantic** content, embedded as
  vectors; served by the semantic index (LanceDB).
- **code plane** *(deferred)* — code symbols + structural edges (SCIP) + code text (semantic).
- *Rule:* the **manifest is never embedded** — semantic entry comes from the knowledge/code plane, then
  crosses into the manifest's structural graph and traverses exactly.

## Engines — WHO (components that act)

- **Manifest engine** — the **write-model**: owns the manifest documents as files (truth, git); all
  filesystem read/write + CRUD; hosts the entity-level governed writer + validate-on-write. *(Don't call
  it "state engine" — that name belongs to `uacp-state` lifecycle.)*
- **Indexer engine** — the **read-model**: builds the queryable projection from the files and serves
  queries (`resolve` / `search` / `walk` / closure). **v1 = an in-memory projector** (glob OKF → dicts) —
  **not a database**. **Query-only**: no write or governance authority (CQRS, D22).
- **Oracle** *(pre-existing)* — the knowledge-plane semantic engine over LanceDB (embed + retrieve + Qwen3
  rerank).

## Gates — enforcement (NOT engines)

- **Guardian** — **write-time** gate: node well-formedness (via uacp-lint/uacp-schema) + path containment +
  policy; blocks raw writes to manifest paths. *(Today checks tool/path/context only; content validation
  is net-new — D25.)*
- **Heartgate** — **phase-transition** gate: runs the **closure checks** (querying the Indexer) and
  re-verifies against truth (watermark; STALE = BLOCK — D24).
- **Council** — **semantic judgment** gate: the one place that reviews *correctness* (the PROPOSE→PLAN
  `asserted` seam + any change to an `asserted` edge). Structural closure is necessary, not sufficient.

## Stores — WHERE (truth vs derived)

- **Files (OKF)** — the **source of truth** for structure (manifest) and knowledge content. Git-versioned.
  Each node owns its fields + outbound edges; the aggregate (`_index.yaml`) owns its intrinsic fields and
  *derives* its members/edges mirror (D21/D28).
- **In-memory graph** — the **derived** structural index (v1). Ephemeral; rebuilt per process. Trustless
  (recomputed from truth on every read).
- **LanceDB** — the **semantic/vector index** for the knowledge plane (+ code semantic later). Derived.
- **SQLite** *(deferred)* — a scale-triggered **cache** for structure, never a source; gates still verify
  vs truth. **`sqlite-vec` is NOT adopted** (D29).

## Modules / tools

- **uacp-schema** — the **pure-leaf rules module**: the **OKF profile** + per-kind JSON-Schemas + enums +
  `validate()`. The single source of structural truth; everything imports it, it imports nothing.
- **uacp-lint / uacp-fmt** — validator (reject invalid) + formatter (canonical form). In v1 they live in
  the leaf module; packaging them as a standalone skill is **deferred** (D27).
- **SCIP** *(deferred)* — symbol/reference-precise code-intelligence **indexer** for the code plane.
- **Index port** *(deferred)* — the swappable-backend interface the Indexer engine *would* expose if/when
  multiple stores exist (D14). v1 has no port — just the in-memory projector.

## Core data-model terms

- **node** — one entity = one OKF file (frontmatter + body). Kinds: `scope_item`, `work_unit`,
  `evidence_obligation`, `checkpoint`, `assessment`, `lesson`; *(deferred)* `prohibition`,
  `method_constraint`, `metric`, `code_symbol`.
- **edge** — a typed link serialized as a key in the **source node's** frontmatter
  (`edges: [{dst, rel_type, provenance}]`; `src` = the owning node). **Truth is distributed across node
  files**; `_index.yaml`/indexes only mirror it.
- **provenance** — how an edge is known: `derived` (FK in a governed file), `parsed` (SCIP/git),
  `asserted` (human/LLM judgment — council-gated), `inferred` (embedding/aboutness — advisory). Enforced
  **per `rel_type`** by uacp-schema (D23). Closure proves *topology*, not *semantic correctness* (D23).
- **aggregate** — a directory + its `_index.yaml`; **itself a node** (canonical for its intrinsic fields;
  derives its members/edges mirror). The **write/transaction** boundary.
- **run** — a complete lifecycle instance; the **closure/consistency** boundary (closure spans phases).
- **status** — node lifecycle: `active` → `superseded` | `deleted`.
- **tombstone** — a `status: deleted` node kept for audit, **visible to closure** (D26).
- **supersede** — replace a node with a successor via `supersedes` / `superseded_by` edges; old node
  retained. Append over destroy.
- **OKF profile** — UACP's documented extension of OKF (typed-provenance `edges:` frontmatter +
  aggregate-as-node + canonical/derived field marking), encoded by uacp-schema (D28).
- **closure checks** — deterministic cross-node integrity checks (Indexer/Heartgate): `orphan`, `phantom`,
  `uncovered`, `unverified`, `skipped-but-claimed`, `index-consistency`, `provenance-per-rel-type`,
  `forged-parsed`, `contradicted`, `stale-reference`, `deleted-with-open-obligation`, `duplicate-id`.
- **watermark** — a commit/content hash stamped on a derived index; a gate rebuilds-or-BLOCKs on mismatch.

## Background terms (short)

- **OKF** — Open Knowledge Format: markdown + YAML frontmatter, one file per concept, per-dir aggregate.
  The container.
- **SCIP** — Sourcegraph Code Intelligence Protocol: precise symbol/reference code index.
- **CTE** — SQL `WITH RECURSIVE`; walks a graph in a relational DB (relevant only if SQLite is ever added).
- **HNSW** — approximate-nearest-neighbor vector index algorithm.
- **Qwen3 reranker** — post-retrieval relevance re-sort; **store-agnostic**.
- **DDD / CA / CQRS** — Domain-Driven Design (entity identity, aggregates) / Clean Architecture
  (domain ⊥ storage) / Command-Query Responsibility Segregation (write-model ⊥ read-model).

## Deprecated / do-not-use (drift guard)

| Deprecated / confusing | Use instead | Why |
|---|---|---|
| "Index engine over SQLite" / "the SQLite index" | **Indexer engine** (in-memory, v1) | SQLite is a deferred cache (D29), not the v1 store |
| "single DB" / "one SQLite for everything" | **files + in-memory; LanceDB for semantics** | D16 superseded by D29 |
| "`sqlite-vec`" | **LanceDB** | not adopted (D29) |
| "knowledge plane = the manifest / documents" | **knowledge plane = lessons/Oracle only** | manifest = relation plane (D17) |
| "indexer plane" (as a third plane) | **Indexer engine** | the indexer is an *engine*, not a plane |
| "`_index.yaml` is the source of truth" | **per-node files are truth; `_index.yaml` derived** | D21/D28 |
| "relation store / semantic store" (as databases) | relation **plane** (files) / semantic **index** (LanceDB) | planes ≠ stores |
| "state engine" (for the document owner) | **Manifest engine** | reserve "state engine" for `uacp-state` |
| Index port as a v1 deliverable | in-memory projector now; **Index port deferred** | D27 |
