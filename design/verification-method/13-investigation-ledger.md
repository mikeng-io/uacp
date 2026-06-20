---
type: design
title: The Investigation Ledger — the revisable, phase-rooted serialized trail
description: The investigation is itself a comprehend→measure→serialize loop, so its trail must be serialized too — a revisable, phase-rooted ledger of what was enumerated, generated, run, reconciled, revised, and escalated. Reuses D18 supersede + GP_CONTRADICTED + the gate-ledger; makes the investigation auditable and resumable.
tags: [verification, ledger, investigation, d18, supersede, revisable]
timestamp: 2026-06-21
edges:
  - {dst: 00-the-primitive, rel: depends_on, provenance: derived}
---

# The Investigation Ledger

## Why it exists

The verification loop is itself `comprehend → measure → serialize`, so the **serialize discipline applies to the investigation too**: its reasoning trail cannot be ephemeral prose. The ledger is where each move (`enumerate/route/bind/run/reconcile/escalate`) is recorded as a typed entry — so the investigation is **auditable, resumable, and revisable**, not a one-shot pass.

## Revisable + phase-rooted (not append-only-forever)

It borrows from sequential-thinking's *revise/branch* and UACP's **D18 node lifecycle / supersede**: an earlier finding can be **superseded** by a later one (with provenance), a line of inquiry can **branch**, and contradictions are first-class (`GP_CONTRADICTED`). Entries are **rooted to the phase** that produced them (phase-parameterized), so a run's verification history reads as a tree, not a flat log.

## What it reuses (IMPROVISE, not new infra)
- **D18 supersede** — revision/replacement of findings with a kept history.
- **`GP_CONTRADICTED`** — the contradiction signal the reconcile move consumes.
- **the gate-ledger + manifest** — the existing serialized state the ledger extends, rather than a parallel store.

## To expand
- The ledger entry schema (move type, target, generated-measurement ref, verdict, supersedes, provenance, phase).
- How the convergence loop reads the ledger to decide "dry" vs "keep going."
- How an escalation (architecture verdict) is recorded and surfaced to the transition gate.
