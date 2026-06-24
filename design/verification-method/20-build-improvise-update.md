---
type: roadmap
title: BUILD vs IMPROVISE vs UPDATE — the decomposition
description: The granular scoping map the whole bundle sequences toward — which parts to BUILD new, which to IMPROVISE from existing engines, which to UPDATE in place. Re-grounded against the as-built engine landscape (engines/ + engines/manifest/ + goal-driven convergence + D35 graph_invariant gates), which has since absorbed most of what this node once called BUILD. UACP-native naming (no "Phase 4.5"). Each item points to the node that specifies it.
tags: [verification, roadmap, build-improvise-update, scoping]
timestamp: 2026-06-24
edges:
  - {dst: 00-the-primitive, rel: sequences, provenance: asserted}
---

# BUILD vs IMPROVISE vs UPDATE

The method is **mostly assembly of existing UACP engines** under the [primitive](00-the-primitive.md); the genuinely-new surface is small — and **smaller now than when this node was first written.** Since then the kernel grew the Manifest engine (`engines/manifest/`), the engine registry + sweep (`run_all_engines` / `ENGINES`), the goal-driven convergence machinery, the `uacp_escalation_event` writer, and the D35 phase-keyed `graph_invariant` exit gates — so several items once scoped BUILD are now IMPROVISE or UPDATE. Granular, UACP-native — no "Phase 4.1/4.5".

> **As-built note.** Two validation surfaces coexist: the offline single-script validator `scripts/validate_uacp_artifacts.py` **still exists and is Heartgate-wired** (`engines/heartgate/heartgate.py:473` invokes it; the per-kind schema registry `engines/domain/schema.py` is **derived from** its `validate_*` functions) — and the **run-time engine registry** `run_all_engines` sweeping `ENGINES` (`artifact_integrity`, `coherence`, `deferral_completeness`, `evidence_completeness`, `graph_projection`→`engines.manifest.projection`, `ledger_integrity`, `scope_conformance`), which the kernel grew alongside it. (The anticipated "uacp-lint" *rename* of the offline validator never landed — it is still `validate_uacp_artifacts.py`.) The substrate Layer 1 (the [harness](11-harness.md)) runs on is that engine registry. For the engine inventory and what each owns, see graph-engine [node 28 — component-registry](../graph-engine/28-component-registry.md) and [node 34 — manifest-engine](../graph-engine/34-manifest-engine.md); this node does not re-list them inline.

## BUILD (new — the generative half, Layer 2)

This is where the real net-new lives: the [generative gate](10-generative-gate.md) — the generator and the moves that route/loop on its output. Two former BUILD items have **shed mass** into existing substrate; the table records what is still genuinely new vs. what merely sits on top of an engine that now exists.

| Item | What is actually new | Spec node |
|---|---|---|
| **Assertion schema/kinds** (typed serialized measurements) | BUILD the schema into `engines/domain/schema.py` — the typed assertion/investigation-entry kinds | [10](10-generative-gate.md) |
| **Assertion runner** (replay frozen checks) | **IMPROVISE onto `run_all_engines`** — the runner substrate (`engines/base.py`, the `Engine`/`Violation` contract, the defensive sweep) already exists; net-new is only registering generated assertions as Checks | [11](11-harness.md) |
| **Reality binder (BIND)** | **PARTLY IMPROVISE.** `artifact_integrity` + the Manifest engine's layout-registry (`entity_writer`) + `manifest.projection` already bind `kind → real path` and `assessment → obligation → checkpoint` on real data. BUILD only the **symbol/infra BIND** — and that waits on the deferred code/SCIP plane | [10](10-generative-gate.md) |
| **Predicate router (ROUTE by provenance D17/D23)** | **STILL BUILD.** No router engine exists; provenance today is *data on edges*, not a dispatcher that selects a check by it | [10](10-generative-gate.md) |
| **Convergence controller (loop-until-dry, adaptive depth)** | **BUILD-ON-IMPROVISE.** Extend the goal-driven convergence machinery (`engines/heartgate/goal_driven.py` — it already counts `CHECKPOINT` entries across a goal's run-chain against a declared budget). Net-new is the verify-mode loop policy, not the counter | [11](11-harness.md) |
| **Architecture-verdict escalation** | **IMPROVISE.** The `uacp_escalation_event` writer already exists (state.py `_handle_uacp_escalation_event`, with `trigger`/`severity`/`reason`/`mode`) plus the `engines/domain/escalation.py` engine. Net-new is only the **verdict-trigger** that fires it | [11](11-harness.md) |
| **Council generative-gate method** | **UPDATE, not BUILD** — `skills/uacp-council/` is already built; this teaches it the generative-gate method (incl. default-to-refute) | [14](14-council-method.md) |

## IMPROVISE (exists — re-aim it)
| Existing piece | New role | Spec node |
|---|---|---|
| `graph_projection` (now a re-export shim → `engines.manifest.projection`) | **ENUMERATE** (targets from the manifest projection) | [10](10-generative-gate.md) |
| provenance taxonomy (D17/D23) | feed ROUTE (the *data*; the router itself is BUILD) | [10](10-generative-gate.md) |
| `GP_CONTRADICTED` + `evidence_completeness` | RECONCILE | [11](11-harness.md) |
| `artifact_integrity` + watermark | BIND / audit | [10](10-generative-gate.md) |
| the `ENGINES` registry + `run_all_engines` | RUN (structural runners) | [11](11-harness.md) |
| D18 supersede + gate-ledger + `engines/manifest/` (the Manifest engine: `entity_writer` write-model + `projection` read-side) | the investigation ledger | [13](13-investigation-ledger.md) |

## UPDATE (extend in place)
| Target | Change | Spec node |
|---|---|---|
| D35 phase-keyed `graph_invariant` exit gates | **already wired** as exit invariants in `engines/domain/phase_transitions.py` (~:231–245, scope key `<from_phase>_exit`), consumed by Heartgate `_validate_phase_exit_invariants`. The UPDATE is **carrying a verification *profile* payload into the existing gate** — not wiring the gate | [12](12-phase-profiles.md) |
| Heartgate `validate_transition` | run the phase's profile at each transition (the exit-invariant hook already fires here) | [12](12-phase-profiles.md) |
| `uacp-council` / `uacp-debate` skills | the generative-gate council method (built skills, taught the method) | [14](14-council-method.md) |
| naming pass | UACP-native names for the moves/escalation | [00](00-the-primitive.md) |

## What the genuine net-new reduces to

Strip the assembly and the irreducibly-new surface is six things:

1. **the generator** — comprehend→measure that authors the assertion (the one semantic touch);
2. **the predicate router** — ROUTE-by-provenance dispatch (no engine for it today);
3. **the convergence controller** — loop-until-dry, built *on top of* goal-driven, not reinvented;
4. **the typed investigation-entry schema** — the assertion/entry kinds in `engines/domain/schema.py`;
5. **the default-to-refute council rule** — the council's generative-gate posture;
6. **the structural per-phase generate-exclusion** — EXECUTE cannot author its own measurements ([00](00-the-primitive.md), the no-self-attestation guarantee).

Everything else is re-aiming an engine that already ships.

## To expand
- **Slice ordering** — see graph-engine [node 20 — slices & infra readiness](../graph-engine/20-slices-readiness.md) for the shippable-first method; here the likely first slice is **VERIFY-profile + harness over the existing engine sweep**, then the generator, then the router.
- The failure-class → closing-item matrix (each #503 class in [01](01-evidence-503.md) → the BUILD/IMPROVISE/UPDATE item that closes it).

---

**Changes (re-grounding, 2026-06-21 → 2026-06-24):**
- BUILD shrank: assertion item split (schema=BUILD into `engines/domain/schema.py`, runner=IMPROVISE onto `run_all_engines`); reality-binder now partly-IMPROVISE (Manifest engine already binds on real data); escalation→IMPROVISE (`uacp_escalation_event` exists); council→UPDATE (built); convergence→build-on-IMPROVISE (goal-driven). Only the predicate router stays pure-BUILD.
- IMPROVISE/UPDATE re-grounded to current paths: `graph_projection` is a shim → `engines.manifest.projection` (ENUMERATE); ledger substrate named as `engines/manifest/` + `entity_writer`; D35 gates are **already wired** as `graph_invariant` exit invariants, so the UPDATE is the *profile payload*, not the wiring.
- Replaced inline engine listing with references to graph-engine nodes 28/34/20, and recorded the `validate_uacp_artifacts.py`→engines decomposition (`run_all_engines`/`ENGINES`, no future single uacp-lint script); added the "net-new reduces to six" summary that sharpens the unchanged thesis.
