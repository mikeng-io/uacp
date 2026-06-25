---
type: design
title: Layer 1 — the Harness (run / reconcile / loop / escalate)
description: The fixed activity — deterministic machinery that runs the frozen measurements, reconciles results, loops to convergence with adaptive depth, and escalates to an architecture verdict when fixes keep failing. The DETERMINISTIC pole of CMS (no comprehension lives here); same every time. Phase-agnostic machinery; wiring it at EXECUTE *checkpoints* (vs the built execute_exit gate) is the UPDATE. Mostly IMPROVISE/UPDATE of existing engines.
tags: [verification, harness, convergence, escalation, fixed-activity]
timestamp: 2026-06-24
edges:
  - {dst: 00-the-primitive, rel: realizes, provenance: asserted}
---

# Layer 1 — the Harness

## What it is

The **fixed activity**: dumb, deterministic machinery that consumes the measurements the [generative gate](10-generative-gate.md) produced and drives them to a verdict. **No comprehension lives here — that is the whole point.** This is the **deterministic pole** of CMS: the gate comprehends-and-freezes a check *once*; the harness *replays* it, forever — exactly the "determinism belongs to the verifying gate, not the agent's judgment" relocation ([00](00-the-primitive.md); CMS [11-measure](../comprehend-measure-serialize/11-measure.md), [25-enforcement-surfaces](../comprehend-measure-serialize/25-enforcement-surfaces.md)).

The machinery is **phase-agnostic** — the same sweep runs at any transition gate. Today it is wired at the phase exits (the running half of the gate, which EXECUTE is *not* excluded from — see [00](00-the-primitive.md)).

## The fixed moves — and what each maps to

Almost everything here is an **existing symbol**. The only genuine BUILD is the convergence controller and the escalation-*verdict* trigger (and even the controller IMPROVISES existing machinery — see LOOP).

- **RUN** — replay each serialized measurement fail-closed (PASS/FAIL/ERROR distinct; ERROR ≠ PASS — closes #503 class A). This *is* `run_all_engines` (`engines/base.py:41`) over the registered `ENGINES`: the shared `Engine`/`Violation` protocol (block/warn severity), each engine wrapped so an unexpected raise becomes an `ENGINE_CRASHED` **block** rather than a silent pass. The Heartgate hub already calls it: `validate_closure` → `run_all_engines` (`engines/heartgate/heartgate.py`).
- **RECONCILE** — collate results, dedup overlapping findings, detect contradiction. This is the reconciling engines run by RUN, read together: `GP_CONTRADICTED` (`engines/manifest/projection.py`, `_check_contradicted`) + `evidence_completeness.py` (the "no self-attesting closure" EV_ checks) + coherence **C2** (`engines/coherence.py` — `state_history` ↔ gate-ledger agreement). `GP_CONTRADICTED` is now **FULLY binding on real producer output**: it joins a `pass` assessment to a `block` evidence item via the shared `obligation_id` (remediation-aware), so it fires on what the PIV producer actually emits — closing the "join gap" the 2026-06-21 sketch flagged (the GN3 work; D42). The dedup is already there in kind: `_check_contradicted` flags **per assessment** across both join paths.
- **LOOP (convergence)** — re-enter the investigation with **adaptive depth**: keep generating+running until K consecutive rounds surface nothing new (loop-until-dry), not a fixed pass count. This is the one **new controller** — but it should **IMPROVISE the existing goal-driven convergence machinery**, not build from zero: `engines/heartgate/goal_driven.py` already counts `gate: CHECKPOINT` ledger entries against a `max_checkpoints` budget across a goal's whole run-chain (`goal_checkpoint_count` + `validate_goal_driven_checkpoint_gate`). The controller's "rounds" are checkpoints; its cap is that budget; "converged on a keep" is already that gate's final-verdict rule.
- **ESCALATE** — the stop rule: when ≥N fixes fail to move the verdict, stop patching symptoms and **emit an architecture verdict** — "the design, not the code, is wrong." The *writer* exists (`uacp_escalation_event` in `skills/uacp-state/scripts/state.py`, schema'd by `engines/domain/escalation.py` — `EscalationRecord`: mode/trigger/severity/reason/authority_artifact). The **new** part is purely the *verdict trigger*: the rule that decides the threshold was crossed and calls it.

## Wiring point

The harness hangs off the **Heartgate hub** (`engines/heartgate/heartgate.py`): `validate_closure` already runs the full sweep at closure, and `validators/phase_exit.py` already runs the **phase-keyed structural subset** at each transition via `validate_graph_invariants(..., "<from_phase>_exit")` (D35 — `plan_exit` / `execute_exit` / `verify_exit`), turning block-severity violations into transition blockers. So RUN/RECONCILE are already wired at the phase exits; LOOP and the ESCALATE verdict-trigger are what attach to this same hub.

> **Path note:** the projection engine now lives at `engines.manifest.projection`; `engines/graph_projection.py` is a **re-export shim** (it re-exports `validate_graph_projection` / `validate_graph_invariants` and triggers the `ENGINES` self-registration on import). Both import spellings work.

## The architecture-verdict escalation (UACP-native, NOT "Phase 4.5")

The systematic-debugging idea of "3+ failed fixes → question the architecture" becomes a **first-class, UACP-named** escalation, wired to the existing `uacp_escalation_event` writer — not a magic phase number. It produces a serialized `EscalationRecord` the [ledger](13-investigation-ledger.md) records and a transition gate can consume.

## What is genuinely new vs. existing

- **Existing (IMPROVISE/UPDATE):** RUN = `run_all_engines`; RECONCILE = `GP_CONTRADICTED` + `evidence_completeness` + coherence C2; the escalation *writer*; the convergence *substrate* (`goal_driven.py`'s checkpoint count + budget cap + final-keep rule); the wiring surface (`heartgate.py` + `phase_exit.py`).
- **New (BUILD):** the convergence **controller** (dry-rounds K, escalate-threshold N, how depth adapts to phase + risk) — built *on* the goal-driven machinery, not beside it — and the escalation **verdict trigger** (the rule that fires `uacp_escalation_event` when ≥N rounds fail to move the verdict).
- **UPDATE (the honest gap):** the machinery is phase-agnostic and runs at `execute_exit`, but it is **not yet wired at intra-EXECUTE *checkpoint* granularity**. Running the loop *between* EXECUTE iterations (vs only at the built `execute_exit` gate) is the wiring UPDATE — the goal-driven track already records per-iteration checkpoints, so the hook exists; what's missing is driving the sweep off each one.

## To expand
- The convergence controller's exact stop conditions (dry-rounds K, escalate-threshold N) and how depth adapts to phase + risk — expressed in terms of the goal-driven checkpoint budget it IMPROVISES.
- The reconcile dedup algorithm (cross-finder, cross-round) and how it avoids re-surfacing judge-rejected findings — building on `_check_contradicted`'s per-assessment dedup.
- The intra-EXECUTE-checkpoint wiring (the UPDATE): driving RUN/RECONCILE off each goal-driven checkpoint, not only at `execute_exit`.
