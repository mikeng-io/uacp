---
type: analysis
title: Codeflair — Prior Art & Adopt-vs-Build
description: A 2026 prior-art check found the code-graph-for-agents space is crowded — the engine is commodity. So Codeflair's plan flips from "build an engine" to "ADOPT the substrate (tree-sitter base + SCIP/LSP-via-Serena refine), BUILD only the fuse/reconcile + the UACP cross-plane adapter (the sole novelty)." Records the landscape, the efficiency-vs-quality (tree-sitter vs SCIP) reasoning, and the adopt/build table.
tags: [codeflair, prior-art, adopt-vs-build, tree-sitter, serena]
timestamp: 2026-06-25
edges:
  - {dst: 00-overview, rel: relates_to, provenance: asserted}
---

# Codeflair — Prior Art & Adopt-vs-Build

## The finding: the engine is commodity (2026)

A prior-art check (web, 2026-06) found the **code-graph-for-agents** category is crowded and active.
Codeflair as a from-scratch engine would be **reinvention**. The pieces — and close-to-whole combos —
already exist:

| Project | What it is | Overlap with Codeflair |
|---|---|---|
| **Aider repo-map** | tree-sitter symbol graph + **PageRank** ranking → LLM context | *validates* the deterministic-ranked-subgraph thesis — and is prior art for it |
| **Serena** (oraios) | **pure-LSP** MCP, 40+ languages (`find_symbol`/`find_references`) | the live-LSP layer, done |
| **Codebase-Memory** | tree-sitter → **SQLite** graph, 66 langs, MCP, **content-hash freshness**, **+LSP-hybrid** refine | *almost exactly* our design (store + freshness + reconcile) |
| **techsavvyash/codegraph** | **SCIP** + Neo4j + MCP; PR **blast-radius + test-gaps** | our exact feature list |
| **knowing** (blackwell) | SCIP + static + runtime traces; blast radius + test scope; content-addressed freshness | a superset |
| **colbymchenry/codegraph** | pre-indexed graph, **working-tree reconcile**, **uncommitted-change impact**, staleness banner | our freshness/3-zone model |

(Also: Anthropic shipped **native LSP in Claude Code**, Dec 2025 — the host runtime is entering this space.)

## The axis underneath it all: efficiency vs quality

Most tools use **tree-sitter**, not SCIP — *not* because it's better (it's fuzzier) but because it wins
on **adoption physics**: no toolchain, ~160 languages uniformly, instant/incremental, parses broken code,
reliably installable. **SCIP** trades all that for **semantic precision**, and needs the language
toolchain + a building project (the install friction we hit). So:

- **tree-sitter = reach/robustness/ease** (good-enough fuzzy graph, works anywhere).
- **SCIP/LSP = precision** (correct edges, narrow + heavy).
- **The mature pattern is a gradient, not a choice:** tree-sitter **base** + SCIP/LSP **refinement where
  available** (Codebase-Memory does exactly this).

**Which side a consumer needs depends on the use:** fuzzy-but-fast context for an LLM that verifies anyway
→ tree-sitter; a **trust-grade, complete blast radius for a governance gate** → SCIP precision. **UACP is
the trust-grade case** (re-derivable, gate-grade), so SCIP-first is *coherent for UACP* even though it is
the wrong base for a mass-market tool.

## The consequence: adopt the substrate, build only the novelty

Codeflair's **only genuine novelty is the UACP cross-plane / governance adapter** (`code_anchor` → manifest
intent). Every other layer is commodity. So the build plan flips:

| Layer | Plan |
|---|---|
| grep · co-change | **build** (trivial) |
| **tree-sitter** (breadth floor — see [02-probes](02-probes.md)) | **adopt** (py-tree-sitter / a tree-sitter graph tool) |
| **LSP** (live, freshness) | **adopt Serena / multilspy** (don't hand-integrate N language servers) |
| **SCIP** (precise, the UACP trust-grade case) | **adopt** `scip-go` etc. |
| **fuse + reconcile + rank** (the precision ladder) | **build** — the engine logic |
| **UACP cross-plane adapter** | **build** — the sole differentiator |

## Recommendation (supersedes "build a Codeflair engine")

1. **Evaluate adopting** Serena (LSP) + a graph tool (tree-sitter base; e.g. Codebase-Memory / colbymchenry-codegraph) against the Trustless cases — the spike is the harness.
2. **Build the thin layer that's actually ours:** the fuse/reconcile (the precision ladder) + the **UACP cross-plane adapter**.
3. Keep it an **in-UACP abstracted package** (CF-D12) so the substrate choice stays swappable.

Decision recorded as [CF-D14](07-decisions.md). *(Sources: Aider repomap; Serena (oraios/serena); Codebase-Memory arxiv 2603.27277; techsavvyash/codegraph; blackwell-systems/knowing; colbymchenry/codegraph.)*
