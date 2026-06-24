---
type: analysis
title: Codeflair — Probes & the Reconcile Job
description: The fixed probe set (SCIP, LSP, grep, manifest-graph, code_anchor, co-change), the uniform probe interface, the cross-plane code_anchor join that turns "find references" into "find relations", the reconciliation the orchestrator does by hand today, and the (corrected) substrate the probes consume.
tags: [codeflair, probes, scip, lsp, grep, co-change, code-anchor, cross-plane]
timestamp: 2026-06-24
edges:
  - {dst: 01-contract, rel: depends_on, provenance: asserted}
---

# Codeflair — Probes & the Reconcile Job

## The probe set (fixed; the policy over them is benchmarked)

A **probe** is a deterministic read against one source. Every probe takes a frontier node and returns
candidate nodes + the edge that connects them (typed, provenance-tagged). The *set* is fixed; *which
probes to run next and how to weight their results* is the benchmarked policy ([03](03-expansion-loop.md)).

| Probe | Source | Finds | Provenance |
|---|---|---|---|
| **SCIP** | per-commit symbol index | `defines` / `references` / `calls` — precise symbol edges | `parsed` |
| **LSP** | live language server | refs / impls / call-hierarchy — complements SCIP, stale-tolerant | `parsed` |
| **grep** | raw text | strings, config keys, cross-language, dynamic/reflective refs SCIP can't see | `parsed` |
| **manifest-graph** | the **Manifest engine** relation graph (D43/D44) | `derives_from` / work_unit / proposal edges (relation plane) | `derived` |
| **code_anchor** | the `code_anchor` edge (D5/D12) | the **cross-plane hop**: a checkpoint ↔ its `code_symbol` (file+symbol+lines+commit) | `parsed` |
| **co-change** | commit history | files/symbols that change **together** — temporal relations with no symbol edge | `inferred` |

> **Dependency flag (council P1):** `code_anchor` is a real construct (`graph-engine/10-edge-schema.md:62`)
> but it is **narrow** (checkpoint→`code_symbol`, `parsed`) and lives in the **deferred, unbuilt** code
> plane (`02-decisions.md:72,743`). The generic "any symbol ↔ the manifest node that governs it" is
> *not* as-built. Codeflair's cross-plane hop therefore **depends on the deferred code plane being
> built first**; until then the join is checkpoint-scoped only.

## The reconcile job (this is what the orchestrator does by hand today)

`CLAUDE.md` already states the rule: *LSP is precise but freshness-dependent and single-root; grep is
the complement that catches strings/comments/dynamic refs/stale-index gaps; **reconcile — the suite
decides.*** Codeflair **mechanizes that reconciliation**. Each hop it runs the relevant probes in
parallel and merges them:

- SCIP/LSP agree → high-confidence symbol edge.
- grep-only hit (no SCIP edge) → a candidate the precise tools missed (dynamic/string/config) — kept,
  flagged lower-confidence.
- SCIP/LSP disagree (e.g. thin cross-file results after a structural change) → kept as *unreconciled*,
  surfaced in the evidence trail rather than silently dropped.

The orchestrator stops being the probe-sequencer. It receives the *reconciled* result.

## The cross-plane join is what makes this more than agentic grep

A grep/SCIP hit is a **code-plane** node (symbol/file). A proposal or work_unit is a **relation-plane**
node. Alone, neither plane answers "what governs this code / what code realizes this intent." The
**`code_anchor`** edge bridges them: it lets the frontier cross from a `code_symbol` to the checkpoint
(and thence the manifest subgraph) anchored to it, and back. A Codeflair heatmap therefore **spans both
planes** — code symbols *and* the manifest intent they trace to — which is exactly the comprehension the
orchestrator currently rebuilds by hand. (Per D44:912 this is a *query-time join in the calling skill*,
the sanctioned cross-plane pattern — see [01-contract](01-contract.md).)

## Why co-change is first-class — but default-on is benchmarked

The relations that matter for blast radius are not all *symbol* relations. Two files that always change
together, or a config key a deploy touches alongside a module, are **temporal** relations with **no
edge for SCIP/LSP/grep to follow** — they would never be found by reference-walking. The co-change
probe is the one that turns Codeflair from a fancy reference-walker into a **relation finder**. It is
also the **noisiest** probe, so two things are true at once and must not be confused (the council flagged
the latent contradiction): co-change is a **first-class member of the probe set**, *and* its
**default-on status is a benchmark axis** ([05](05-benchmark.md)) — it ships available, and is promoted
to on-by-default only if "on" measurably beats "off" on recall. Decision recorded in
[07-decisions](07-decisions.md).

## Substrate (decided elsewhere; Codeflair only consumes it — corrected per council)

The probes read substrate already locked by the graph-engine bake-offs. The **live** decisions (earlier
ones were superseded):

- **SCIP** indexer for symbol-precise code edges — **D12** (still live).
- **Structural store = plain YAML + in-memory projection; semantic = LanceDB; no sqlite-vec, no
  structural DB** — **D29** (supersedes D13/D16). The Qwen3 reranker is post-retrieval/store-agnostic
  and survives.
- **Indexing is folded into each engine's read-side; cross-plane = a query-time join in the calling
  skill** — **D44** (supersedes D14/D17/D37).
- The **code-plane** symbol-graph store (per D12) is itself **deferred/unbuilt**.

Codeflair adds **no** new store — it is a reader.
