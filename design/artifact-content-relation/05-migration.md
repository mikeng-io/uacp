---
type: design
title: "Migration — additive ratchet, not cutover"
description: "Describes the staged additive migration strategy: anchor is added as optional, YAML prose fields stay valid as legacy, each ratchet stage is independently shippable and reversible. Hard cutover is rejected."
tags: [migration, ratchet, additive, backward-compatible, design, staged]
timestamp: 2026-06-30
edges:
  - {dst: 03-anchor-primitive, rel: depends_on, provenance: asserted}
---
# 05 — Migration: additive ratchet, not cutover

## The lever
The whole cost profile turns on one choice.

- **Additive ratchet (chosen).** Add `anchor` to the schema (optional). Add the MD-section
  binding mode to `field_present`. Keep YAML prose fields (`statement`, `objective`) valid
  but *optional/legacy*. New artifacts use anchors; old artifacts still validate. Coverage is
  **added**, not rewritten — the existing 18 tests mostly keep passing; new tests cover the
  anchor path. This is UACP's own established shape (validate-on-write ratchet, schema ratchet).

- **Hard cutover (rejected).** Remove prose from YAML now → rewrite all 18 tests, migrate
  in-flight on-disk runs, breaking change. No upside that the ratchet doesn't get more safely.

## Ratchet stages (design-level; build sequences them)
1. **Add anchors (inert).** Schema accepts `anchor`; projection records `anchored_to`. Nothing
   requires it yet. Zero behavior change.
2. **Teach the check.** `field_present` learns the anchor binding mode (opt-in per check).
3. **Author with anchors.** Lifecycle skills start authoring anchored content (MD home + YAML
   anchor) for new runs. Prose-in-YAML still tolerated.
4. **Tighten per kind.** Once a kind's producers/consumers are all anchor-aware, make the
   anchor the floor for that kind (per-kind ratchet, exactly like validate-on-write grew).
5. **(Optional, much later) retire legacy prose fields** once no producer emits them.

## No eager run migration
In-flight on-disk runs (hnp-20260628, etc.) are NOT rewritten. They validate under the legacy
optional-prose path. Migration is opt-in per new run.

## Why staged matters
Each stage is independently shippable and reversible, and each keeps the suite green. The
boundary redesign never lands as one big bang.
