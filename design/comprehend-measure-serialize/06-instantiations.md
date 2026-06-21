---
type: analysis
title: Instantiations — graph-engine, verification, lifecycle as CMS in the concrete
description: How the abstract primitive shows up as UACP-execution — the graph engine is its serialize discipline, the verification method is its loop, the lifecycle is the cycle iterated. The mapping from underlying-logic to UACP-execution, and the reframe of UACP as an information-processing architecture.
tags: [primitive, instantiation, uacp, graph-engine, verification, lifecycle]
timestamp: 2026-06-21
edges:
  - {dst: 00-the-axiom, rel: depends_on, provenance: derived}
---

# Instantiations — the abstract layer made concrete

CMS ([00-the-axiom](00-the-axiom.md)) is the *underlying logic*; UACP-execution is one **instantiation** of it. The mapping:

| CMS facet | UACP instantiation | Bundle |
|---|---|---|
| **serialize** discipline (typed key + provenance, idempotent canonical form) | the **graph engine** (`graph_projection`, the entity-writer, `uacp-fmt`, edge records) | [graph-engine](../graph-engine/00-overview.md) |
| the **loop** (comprehend → measure → serialize, to convergence) | the **verification method** (generative gate + harness) | [verification-method](../verification-method/00-the-primitive.md) |
| the cycle **iterated** (serialize(N) → comprehend(N+1)) | the **lifecycle** (TRIAGE → … → RESOLVE, phases chained by artifacts) | AGENTS.md |
| the **measure** discipline (deterministic decidable signal) | the **engines** + `uacp-lint` (fail-closed structural checks) | graph-engine |
| the **routing** (decision/gate) | **Guardian / Heartgate** + per-phase authority | runtime-enforcement |

So the verification bundle's `00-the-primitive` is **this primitive seen through the verification phase**; the graph-engine bundle is **this primitive's serialize half built**. They are not three ideas — they are one primitive at three vantage points.

## The reframe (UACP's actual category)

If serialize has many targets ([03](03-serialize-targets.md)), then **UACP is an information-processing architecture, not a memory system.** Memory is one serialize-target; the knowledge graph, the event log, the audit trail, the search index are others. UACP's job is the *disciplined pipeline* ([04](04-trustless-differentia.md)); the stores are its outputs.

## Open: where this lands in the doctrine

- This bundle stays **pre-governance** until [05-validation-matrix](05-validation-matrix.md) clears.
- On clearing: a governed run promotes a neutral one-liner to AGENTS.md and graduates the per-phase mapping to `docs/`; the verification + graph-engine bundles then cite *up* to the ratified principle instead of restating it.

## To expand
- The full cross-walk: every CMS-bundle node → the UACP mechanism that realizes it.
- Whether non-UACP systems (Trustless ledger, deployment assessment) instantiate the *same* primitive — strengthening [05](05-validation-matrix.md).
- The "Memory is one output" consequence for how UACP is described publicly.
