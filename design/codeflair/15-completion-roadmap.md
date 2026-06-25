---
type: analysis
title: Codeflair — Completion Roadmap (As-Built → Design)
description: >-
  The build roadmap that closes the gap between the merged Codeflair package
  (deterministic core only) and the full design this bundle already specifies.
  The design is complete and councilled; this node sequences the IMPLEMENTATION
  of the unbuilt layers — freshness (watermark + 3-zone reconcile), the live
  LSP/Serena overlay, SCIP enrichment, output honesty (replayable trace),
  the full heat formula, cross-plane completion, and the delivery faces — and
  resolves the as-built divergences. Each phase is a worktree-isolated,
  cross-provider-councilled, TDD slice. No new design surface; this maps gaps to
  the nodes that already specify them. Cross-provider councilled 2026-06-26
  (Claude + kimi + codex); their convergent findings are folded in.
tags: [codeflair, roadmap, completion, gap-closure, build-plan, freshness, lsp, serena]
timestamp: 2026-06-26
edges:
  - {dst: 00-overview, rel: realizes, provenance: asserted}
  - {dst: 10-freshness, rel: depends_on, provenance: asserted}
  - {dst: 11-substrate, rel: depends_on, provenance: asserted}
  - {dst: 12-delivery, rel: depends_on, provenance: asserted}
  - {dst: 04-outputs, rel: depends_on, provenance: asserted}
  - {dst: 09-abstraction, rel: depends_on, provenance: asserted}
---

# Codeflair — Completion Roadmap (As-Built → Design)

## What this is (and is not)

The deterministic **core** of Codeflair is built and merged (fused SQLite store, 3-language
SCIP ingest, tree-sitter floor, co-change + shared-string coupling, blast-radius CTE,
Policy-D heatmap, gap flags, cross-plane adapter skeleton, and the read-only UACP seam
`engines/code_plane.py` + `engines/code_index_build.py`). The **operational and delivery
layers the design specifies are largely unbuilt.** This node is the *implementation*
sequence that closes that gap.

It is **not new design.** Every capability below is already specified by an existing node
(10-freshness, 11-substrate, 12-delivery, 04-outputs, 02-probes, 03-expansion-loop,
01a-indexer, 13-multi-language). The gap is between *as-built code* and *as-designed
intent*, confirmed by a file:line-grounded audit (2026-06-26). Where this node would
otherwise pre-resolve build detail, it stops at acceptance criteria and lets the BUILD's
tests arbitrate (house style: don't over-serialize).

## Locked decisions (2026-06-26, mike)

- **Scope = full design completion.** Close all gaps and divergences, not a subset.
- **Serena is reached as a Python library** (not over MCP) — `lsp_ingest.py` imports
  Serena's language-server API directly. This is *how Codeflair reaches LSP*; it is why the
  engine is Python (12-delivery.md:74). **Open (see OD-1):** whether LSP edges are
  *persisted* into the store or supplied as a *live query-time overlay* — the council found
  these are different freshness architectures and 10-freshness defaults to the latter.
- **Kickoff = plan first.** This node is authored as pre-governance input for review; the
  formal run (TRIAGE→PROPOSE→PLAN→build slices) is a separate decision.

## The gap ledger (gap → the node that already specifies it → status)

| # | Capability | Specified by | As-built status |
|---|---|---|---|
| 1 | **LSP/Serena overlay** filling the `"lsp"` precision tier | 02-probes, 10-freshness, 12-delivery | UNBUILT — `store.py:23` reserves `"lsp"`, no producer |
| 2 | **Replayable search trace** (re-derivability) | 04-outputs | UNBUILT — `HeatmapEntry` carries only symbol/hop/score/via |
| 3 | **Watermark + per-file/per-source freshness** | 10-freshness, 11-substrate | UNBUILT — no watermark in `_SCHEMA`; `freshness` table exists (`store.py:48`) but is never written/read |
| 4 | **Probe registry** (pluggable seam, CF-D9) | 02-probes, 09-abstraction | UNBUILT — probes hardcoded in `expand.py` |
| 5 | **Cross-plane: read-only join + (separately) governed write** | 09-abstraction, 01a-indexer | UNBUILT — `manifest_anchor.py:94` marks the governed write deferred |
| 6 | **Delivery faces** (CLI / MCP / `.mcp.json`) | 12-delivery | UNBUILT — no `[project.scripts]`, no MCP server, no `.mcp.json` |
| 7 | **Full heat formula** (recency, fan-in, PMI, agreement) | 03-expansion-loop | PARTIAL — `query.py:19` has rel·trust·decay^hop only |
| 8 | **Eval seed-set ≥20 + recall@K harness** | 05-benchmark | PARTIAL — `eval/seed-set.yaml` has 6 (4 ungrounded) |
| 9 | **Incremental delta re-index** | 01a-indexer, 10-freshness | UNBUILT — full re-ingest only |
| 10 | **Contract-parser probe** (proto/OpenAPI/GraphQL → cross-lang edges) | 02-probes, 13-multi-language, CF-D13 | UNBUILT — `.proto` is only string-scanned by grep, not codegen-parsed |
| 11 | **Cross-plane spanning heatmap** (relation-plane nodes in the output when the adapter is registered) | 04-outputs, 02-probes, 09-abstraction | UNBUILT — loop walks code-plane edges/coupling only; `crossplane` answers a separate API |

### Divergences (as-built differs from design — correct these, not just fill)

- **D1 — tree-sitter change-detector role unbuilt (additive).** 01a-indexer specifies
  tree-sitter as the per-commit *change-detector* deciding what to re-index. As-built it is
  the *graph-source breadth floor* (`treesitter_ingest.py:152`) — which the design ALSO
  requires (CF-D14). So the change-detector is a **second, additive** role, not a wrong role
  that displaced the right one. P3 **adds change-detection while preserving** the graph-source
  floor (do not remove the floor). *(Reframed per unanimous council finding.)*
- **D2 — `calls`-only edges.** `scip_ingest.py:138` emits `rel="calls"` only; 01b-store
  specifies `defines`/`references`/`calls`. Reconciled in **P3**.
- **D3 — `VALID_SOURCES` vs the coupling axis.** `grep`→`shared_string` and `co_change`→
  `co_change` flow through `add_coupling` (`store.py:64` `VALID_COUPLING`), NOT as edge
  sources — consistent with 02-probes but divergent from 11-substrate. **Resolved in P0**
  (no longer "open"): tighten `VALID_SOURCES` to edge-emitting sources and amend 11-substrate
  to describe the two axes (coupling axis is the as-built truth; 02-probes agrees).
- **D4 — `CrossPlaneAdapter.__init__` mutates.** `crossplane.py:63` runs
  `CREATE TABLE code_anchor`, so a UACP consumer cannot instantiate it read-only. **Moved to
  P0** (council: a foundational read-only-safety fix, not an end-phase afterthought).
- **D5 — inferred manifest-granularity anchor vs the parsed edge schema.** `manifest_anchor.py`
  anchors by mining intent text at `manifest_id` granularity (`inferred`); the edge schema
  mandates `code_anchor = checkpoint → code_symbol`, provenance `PARSED`. This is a real
  divergence the prior ledger missed; bounded in **P7** (see OD-2). *(Added per council.)*

## The dependency spine — why freshness is the keystone

Most gaps converge on **freshness**. The watermark + per-file/per-source hashes (3), the LSP
overlay (1), the freshness tags, and the 3-zone reconcile are one interlocking mechanism
(10-freshness): the LSP overlay is meaningless without a watermark to reconcile *against*,
and the heatmap can't tag `trusted`/`live`/`unreconciled` without both. The eval harness (8)
gates the heat-formula tuning (7), so eval lands **before** the formula. Build order:
registry+safety → freshness substrate → LSP overlay → SCIP/change-detection → output
contract → eval → heat formula → cross-plane+delivery.

## Phases

Each phase = one worktree (`$UACP_ROOT/.worktrees/`), TDD, a cross-provider council pass
before PR (per [[council-include-external-reviewer]]), verification that improvises against
as-built reality ([[verification-must-improvise-and-ground]]).

### P0 — Foundations: probe registry + D3 enum + D4 read-only-safe adapter · closes #4, fixes D3, D4
- **Goal:** introduce the pluggable probe/source registry the UACP adapter and future probes
  (LSP, contracts) register into; tighten `VALID_SOURCES` to edge-emitting sources and amend
  11-substrate (D3); move `CREATE TABLE code_anchor` out of `CrossPlaneAdapter.__init__` so a
  read-only consumer can instantiate it (D4).
- **Acceptance:** existing probes run behavior-identically through the registry; a **new probe
  is added in a test without editing `expand.py`** (demonstrated, not asserted); a UACP
  consumer opens the adapter against a read-only index with no mutation; `VALID_SOURCES`
  rejects `grep`/`co_change` as edge sources.
- **Why first:** P2's LSP probe registers instead of hardcoding; D4 read-only safety unblocks
  integration-testing every later phase through the real seam.

### P1 — Freshness substrate · closes #3 (schema + population only)
- **Goal:** add the `watermark(repo_commit, built_at)` table; **populate** the existing
  `files`/`freshness` tables (per-file content hash, per-source `commit_sha`/`tool_version`)
  at ingest; per-file hash compare at query time.
- **Acceptance:** after an ingest, watermark + per-source freshness rows exist and match the
  real index (not synthetic); a hash-mismatched file is *detected* `stale`. **No reconcile-tag
  claims here** — `live`/`unreconciled` require the LSP overlay (P2), so they are verified
  there. (Council: the old "zero re-index" criterion was vacuous; restated to schema+population.)
- **Specified by:** 10-freshness (index side), 11-substrate (schema).

### P2 — LSP/Serena overlay + 3-zone reconcile · closes #1
- **Goal:** wire Serena (Python lib) as a registered probe supplying LSP refs/defs over the
  working tree; the query-time **3-zone reconcile** uses P1's watermark/hashes to tag nodes
  `trusted`/`live`/`unreconciled`. **OD-1 decides** whether LSP is a live query-time overlay
  (10-freshness default) or persists `source="lsp"` rows (the deferred working-layer) — resolve
  before building.
- **Acceptance:** on a dirty file the LSP overlay supersedes stale SCIP and the node is `live`;
  on SCIP↔LSP conflict the node is `unreconciled` and surfaced, never silently blended; Serena
  absent → clean two-zone degrade (`trusted`/`stale`), not an error.
- **Specified by:** 10-freshness (3-zone), 12-delivery (Serena, uvx).

### P3 — SCIP enrichment + tree-sitter change-detection · closes #9, fixes D1, D2
- **Goal:** emit `defines`/`references` edges (D2); **add** tree-sitter change-detection driving
  a delta re-index (D1, #9), re-SCIP-ing only changed files and advancing the watermark —
  **without removing** the tree-sitter graph-source floor.
- **Acceptance:** a single-file edit re-indexes only that file (a negative test asserts the
  corpus is untouched — catches accidental full re-index); `defines`/`references` are queryable
  and distinct from `calls`; the tree-sitter graph-source floor still emits its edges.
- **Specified by:** 01a-indexer, 01b-store, 10-freshness.

### P4 — Output honesty: replayable trace + JSON contract · closes #2
- **Goal:** a replayable, watermarked search trace (hop log) and the structured
  `{nodes[], gaps[], trace{}}` JSON contract.
- **Acceptance:** **byte-stable** JSON replay of the full contract — nodes AND scores, order,
  hops, freshness tags, provenance, gaps, and the kept/pruned beam — from the trace; a
  content/hash mismatch marks the trace stale. (Council: "same nodes" alone was too weak.)
- **Specified by:** 04-outputs (the "re-derivability reconciliation").

### P5 — Eval harness · closes #8 (moved BEFORE the heat formula)
- **Goal:** grow `eval/seed-set.yaml` to ≥20 grounded pairs (CF-D5 prerequisite) and wire the
  recall@K harness.
- **Acceptance:** recall@K runs against ≥20 labeled, human-grounded pairs and reports a
  baseline for the current Policy-D formula.
- **Specified by:** 05-benchmark, CF-D5. *(Was inside the old P6; pulled forward because it
  gates P6 tuning — unanimous council blocker.)*

### P6 — Full heat formula · closes #7 (tuned against P5)
- **Goal:** add `recency_factor`, fan-in penalty `÷(1+log(fan_in))`, `co_change_PMI`, and the
  multi-probe `agreement_bonus` to Policy D.
- **Acceptance:** each term independently tested; constants tuned against **P5's** eval set
  (recall@K improves or is neutral, never regresses); the `agreement_bonus` is defined to
  apply only to non-conflicting probes — it never re-blends an `unreconciled` node (resolves
  the P2↔formula tension the council flagged).
- **Specified by:** 03-expansion-loop.

### P7 — Cross-plane completion + delivery · closes #5, #6, #11, fixes D5
- **Goal:** (a) **read-only join** — register a cross-plane probe so the heatmap *spans* both
  planes (relation-plane manifest nodes appear in the output when the adapter is registered,
  #11) using the read-only-safe adapter from P0; (b) **governed write** — Step-B
  (`code_anchor = checkpoint → code_symbol`, provenance `PARSED`, from the EXECUTE diff) is
  **split out** and treated as needing its own schema/projection/governed-writer design
  (OD-2) — *not* claimed as a "no-kernel-change" drop-in; (c) delivery faces — CLI
  (`[project.scripts]`), MCP server, and the bundled `.mcp.json` (agent-facing Serena),
  **all** delivery artifacts owned here (not split into P2).
- **Acceptance:** a registered cross-plane query returns a heatmap containing relation-plane
  nodes; the read-only join performs no governed write; `codeflair query`/`index` run from the
  CLI; the MCP server registers and answers; Step-B governed write proceeds only after OD-2 is
  resolved with its own design + tests.
- **Specified by:** 09-abstraction (CF-D9 boundary), 04-outputs (spanning), 12-delivery,
  05-benchmark; seam correctness per the Shim-B rejection (07-decisions / edge schema).

## Open design decisions (resolve at PROPOSE, before building the affected phase)

- **OD-1 (P2) — LSP: live overlay vs persisted edges.** 10-freshness defaults to a
  *query-time live overlay* that does **not** write dirty-file rows; persisting `source="lsp"`
  edges is the explicitly-**deferred** working-overlay layer. Yet `"lsp"` sits in
  `VALID_SOURCES` as an edge source. **Council finding (2 reviewers, blocker):** the locked
  "writes `source=lsp` edges" describes the deferred working-layer, contradicting the live
  default. **Recommendation:** build the live query-time overlay first (default), keep the
  persisted working-layer deferred until a measured edit-then-query loop proves it's needed;
  reconcile the `VALID_SOURCES` `"lsp"` slot with that choice. **Needs mike's ruling — it
  touches the locked Serena decision.**
- **OD-2 (P7) — Step-B governed write.** The read-only join (query/join anchors) is safe to
  build now; the *governed* `code_anchor` write into UACP's graph contradicts the current
  "Codeflair outputs are not governed writes / edge promotion deferred" stance and the prior
  Shim-B rejection. **Recommendation:** ship the read-only join in P7; gate the governed write
  behind its own design node (correct seam: checkpoint→code_symbol, PARSED, adapter-emitted,
  neutral `code_refs` at most in the kernel) before any kernel change.
- **OD-3 (P5/P6) — policy interface.** 03-expansion-loop specifies a swappable
  `next_probes`/`score` interface so A/B/C could plug in later; CF-D11 defers A/B/C. Decide:
  build the interface seam now (cheap, future-proofs P6) or note it explicitly deferred. *(Not
  a gap — a stated deferral, per council.)*
- **OD-4 (P1/P2) — per-worktree store keying.** Confirm `.codeflair/` is keyed to the worktree
  root and gitignored (10-freshness) before the freshness block lands.

## Cadence & invariants

- Worktree per slice under `$UACP_ROOT/.worktrees/`; never write `main` directly.
- TDD; tests assert specific behavior and prove non-vacuity ([[test-quality-no-vacuous-tests]]).
- Cross-provider council per PR (not same-model self-review).
- `codeflair/` stays import-clean of `uacp` (CF-D9); the UACP seam stays read-only.
- The engine is **pre-release**: `HeatmapEntry`/output-shape changes (freshness tags in P2,
  the JSON contract in P4) are permitted breaking changes within codeflair — "additive" means
  no regression to the **UACP suite**, not a frozen `HeatmapEntry`. *(Clarified per council.)*
