---
type: design
title: Layer 1 — the Harness (run / reconcile / loop / escalate)
description: The fixed activity — deterministic machinery that runs the frozen measurements, reconciles results, loops to convergence with adaptive depth, and escalates to an architecture verdict when fixes keep failing. Same every time; runs everywhere including EXECUTE checkpoints. Mostly IMPROVISE/UPDATE of existing engines.
tags: [verification, harness, convergence, escalation, fixed-activity]
timestamp: 2026-06-21
edges:
  - {dst: 00-the-primitive, rel: realizes, provenance: asserted}
---

# Layer 1 — the Harness

## What it is

The **fixed activity**: dumb, deterministic machinery that consumes the measurements the [generative gate](10-generative-gate.md) produced and drives them to a verdict. No comprehension lives here — that is the whole point. It runs **everywhere, including EXECUTE checkpoints** (the running half of the gate that EXECUTE is *not* excluded from — see [00](00-the-primitive.md)).

## The fixed moves

- **RUN** — replay each serialized measurement fail-closed (PASS/FAIL/ERROR distinct; ERROR ≠ PASS — closes #503 class A). Built on the existing `run_all_engines`.
- **RECONCILE** — collate results, dedup overlapping findings, detect contradiction (reuse `GP_CONTRADICTED` + `evidence_completeness`).
- **LOOP (convergence)** — re-enter the investigation with **adaptive depth**: keep generating+running until K consecutive rounds surface nothing new (loop-until-dry), not a fixed pass count.
- **ESCALATE** — the stop rule: when ≥N fixes fail to move the verdict, stop patching symptoms and **emit an architecture verdict** — "the design, not the code, is wrong."

## The architecture-verdict escalation (UACP-native, NOT "Phase 4.5")

The systematic-debugging idea of "3+ failed fixes → question the architecture" becomes a **first-class, UACP-named** escalation, wired to the existing `uacp_escalation_event` writer — not a magic phase number. It produces a serialized escalation artifact the [ledger](13-investigation-ledger.md) records and a transition gate can consume.

## To expand
- The convergence controller's exact stop conditions (dry-rounds K, escalate-threshold N) and how depth adapts to phase + risk.
- The reconcile dedup algorithm (cross-finder, cross-round) and how it avoids re-surfacing judge-rejected findings.
- Wiring: which existing engines map to RUN/RECONCILE, and what is genuinely new.
