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
| **LSP** | live language server | refs / impls / call-hierarchy — live, stale-tolerant | `parsed` (real edge) | ✓ now |
| **grep** | raw text | strings, config keys, cross-language, dynamic/reflective refs | in-memory hit (text match) | ✓ now |
| **manifest-graph** | the **Manifest engine** read-side projection (D43/D44) | `derives_from` / work_unit / proposal edges | the edge's own provenance (`derives_from`=`asserted`; FK=`derived`) | ✓ now |
| **co-change** | commit history | files/symbols that change **together** — temporal | in-memory result (`inferred`-grade; not a manifest edge) | ✓ now |
| **SCIP** | per-commit symbol index | `defines` / `references` / `calls` — precise symbol edges | `parsed` (real edge) | ⏳ **deferred** |
| **code_anchor** | the `code_anchor` edge (D5/D12) | the cross-plane hop: a checkpoint → its `code_symbol` | `parsed` (real edge) | ⏳ **deferred** |

> **Codeflair writes nothing** (see [01](01-contract.md)). The "result tag" is the confidence/source
> label it attaches to a *heatmap node in memory* — it is the manifest edge's real provenance **only
> when** the probe surfaces an already-serialized edge (LSP/SCIP/`code_anchor`/manifest-graph). grep
> hits and co-change correlations are **not** manifest edges — there is no `grep` or `co_change`
> `rel_type` in the edge schema — so they are carried as in-memory heatmap results, never written back.

## v1 availability — the spike runs on what exists today (council R2, P1)

SCIP and `code_anchor` belong to the **deferred, unbuilt code plane** (D5/D27/D44; *"All of
LSP/codegraph/SCIP are EXTERNAL deps"*, D36). So the v1 spike runs the **available-now** probes — LSP,
grep, the Manifest-engine read-side projection, and co-change/git history — and the `parsed`-grade edges
in v1 come from **LSP only**. SCIP and the cross-plane `code_anchor` hop **light up when the code plane
ships**; until then the heatmap is code-plane-shallow (LSP + text + co-change) and relation-plane-deep
(manifest projection). The spike measures the delta with the probes it actually has.

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

## The cross-plane join is what makes this more than agentic grep

A code hit is a **code-plane** node (symbol/file). A proposal or work_unit is a **relation-plane** node.
Alone, neither answers "what governs this code / what code realizes this intent." The **`code_anchor`**
edge bridges them. It is **directional** — `checkpoint → code_symbol` (`10-edge-schema.md:62`) — so the
frontier crosses *forward* checkpoint→symbol along the edge, and *backward* symbol→checkpoint via a
**reverse index lookup**, not a symmetric edge. A Codeflair heatmap therefore **spans both planes** —
code symbols *and* the manifest intent they trace to. Per D44:912 this is a *query-time join in the
calling skill*, the sanctioned cross-plane pattern (see [01-contract](01-contract.md)). It is gated on
the code plane being built (above).

## Why co-change is first-class — but default-on is benchmarked

The relations that matter for blast radius are not all *symbol* relations. Two files that always change
together, or a config key a deploy touches alongside a module, are **temporal** relations with **no
edge for SCIP/LSP/grep to follow**. The co-change probe is the one that turns Codeflair from a fancy
reference-walker into a **relation finder** — and the **noisiest**, so two things hold at once: co-change
is a **first-class member of the probe set**, *and* its **default-on status is a benchmark axis**
([05](05-benchmark.md)). Decision recorded in [CF-D3](07-decisions.md).

## Substrate (decided elsewhere; Codeflair only consumes it — corrected per council)

The **live** decisions (earlier ones were superseded):

- **SCIP** indexer for symbol-precise code edges — **D12** (the indexer verdict is live; the code-plane
  *store* it feeds is itself **deferred**, D27/D44).
- **Structural store = plain YAML + in-memory projection; semantic = LanceDB; no sqlite-vec, no
  structural DB** — **D29** (supersedes D16; D13's sqlite-vec is obsoleted via the D13→D16→D29 chain).
  The Qwen3 reranker is post-retrieval/store-agnostic and survives.
- **Indexing is folded into each engine's read-side; cross-plane = a query-time join in the calling
  skill** — **D44** (supersedes D14/D17/D37).

Codeflair adds **no** new store — it is a reader.
