---
type: design
title: The Investigation Ledger — the revisable, phase-rooted serialized trail
description: The investigation is itself a comprehend→measure→serialize loop, so its trail must be serialized too — a revisable, phase-rooted ledger of what was enumerated, generated, run, reconciled, revised, and escalated. Most of the substrate already exists (the goal-driven CHECKPOINT MANIFEST is a revisable phase-rooted move-trail); the net-new is a typed investigation-entry schema + a convergence loop that READS the ledger to decide dry-vs-keep-going.
tags: [verification, ledger, investigation, checkpoint-manifest, supersede, revisable]
timestamp: 2026-06-24
edges:
  - {dst: 00-the-primitive, rel: depends_on, provenance: derived}
---

# The Investigation Ledger

## Why it exists

The verification loop is itself `comprehend → measure → serialize`, so the **serialize discipline applies to the investigation itself** — *not just to the checks it authors*. The ledger is where each move (`enumerate / route / bind / run / reconcile / revise / escalate`) and each verdict is **frozen with provenance**, so the investigation is **auditable, resumable, and revisable** rather than a one-shot pass whose reasoning evaporates. This is [00-the-primitive](00-the-primitive.md)'s line — *the gate authors a check, freezes it, the harness replays it* — turned on the act of investigating: the trail of what was generated and why is itself serialized state, not ephemeral prose.

## Revisable + phase-rooted (not append-only-forever)

A finding can be **superseded** by a later one (with its history kept), a line of inquiry can **branch**, and a contradiction is first-class. Entries are **rooted to the phase** that produced them, so a run's verification history reads as a tree, not a flat log. This is not new lifecycle machinery: it is UACP's existing **node-lifecycle / supersede** rule (graph-engine D18, [decisions](../graph-engine/02-decisions.md)) applied to investigation entries — see [node-taxonomy](../graph-engine/11-node-taxonomy.md) for the identity/lifecycle rule a revisable entry inherits.

## What already exists (name the substrate — most of this is EXISTS, not propose)

The instinct "this needs new infra" is wrong. The substrate is built; the as-built names are:

- **A revisable, phase-rooted move-trail already ships** — the goal-driven track's **CHECKPOINT MANIFEST** (`engines/heartgate/goal_driven.py` → `load_checkpoint_manifest` [defined in `engines/io/loaders.py`] / `validate_goal_driven_checkpoint_gate`). It is exactly the proposed ledger's shape: each EXECUTE iteration is a `gate: CHECKPOINT` ledger record carrying a **verdict** (`keep` / `roll_back` / `restart`), bound to a `goal_id`, evidence-coupled, and read back as an ordered trail the gate walks to decide whether the run has converged on a `keep`. A `roll_back`/`restart` followed by a forward run *is* supersede-with-history. **This is the closest existing analogue of the investigation ledger — the design should extend it, not parallel it.**
- **The contradiction signal** the `reconcile` move consumes is `GP_CONTRADICTED` — `engines/manifest/projection.py::_check_contradicted` (real-data-bound via the shared `obligation_id` join after GN3; the `evidence_refs→checkpoint_id` path is the secondary join). See [projection-engine](../graph-engine/14-projection-engine.md) for the projection model.
- **The serialized store** the ledger extends is the **Manifest engine + gate-ledger**, not a parallel store: manifest entries are written through the typed, validated, watermarked write path (`engines/manifest/entity_writer.py::create_entity` + the `layout` registry), and the gate-ledger is the append-only `gate: …` record stream.
- **The append-only integrity** of that store is already enforced — `engines/ledger_integrity.py` validates monotonic `ts`, duplicate-transition-gate (`LI_DUPLICATE_GATE`), and per-record `run_id` consistency. (Note the asymmetry the design must respect: the *gate-ledger* is integrity-checked as **append-only**; the *revisable* tree is the manifest/entity layer above it, where supersede lives — the ledger never rewrites, the projection re-reads.)

## What's genuinely still to propose (the real gap — two net-new pieces)

The substrate exists; what does **not** yet exist is investigation-specific:

1. **A typed investigation-entry schema.** The CHECKPOINT manifest carries `verdict`/`evidence`/`goal_id` — it does not carry the *investigation* fields: **move-type** (`enumerate / route / bind / run / reconcile / revise / escalate`), a **ref to the generated measurement** the move produced (the frozen check from [00-the-primitive](00-the-primitive.md), not just the raw evidence path), an explicit **`supersedes`** pointer, and the verify verdict (`PASS / FAIL / ERROR`, fail-closed). This is `CheckpointEntry`'s sibling, scoped to the verify loop — net-new, but modeled on the existing entry + the existing supersede rule.
2. **A convergence loop that READS the ledger to decide "dry vs keep going."** The goal-driven gate already reads its manifest to decide *converged-on-a-keep vs not* against a `max_checkpoints` cap — but that is goal-completion, not investigation-exhaustion. The verify loop needs the analogous read: *has enumeration gone dry (no new unbound claim, no open contradiction) → stop; else generate the next check.* The cap mechanism and the manifest read are built; the **dry-predicate over investigation entries** is the new part.

## To expand
- The investigation-entry schema as a `CheckpointEntry` sibling (fields above), and where it is layout-registered for `entity_writer`.
- The exact dry-predicate (what "no new check is worth generating" means over the entry set) and how it composes with the existing `max_checkpoints` convergence cap.
- How an escalation (architecture verdict) is recorded as an entry and surfaced to the transition gate (reusing `uacp_escalation_event`, per [11-harness](11-harness.md)).

---

**Summary of changes (re-grounding 2026-06-24):** (1) Named the abstract substrate against as-built code — `GP_CONTRADICTED`→`projection.py::_check_contradicted`, gate-ledger+manifest→Manifest engine/`entity_writer.py`, integrity→`ledger_integrity.py` (monotonic-ts / dup-gate / run_id); D18 supersede + GP_CONTRADICTED now reference graph-engine nodes 02/11/14 instead of restating. (2) Biggest update: surfaced the goal-driven **CHECKPOINT MANIFEST** (`goal_driven.py::load_checkpoint_manifest`) as the already-shipping revisable phase-rooted move-trail — tipped "what exists vs propose" hard toward EXISTS. (3) Sharpened the real gap to two net-new pieces (typed investigation-entry schema; the dry-predicate convergence loop that reads the ledger), keeping the "serialize applies to the investigation itself" thesis and the revisable-NOT-append-only framing (now with the gate-ledger-append-only vs manifest-revisable asymmetry made explicit).
