---
type: analysis
title: Codeflair — Council Review (Round 1)
description: The serialized record of the first design-council pass — reviewers (3 Claude lenses + 1 cross-provider), the finding clusters, their grounding, and the disposition of each. Kept as a node so the review is part of the graph, not a lost chat.
tags: [codeflair, council, review, verification]
timestamp: 2026-06-24
edges:
  - {dst: 05-benchmark, rel: relates_to, provenance: asserted}
---

# Codeflair — Council Review (Round 1)

## The panel

Run on the v0 bundle (00–06) before these fixes. Four substantive voices, each told to improvise its own
checks and ground every finding in a quote from the as-built files (not grade the author's rubric):

- **Architecture & citation integrity** (Claude) — verdict: SOUND-WITH-FIXES
- **Devil's Advocate** (Claude) — verdict: SOUND-WITH-FIXES
- **Completeness vs. discussion** (Claude) — verdict: ADD-NODES
- **Cross-provider** (Gemini, external) — verdict: SOUND-WITH-FIXES

(A fifth voice, Codex, was dispatched but exhausted its provider quota and returned nothing; the
cross-provider requirement was met by Gemini.)

## Findings & disposition

| # | Finding (severity) | Raised by | Disposition |
|---|---|---|---|
| 1 | **Fabricated/stale citations** — "Norty" invented (zero hits; the plane is the **Manifest engine**, D43/D44); D13→superseded by **D29**; D17→superseded by **D44**; `code_anchor` misdescribed (it is checkpoint→`code_symbol`, `parsed`, deferred). Ground identity in **D44:912**. (P1) | Architecture, Gemini | **FIXED** — [01](01-contract.md), [02](02-probes.md), [05](05-benchmark.md) corrected; identity re-grounded in D44:912. |
| 2 | **Killed query-expansion prior missing** — no guardrail distinguishing search-expansion from the reverted query-string expansion. (P1) | Completeness, Gemini | **FIXED** — [CF-D7](07-decisions.md) records it as a rejected prior. |
| 3 | **No decisions node** — forks stated as conclusions; alternatives-weighed lost. (ADD-NODE) | Completeness | **FIXED** — added [07-decisions](07-decisions.md). |
| 4 | **Bake-off can't falsify its own premise** — every contender had an LLM; beating 42s proves nothing. (P1) | Devil's Advocate | **FIXED** — [CF-D5](07-decisions.md): mandatory **Policy D** (no-LLM control) + provenance-split recall + gate = "beat D." |
| 5 | **"Expand, don't diagnose" leaks** — ranking `inferred` edges *is* causal; "gap = missing test" *is* structural diagnosis. | DA, Gemini | **FIXED** — [01](01-contract.md) draws the structural-permitted / causal-barred line; [05](05-benchmark.md) tests it on the `inferred` subset. |
| 6 | **Eval set is a blocker dressed as a task** — promote to gating prerequisite + owner + agreement spike. (P1) | DA, Gemini | **FIXED** — [05](05-benchmark.md) makes the 20-pair smoke set + inter-labeler agreement a build-gating prerequisite. |
| 7 | **Scope/novelty** — most exists; real delta = co-change + beam-iterating the reranker; prototype around Oracle first. (P2) | Devil's Advocate | **FIXED** — [CF-D4](07-decisions.md): v1 is a spike around Oracle; graduate to a service only after it proves out. |
| 8 | **NL-seed entry point** — promote from open question to v1? (P2) | Gemini | **OPEN** — left in [06](06-open-questions.md); not forced into v1 pending the spike's seed needs. |

## Lesson recorded

The author's own self-review was **green** because it proved the bundle was *schema-valid* — it could
not catch that "Norty" was invented or that D13/D17 were superseded, because those are *citation-truth*,
not structure. Independent review grounded in the real producer files (graph-engine `02-decisions.md`,
`10-edge-schema.md`) is what caught them. This is the `verify-against-the-real-producer` discipline: a
passing structural check is not a substitute for an improvised, grounded second read.

## Round 2 (cross-provider, on the revised bundle)

Run on the post-fix bundle. Two cross-provider voices, each instructed to **re-verify the round-1
citation fixes** against the real graph-engine files (not trust them):

- **kimi** (Moonshot) — verdict: SOUND-WITH-FIXES
- **minimax-m3** (via opencode) — verdict: SOUND-WITH-FIXES

Both **independently verified** that the round-1 corrections hold (Norty gone; D17→D44; `code_anchor` =
checkpoint→code_symbol/parsed/deferred; D44:912 quoted exactly; identity correctly *not* an
engine/gate/check). No round-1 fix was found to have introduced a node-to-node contradiction.

### Round-2 findings & disposition

| # | Finding (severity) | Raised by | Disposition |
|---|---|---|---|
| R2-1 | **v1 over-claims "existing SCIP"** — SCIP + `code_anchor` are deferred/unbuilt; in v1 only LSP-derived `parsed` edges exist. (P1) | minimax | **FIXED** — [02](02-probes.md) adds a v1-availability column + section; [01](01-contract.md) and [05](05-benchmark.md) scope the spike + the `parsed` subset to what exists today. |
| R2-2 | **`code_anchor` described bidirectional** — the edge is directional checkpoint→code_symbol. (P2) | kimi | **FIXED** — [02](02-probes.md): directional edge; reverse traversal via index lookup. |
| R2-3 | **Result tags mislabeled as manifest provenance** — grep=`parsed` and co-change have no `rel_type`; Codeflair writes nothing. (P2) | kimi, minimax | **FIXED** — [02](02-probes.md): the column is a heatmap *result tag*; grep/co-change are non-serialized in-memory results, not manifest edges. `derives_from`=`asserted` split out. |
| R2-4 | **Identity placed "in" the application ring** — drivers sit *above* it. (P2) | kimi | **FIXED** — [01](01-contract.md): "driver above the application ring." |
| R2-5 | **D44 over-claimed as a bake-off** — it is an architecture correction. (P3) | kimi | **FIXED** — [05](05-benchmark.md), [CF-D2](07-decisions.md). |
| R2-6 | **CF-D7 over-claimed a measured in-repo recall regression.** (P2/P3) | kimi | **FIXED** — [CF-D7](07-decisions.md): "removed as dead code; evidence = literature + QMD retirement." |
| R2-7 | **Misc citation precision** — D29-supersedes-D13 (via chain), 100k+ regime (D11/D12), Manifest-engine ownership (D43/D44 not D29). (P3) | kimi, minimax | **FIXED** — [00](00-overview.md), [01](01-contract.md), [02](02-probes.md). |

Round-2 verdict: **SOUND-WITH-FIXES, all applied.**

## Scope change after R1/R2 — Round 3 now REQUIRED

After R1/R2 the bundle was **re-scoped** ([CF-D8](07-decisions.md)): from a read-only *lookup driver* to
**the whole Code Engine** (build SCIP + store + query). This **reverses the councils' "not an engine"
finding** — correctly, because the scope changed (a storage-owning engine, not a pure reader). The
producer/store nodes ([01a](01a-indexer.md), [01b](01b-store.md)) are **new and un-reviewed**, and the
engine-identity reversal touches governance (an engine that *writes* its index, even a rebuildable one).

**A Round 3 council is required before this enters governance (PROPOSE/PLAN)** and must:
1. verify the not-an-engine→is-an-engine reversal is sound (store ownership; build-side write is a
   rebuildable projection, not governed state);
2. review the new indexer/store nodes against the graph-engine substrate (D12/D29/D44) and the
   `code_anchor` producer gap they claim to close;
3. include a cross-provider voice (R1 = Gemini; R2 = kimi + minimax; Codex pending quota).
