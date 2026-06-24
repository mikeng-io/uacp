---
type: analysis
title: Codeflair — Core / UACP-Adapter Abstraction
description: The boundary that makes Codeflair work WITHOUT UACP. The core (SCIP/LSP/grep/co-change + store + loop + heatmap) is a standalone code-intelligence engine on any git repo; UACP plugs in as a thin adapter (manifest-graph probe + code_anchor join + governed-writer/Guardian wrapper). What you keep and lose without UACP, the seam (query API + probe registry), and the packaging.
tags: [codeflair, abstraction, standalone, uacp-adapter, boundary]
timestamp: 2026-06-24
edges:
  - {dst: 00-overview, rel: realizes, provenance: asserted}
---

# Codeflair — Core / UACP-Adapter Abstraction

**Requirement (CF-D9):** Codeflair must work **without UACP**. The code-intelligence value is not
UACP-specific — it is useful on any codebase — so UACP must be a *dependency of the adapter, never of the
core*.

## The two layers

| | **Core** (standalone — any git repo) | **UACP adapter** (only when embedded) |
|---|---|---|
| Probes | SCIP · LSP · grep · co-change | manifest-graph · `code_anchor` cross-plane join |
| Store | code-graph in a plain cache dir | (same store; path moved outside `.uacp/` governed roots) |
| Loop | expansion + prune (policy D/A/B/C) | unchanged |
| Output | heatmap: blast radius · code-side relations · structural gaps | + relation-plane nodes + cross-plane gaps ("what governs this code") |
| Writes | just writes its index — no gate | the governed-writer/Guardian-path preconditions ([01b](01b-store.md), [CF-D8](07-decisions.md)) |
| Identity | a code-intelligence engine (owns its store) | a calling skill (drivers sit above the ring, `29-ddd-ca-reference.md`) doing a query-time cross-plane join (D44:912) |
| Reasoning model | the expensive caller (any orchestrator) | the UACP run's orchestrator |

## What you keep / lose without UACP

- **Keep (the core):** symbol blast-radius, reference/call-hierarchy walking, co-change correlation,
  grep/LSP reconciliation, **code-side relations** (`defines`/`references`/`calls`/co-change), the
  heatmap, the replayable trace, the whole expansion-loop + benchmark, and **structural gaps** (e.g. a
  caller with no test). A bare-repo developer (or any agent) gets the full code-side value.
- **Lose (the adapter):** the cross-plane join — *which manifest intent governs this code*, *which code
  realizes this proposal* — the **manifest relations** (`derives_from`/work_unit) and the **cross-plane
  gaps** (no-manifest-anchor / orphan), and the governance integration (watermark-on-run, governed-writer
  wrapper). The heatmap simply carries no relation-plane nodes.

The eval seed-set is split the same way (`layer: core | uacp-adapter`) — see `eval/seed-set.yaml`
(PR #13); of the starter pairs only the cross-plane orphan is `uacp-adapter`.

## The seam (how the adapter plugs in)

- **A probe registry.** The loop ([03](03-expansion-loop.md)) iterates over a registered probe set. Core
  registers SCIP/LSP/grep/co-change; the UACP adapter *additionally* registers the manifest-graph +
  `code_anchor` probes. The loop, scoring, and stop-conditions are blind to which probes are present.
- **A stable query API + heatmap schema.** `query(seed, k, budget) → heatmap`. The schema is identical
  with or without UACP; the adapter only *adds* relation-plane node types when its probes are registered.
- **A storage-location hook.** Core writes its index to a plain cache dir; the UACP adapter relocates it
  outside `.uacp/`'s governed roots and supplies the run watermark. No core code knows about Guardian.

## Packaging implication (design intent; details to BUILD)

Ship the **core as a self-contained library/CLI** with no UACP import; ship the **UACP adapter as a
separate module** that depends on the core + UACP, registering the extra probes and the governance
wrapper. The dependency arrow points **adapter → core**, never the reverse. A core import of anything
UACP-specific is the litmus violation.
