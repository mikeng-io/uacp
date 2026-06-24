---
type: analysis
title: Codeflair — The Expansion Loop & Swappable Policy
description: The frontier/beam model, why pruning is necessary (cardinality) but LLM-pruning is not yet proven, the stop conditions, the fixed strategy interface (next_probes / score), and the four policies (D no-LLM control, A LLM-ranks, B LLM-drives, C hybrid) the benchmark chooses between.
tags: [codeflair, expansion, loop, beam, policy, pruning, policy-d]
timestamp: 2026-06-24
edges:
  - {dst: 02-probes, rel: consumes, provenance: asserted}
---

# Codeflair — The Expansion Loop & Swappable Policy

This is **search/evidence expansion** — iterating *probe → prune* to grow the evidence frontier — **not**
query-string expansion (a rejected prior; see [CF-D7](07-decisions.md)).

## The loop

```
seed → normalize to an initial frontier
  repeat:
    1. probe   — run the relevant probes (02) over the current frontier  → candidate nodes + edges
    2. score   — the policy (an LLM, or a deterministic score under Policy D) ranks the candidates
    3. prune   — keep the top-K (the beam); the rest are recorded but not expanded
    4. accrue  — add kept nodes to the heatmap with their evidence
  until  stop condition
emit → heatmap + evidence trail + gaps + trace (04)
```

`score` and `prune` are where the **policy** lives. `probe` is deterministic.

## Why pruning is necessary — but an LLM may not be

At codespace scale the frontier explodes: hop 1 of a moderately-connected symbol returns dozens of
references; hop 2 returns thousands. **Unbounded expansion is unusable** — it would return half the
repo, so *some* ranking + top-K prune is mandatory. But the council caught a conflation: "pruning is
necessary" (a cardinality fact) is **not** "**LLM** pruning is necessary." A deterministic score
(edge-confidence + graph-distance + co-change-PMI + recency) also ranks + top-K, in milliseconds, with
zero model calls. Whether an LLM beats that baseline is an **open empirical question** — exactly what
**Policy D** tests ([05](05-benchmark.md), [CF-D5](07-decisions.md)). The design does **not** assume the
LLM is needed.

## Stop conditions

The loop terminates on the first of:

- **max-hops** — a hard depth cap (a blast radius is local; depth is bounded).
- **budget** — a cap on probes and model calls per run (cost ceiling).
- **convergence (loop-until-dry)** — N consecutive hops add no node above the relevance threshold.

The *shape* of these conditions is fixed; their *values* (hop cap, K, threshold) are tuned by the
benchmark ([05](05-benchmark.md)).

## The fixed strategy interface

Everything above is invariant. The **policy** — deterministic vs. how much the model drives vs. ranks —
is a swappable strategy behind one interface:

```
next_probes(evidence_so_far) -> [probe]      # which probes to run next hop
score(frontier)              -> ranked_nodes # relevance ranking → beam selection
```

Build the interface and the harness now; let the benchmark choose the default implementation — including
the choice of **no LLM at all**. The winner does not change the interface, the probes, the outputs, or
the trace.

## The policies the benchmark compares

| | Policy | `next_probes` | `score` | Trade-off |
|---|---|---|---|---|
| **D** | **no LLM (control)** | fixed rules enumerate next probes | deterministic score (edge-conf + distance + co-change-PMI + recency) | zero model calls, fully deterministic, millisecond-fast. **The null hypothesis A/B/C must beat** ([CF-D5](07-decisions.md)). |
| **A** | LLM ranks; expansion deterministic | fixed rules enumerate next probes | LLM scores the frontier | cheap, auditable, reuses the Qwen3 reranker made iterative |
| **B** | LLM drives + ranks (agentic) | the LLM emits the next probes itself | LLM scores | most flexible at weird boundaries; every hop is a model call; only replayable-from-trace |
| **C** | hybrid: deterministic candidates, LLM steers | fixed rules *enumerate* candidates; LLM *picks a subset* | LLM scores | bounded non-determinism; the LLM never invents a probe from nothing |

All four honor the read-only/hypothesis contract ([01](01-contract.md)) and emit the same outputs
([04](04-outputs.md)). They differ only in how the frontier is chosen — which is exactly what the
benchmark measures.
