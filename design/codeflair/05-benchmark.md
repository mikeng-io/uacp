---
type: analysis
title: Codeflair — The Bake-off
description: How Codeflair decides its policy by measurement, not faith — the mandatory no-LLM control (Policy D), the policy/probe axes, the labeled eval set promoted to a gating prerequisite, provenance-split metrics that test whether the LLM is actually needed, and the promotion gate (beat D, not just 42s).
tags: [codeflair, benchmark, bake-off, eval, metrics, policy-d]
timestamp: 2026-06-24
edges:
  - {dst: 03-expansion-loop, rel: decides_on, provenance: asserted}
---

# Codeflair — The Bake-off

## "We need to benchmark" is the house style, not a punt

Substrate decisions in the sibling bundle were settled by measured bake-offs — D12 (SCIP indexer) and
D29 (structural+semantic stores); D44 (indexing-as-engine-capability) is an architecture correction,
not a bake-off. The policy fork
(A/B/C/**D**, [03](03-expansion-loop.md)) is the same kind of question. The design's job is **not** to
pick now; it is to make the policy swappable behind a fixed interface, build the harness, and let data
choose — **including the choice to use no LLM at all.**

## The mandatory control: Policy D (council P1)

The original A/B/C all contained an LLM, so the bake-off literally **could not discover that the LLM is
unnecessary** — beating Trustless's 42s bar is trivial for *any* method and proves nothing about the
model. So the benchmark adds a **mandatory control**:

- **Policy D — deterministic score, zero model calls.** Rank/prune the frontier by a weighted heuristic:
  edge-type confidence + graph distance + co-change PMI + recency. Fully deterministic, millisecond-fast,
  no eval-labeling dependency to *run*.

Pruning at scale is necessary (a cardinality problem); whether it needs an **LLM** was the question —
**now resolved by [CF-D11](07-decisions.md): no. Policy D is the default engine**; the Trustless spike
shows deterministic ranking is fast + correct. The A/B/C *LLM* policies are **deferred** — kept only as
future curiosities that would have to beat D; this bench section stands as the gate *if* they're ever
revisited.

## What is fixed vs. what the benchmark decides

| **Fixed (build now)** | **Benchmarked (decide later)** |
|---|---|
| Probe adapters (SCIP ∥ LSP ∥ grep ∥ manifest ∥ code_anchor ∥ co-change) | Policy: **D (no LLM)** / A (LLM ranks) / B (LLM drives) / C (hybrid) |
| Read-only heatmap output + gap flags | Beam width K, max hops, convergence threshold |
| Replayable watermarked trace | Which small model (if any) |
| code_anchor adapter (produced by the indexer, [01a](01a-indexer.md)) | Co-change probe: on vs. off |
| The strategy interface (`next_probes` / `score`) | The *implementation* of that interface |

## The eval set — a gating PREREQUISITE, not an open task (council P1)

The bake-off needs labeled pairs **`(seed → ground-truth relevant subgraph)`**, and a blast-radius
set-membership label over a huge graph is *harder* than the Oracle's retrieval pairs (reasonable
engineers disagree on the boundary). So eval-set production is promoted from "open question" to a
**blocking prerequisite before any adapter is built**:

1. A **named owner** produces a **20-pair smoke set** on *this* repo (half the Oracle ≥50-pair bar).
2. Measure **inter-labeler agreement** on blast-radius membership. If agreement is low, `recall@K of the
   true root node(s)` is ill-defined and the bake-off cannot arbitrate anything — that finding gates the
   build.

## Metrics (provenance-split — the real test of "expand-not-diagnose")

- **recall@K of the true root node(s)** — the primary metric — **reported split by probe provenance**
  (`parsed` vs `inferred`). Per [CF-D11](07-decisions.md) the default is deterministic (Policy D); *if* a
  future LLM policy is ever revisited, it only matters where it beats Policy D on the **`inferred`
  subset** (co-change), where ranking is hardest — run that comparison on that subset only.
  *(The `parsed` subset comes from the engine's own indexer ([01a](01a-indexer.md)) — SCIP + LSP. An
  optional thin early spike, run before the indexer ships, has `parsed` = LSP-only.)*
- **hops-to-hit** — how deep before the true node enters the beam.
- **model-calls per run** — the cost axis; B highest, **D zero**.
- **wall-clock per query** — must beat **Trustless's retired QMD at ~42s/query** ([00](00-overview.md)).
  Necessary, not sufficient (Policy D beats it trivially).
- **gaps (best-effort)** — scored on a **separate, best-effort** label set, **not** folded into the
  primary recall@K (absences have no clean ground truth). Gaps stay a first-class *output*; they are not
  a first-class *metric*.

## The promotion gate

An **LLM** policy becomes the default only when, on the labeled set, it **beats Policy D by a material,
stated margin on recall@K (especially the `inferred` subset) at acceptable cost** — *not* merely when it
beats 42s. If no LLM policy beats D, the finding is **"the deterministic baseline wins"** — ship D, drop
the model. If no policy clears the recall bar at all, the finding is **"Codeflair is not yet viable"** —
a real negative result (as QMD's retirement was), not a forced ship. Co-change is promoted to default
only if "on" measurably beats "off."
