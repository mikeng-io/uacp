# Codeflair eval seed-set

This is the **CF-D5 build-gating prerequisite** for the Code Engine: the labeled
`(seed → ground-truth subgraph)` pairs the benchmark ([../05-benchmark.md](../05-benchmark.md))
uses to rank the expansion policies (**D** no-LLM control / A / B / C). Without
an *agreed* set, the bake-off cannot arbitrate, so producing it gates the build.

## What a pair is

A `seed` (a symbol, a diff, or an NL incident) plus the **ground-truth subgraph**
— the nodes a competent engineer agrees belong in the blast radius / relations /
gaps — each tagged with how it should be found (`via`) and its `provenance`
(`parsed` vs `inferred`). See the header of [`seed-set.yaml`](seed-set.yaml).

## The two rules that keep this honest

1. **Non-fiction.** Ground truth is **derived from this repo at a pinned commit**
   (`repo_commit`), never invented — the spike-fictional trap UACP has hit before.
   Every pair carries a `derivation:` line showing how its node set was obtained
   (LSP `findReferences`, git co-change, grep, or manual).
2. **Human adjudication gates the build (CF-D5).** Mechanical derivation produces a
   *candidate*; a human label makes it ground truth. The build gate is **≥20 pairs
   with measured inter-labeler agreement** on this repo. Pairs marked
   `adjudication: needs-human` are awaiting that step; `grounded-mechanical` are
   derived from precise tooling but still want a confirm.

## How it's scored

- **recall@K of the ground-truth nodes** — primary metric — **split by provenance**
  (`parsed` vs `inferred`). The cheap-model premise only holds if it survives on the
  **`inferred` subset** (run cheap-vs-big model there). This is why pair **B**
  (co-change) is flagged as the primary cheap-model test.
- **gaps** are scored **best-effort, separately** (absences have no clean ground
  truth) — not folded into recall@K (CF-D6).

## The `layer` dimension (Codeflair's abstraction)

Each pair is tagged **`core`** or **`uacp-adapter`**. The Code Engine's **core**
(SCIP/LSP/grep/co-change → store → loop → heatmap) runs **standalone on any git
repo with zero UACP**; the **uacp-adapter** is the pluggable `code_anchor` /
manifest cross-plane join. The eval split mirrors this: **core** pairs validate
the engine on its own; **uacp-adapter** pairs validate the join. (This split will
be formalized in the design as **CF-D9**; here it's a forward reference.)

## Status of this starter set

| pair | capability | layer | grounded? |
|---|---|---|---|
| A `resolve_uacp_root` | symbol blast-radius | core | ✅ LSP refs ⊕ grep (6 files; grep-scoped missed 1 — the reconcile value) |
| B `graph_projection` | temporal / co-change | core | ✅ git co-change (real cluster); the cheap-model test |
| C governance orphan | cross-plane gap | uacp-adapter | recipe — `requires: code-plane-built` (can't ground until the indexer exists) |
| D NL incident (heartgate) | nl bootstrap | core | ✅ real expansion target (the heartgate validators dir) |
| E pre-PR diff (208f506) | gap sweep | core | ✅ real diff; **dynamic-dispatch case** — grep/registry wins where LSP is thin (inverse of A) |
| F high-fanout symbol | scale compression | core | ⚠ **ungroundable on UACP** (too small) — `requires: large-external-repo` in standalone mode |

**Next** (the actual CF-D5 work): fill C–F's `<...>`/`TODO`s by the same LSP/git
derivation, label all pairs by hand, measure inter-labeler agreement, and grow to
≥20. Note where SCIP-precise ground truth must wait on the indexer
([../01a-indexer.md](../01a-indexer.md)) — today LSP `findReferences` is the live
stand-in for SCIP refs.
