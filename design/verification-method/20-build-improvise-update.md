---
type: roadmap
title: BUILD vs IMPROVISE vs UPDATE — the decomposition
description: The granular scoping map the whole bundle sequences toward — which parts to BUILD new, which to IMPROVISE from existing engines, which to UPDATE. UACP-native naming (no "Phase 4.5"). Each item points to the node that specifies it.
tags: [verification, roadmap, build-improvise-update, scoping]
timestamp: 2026-06-21
edges:
  - {dst: 00-the-primitive, rel: sequences, provenance: asserted}
---

# BUILD vs IMPROVISE vs UPDATE

The method is mostly *assembly of existing UACP pieces* under the [primitive](00-the-primitive.md); the genuinely new surface is small. Granular, UACP-native — no "Phase 4.1/4.5".

## BUILD (new — the generative half, Layer 2)
| Item | Spec node |
|---|---|
| Assertion model + deterministic runner (serialized measurements) | [10](10-generative-gate.md) |
| Reality binder (BIND: spec → real artifact/symbol/infra) | [10](10-generative-gate.md) |
| Predicate router (ROUTE by provenance D17/D23) | [10](10-generative-gate.md) |
| Convergence controller (loop-until-dry, adaptive depth) | [11](11-harness.md) |
| Architecture-verdict escalation (native, → `uacp_escalation_event`) | [11](11-harness.md) |
| Council generative-gate method | [14](14-council-method.md) |

## IMPROVISE (exists — re-aim it)
| Existing piece | New role | Spec node |
|---|---|---|
| `graph_projection` | ENUMERATE (targets from the manifest) | [10](10-generative-gate.md) |
| provenance taxonomy (D17/D23) | ROUTE | [10](10-generative-gate.md) |
| `GP_CONTRADICTED` + `evidence_completeness` | RECONCILE | [11](11-harness.md) |
| `artifact_integrity` + watermark | BIND / audit | [10](10-generative-gate.md) |
| the engines + `run_all_engines` | RUN (structural runners) | [11](11-harness.md) |
| D18 supersede + gate-ledger + manifest | the investigation ledger | [13](13-investigation-ledger.md) |

## UPDATE (extend in place)
| Target | Change | Spec node |
|---|---|---|
| D35 phase-keyed gates | carry a verification *profile*; invoke the loop with it | [12](12-phase-profiles.md) |
| Heartgate `validate_transition` | run the phase's profile at each transition | [12](12-phase-profiles.md) |
| `uacp-council` / `uacp-debate` skills | the generative-gate council method | [14](14-council-method.md) |
| naming pass | UACP-native names for the moves/escalation | [00](00-the-primitive.md) |

## To expand
- Slice ordering (what is shippable first; likely VERIFY-profile + harness over the existing engines, then the generative gate).
- The failure-class → closing-item matrix (each #503 class in [01](01-evidence-503.md) → the BUILD/IMPROVISE item that closes it).
