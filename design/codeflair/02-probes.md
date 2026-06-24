---
type: analysis
title: Codeflair — Probes & the Reconcile Job
description: The probe set with v1 availability (LSP/grep/manifest/co-change live now; SCIP/code_anchor gated on the deferred code plane), how Codeflair tags results (it writes nothing, so non-edge results are in-memory tags, not manifest edges), the cross-plane code_anchor join, the reconcile job, and the corrected substrate.
tags: [codeflair, probes, scip, lsp, grep, co-change, code-anchor, cross-plane]
timestamp: 2026-06-24
edges:
  - {dst: 01-contract, rel: depends_on, provenance: asserted}
---

# Codeflair — Probes & the Reconcile Job

## The probe set (fixed; the policy over them is benchmarked)

A **probe** is a deterministic read against one source. Every probe takes a frontier node and returns
candidate nodes + how they connect. The *set* is fixed; *which probes to run next and how to weight
their results* is the benchmarked policy ([03](03-expansion-loop.md)).

| Probe | Source | Finds | Result tag | v1 avail. |
|---|---|---|---|---|
| **LSP** | live language server (**Serena**, [12](12-delivery.md)) | refs / impls / call-hierarchy — live, working-tree-fresh | `parsed` (real edge) | ✓ *when Serena/`uv` present*; absent → tree-sitter+grep |
| **contract-parser** | IDL files (proto / OpenAPI / GraphQL) | cross-language edges via codegen naming (`Account` → Go struct + TS iface) | `inferred` (near-deterministic) | ✓ now (cross-lang, [13](13-multi-language.md)) |
| **grep** | raw text | strings, config keys, cross-language, dynamic/reflective refs | in-memory hit (text match) | ✓ now |
| **tree-sitter** | syntactic parse (any language, no toolchain) | structural edges (name-based defs/refs) — the **breadth floor**: works on unsupported langs, broken code, dirty files | `syntactic` (fuzzy; below `parsed`) | ✓ now (adopt) |
| **manifest-graph** | the **Manifest engine** read-side projection (D43/D44) | `derives_from` / work_unit / proposal edges | the edge's own provenance (`derives_from`=`asserted`; FK=`derived`) | adapter only |
| **code_anchor** | adapter join (Manifest checkpoint ↔ `code_symbol`) | the cross-plane hop | `parsed` | adapter only |
| **co-change** | commit history | files/symbols that change **together** — temporal | in-memory result (`inferred`-grade; not a manifest edge) | ✓ now |
| **SCIP** | per-commit symbol index, produced by [01a](01a-indexer.md) | `defines` / `references` / `calls` — precise symbol edges | `parsed` (real edge) | core, phase-1 |

> **Probe layers (CF-D9, [09-abstraction](09-abstraction.md)):** SCIP / LSP / grep / tree-sitter /
> co-change are **core** — they run standalone on any git repo. `manifest-graph` and `code_anchor` are the
> **UACP adapter** — registered only when embedded in UACP. The loop is blind to which are present.
>
> **Precision ladder (CF-D14, [14-prior-art-and-adoption](14-prior-art-and-adoption.md)):** the probes form
> a precision gradient that the fuse step (④) ranks by — **SCIP/LSP (`parsed`, precise) > tree-sitter
> (`syntactic`, fuzzy/all-languages/broken-code-tolerant) > grep (text) > co-change (`inferred`)**.
> tree-sitter is the **breadth/fallback floor** — a node it finds where SCIP can't reach (unsupported
> language, uncompilable code, no toolchain) is kept, tagged lower-confidence, rather than lost. So
> Codeflair **degrades to tree-sitter quality** instead of failing, and **upgrades to SCIP/LSP precision**
> where the toolchain allows. Most of these layers are **adopted, not built** (CF-D14).

> **The query layer writes nothing** (see [01](01-contract.md)). The "result tag" is the confidence/source
> label it attaches to a *heatmap node in memory* — it is the manifest edge's real provenance **only
> when** the probe surfaces an already-serialized edge (LSP/SCIP/`code_anchor`/manifest-graph). grep
> hits and co-change correlations are **not** manifest edges — there is no `grep` or `co_change`
> `rel_type` in the edge schema — so they are carried as in-memory heatmap results, never written back.

## Build order — the engine produces its own precise edges

SCIP and `code_anchor` are no longer an external deferral: **this engine produces them**
([01a-indexer](01a-indexer.md)). The build order *within* the engine is **indexer → store
([01b](01b-store.md)) → query (here)**, so the query layer's `parsed`-grade SCIP/`code_anchor` edges
come online when the indexer ships. A **thin early spike** can still run the query loop on
LSP/grep/co-change + the Manifest-engine projection *before* the indexer lands — a code-plane-shallow
heatmap that tests the loop+prune hypothesis early ([05](05-benchmark.md)) — but the engine's
distinctive value (SCIP precision + the cross-plane join) arrives with [01a](01a-indexer.md).

## The reconcile job (this is what the orchestrator does by hand today)

`CLAUDE.md` already states the rule: *LSP is precise but freshness-dependent and single-root; grep is
the complement that catches strings/comments/dynamic refs/stale-index gaps; **reconcile — the suite
decides.*** Codeflair **mechanizes that reconciliation**. Each hop it runs the relevant probes in
parallel and merges them:

- (once SCIP ships) SCIP/LSP agree → high-confidence symbol edge.
- grep-only hit (no symbol edge) → a candidate the precise tools missed — kept, flagged lower-confidence.
- SCIP/LSP disagree (e.g. thin cross-file results after a structural change) → kept as *unreconciled*,
  surfaced in the evidence trail rather than silently dropped.

The orchestrator stops being the probe-sequencer. It receives the *reconciled* result.

## The cross-plane join (UACP adapter only) — what makes this more than agentic grep *when embedded*

**Standalone, the core is a strong relation-finder for the code side** (refs + call-hierarchy + co-change
+ grep/LSP reconcile) — essentially mechanized grep·LSP·SCIP. **When the UACP adapter is registered**, it
becomes more: a code hit is a **code-plane** node; a proposal or work_unit is a **relation-plane** node;
alone neither answers "what governs this code / what code realizes this intent." The adapter's
**`code_anchor`** join bridges them. It is **directional** — `checkpoint → code_symbol`
(`10-edge-schema.md:62`) — so the frontier crosses *forward* checkpoint→symbol, and *backward* via a
**reverse index lookup**, not a symmetric edge. The heatmap then **spans both planes**. Per D44:912 this
is a *query-time join in the calling skill*, the sanctioned cross-plane pattern (see
[01-contract](01-contract.md)). Gated on the code plane being built.

## Why co-change is first-class — but default-on is benchmarked

The relations that matter for blast radius are not all *symbol* relations. Two files that always change
together, or a config key a deploy touches alongside a module, are **temporal** relations with **no
edge for SCIP/LSP/grep to follow**. The co-change probe is the one that turns Codeflair from a fancy
reference-walker into a **relation finder** — and the **noisiest**, so two things hold at once: co-change
is a **first-class member of the probe set**, *and* its **default-on status is a benchmark axis**
([05](05-benchmark.md)). Decision recorded in [CF-D3](07-decisions.md).

## Substrate (decided elsewhere; Codeflair only consumes it — corrected per council)

The **live** decisions (earlier ones were superseded):

- **SCIP** indexer for symbol-precise code edges — **D12** (the indexer verdict is live; this engine
  *realizes* it as [01a](01a-indexer.md), feeding the store [01b](01b-store.md) it now owns).
- **Code-plane store = SQLite + recursive CTE** (this engine's own store, [01b](01b-store.md)) — **D12**.
  Note **D29** ("plain YAML + in-memory; no sqlite-vec; semantic = LanceDB") governs the **manifest /
  relation plane**, not the code plane — it bounds what the *adapter's* manifest-graph probe reads, not
  Codeflair's code store. The Qwen3 reranker is post-retrieval/store-agnostic and survives either way.
- **Indexing is folded into each engine's read-side; cross-plane = a query-time join in the calling
  skill** — **D44** (supersedes D14/D17/D37).

Codeflair *owns* its code-graph store ([01b](01b-store.md)); it adds **no** new store to the planes it reads.
