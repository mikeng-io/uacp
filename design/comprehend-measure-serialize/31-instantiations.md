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
| **serialize** discipline (typed key + provenance, idempotent canonical form) | the **graph engine** — `graph_projection` + the entity-writer **BUILT + merged to main** (`uacp-lint` / `uacp-fmt` designed, not yet built) | [graph-engine](../graph-engine/00-overview.md) |
| the **loop** (comprehend → measure → serialize, to convergence) | the **verification method** (generative gate + harness) — *planned sibling bundle, not on this branch* | verification-method (planned) |
| the cycle **iterated** (serialize(N) → comprehend(N+1)) | the **lifecycle** (TRIAGE → … → RESOLVE, phases chained by artifacts); the per-phase CMS triple | [24-phase-crosswalk](24-phase-crosswalk.md) |
| the **measure** discipline (**grounded** decidable signal — *determinism in the verifying gate*) | the **agent grounds** (cognition) + the **engines / `uacp-lint`** check fail-closed (the gate half) | [25-enforcement-surfaces](25-enforcement-surfaces.md) |
| the **routing** (decision/gate) | **Guardian / Heartgate** + per-phase authority | runtime-enforcement |
| the two **enforcement surfaces** (architecture + cognition) | gates + governed writers / the injected `UACP.md` | [25-enforcement-surfaces](25-enforcement-surfaces.md) |

So the verification bundle's `00-the-primitive` is **this primitive seen through the verification phase**; the graph-engine bundle is **this primitive's serialize half built**. They are not three ideas — they are one primitive at three vantage points.

## The reframe (UACP's actual category)

If serialize has many targets ([03](12-serialize.md)), then **UACP is an information-processing architecture, not a memory system.** Memory is one serialize-target; the knowledge graph, the event log, the audit trail, the search index are others. UACP's job is the *disciplined pipeline* ([04](22-differentia.md)); the stores are its outputs.

## Status in the doctrine (PROMOTED 2026-06-24)

- CMS is **ratified** — [ADR-0018](../../docs/architecture/0018-cms-semantic-thinking-principle.md) — and stated in **AGENTS.md** ("Core Principle"); the cognition-injection mechanism is **built** ([25-enforcement-surfaces](25-enforcement-surfaces.md)).
- The per-phase mapping is the cross-walk in [24-phase-crosswalk](24-phase-crosswalk.md). The verification + graph-engine bundles should cite *up* to the ratified principle rather than restate it.
- Remaining: cross-runtime injection (Kimi / opencode); merge this bundle to main.

## To expand
- The full per-phase cross-walk now lives in [24-phase-crosswalk](24-phase-crosswalk.md); extend it to *every* CMS-bundle node → the UACP mechanism that realizes it.
- Whether non-UACP systems (Trustless ledger, deployment assessment) instantiate the *same* primitive — strengthening [05](30-validation-matrix.md).
- The "Memory is one output" consequence for how UACP is described publicly.
