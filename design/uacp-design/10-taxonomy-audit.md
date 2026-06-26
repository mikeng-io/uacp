---
type: analysis
title: As-built audit — the real bundle + node-type taxonomy (comprehend before serialize)
description: The grounded survey of the live design/ corpus — the 9 bundles, the 11 actual node `type:` values, and the structural violations already present (a non-conforming _index, type sprawl/duplication). Derives a CLOSED canonical node-type set from reality (not invented) and the reconciliation the lint's staged rollout must do — the lesson from the reverted graph-engine doc-kinds.
tags: [uacp-design, audit, taxonomy, as-built, grounding]
timestamp: 2026-06-26
edges:
  - {dst: 00-intent, rel: motivated_by, provenance: derived}
---

# As-built audit — the real taxonomy

## Why audit first

The graph-engine "doc-kinds" were once **invented** and had to be **reverted** because they were
spike-fictional, not grounded in the as-built. The rule (mike): *comprehend the taxonomy before
serializing it.* So the canonical node-`type` set below is **derived from the live corpus**, not
designed in a vacuum, and the lint enforces only what reality + the schema actually warrant.

## The corpus (survey 2026-06-26, `design/*/`)

**9 bundles:** `bridge-containment`, `codeflair`, `comprehend-measure-serialize`, `e2e-acceptance`,
`entrypoints`, `graph-engine`, `handoff`, `verification-method`, `work-unit-status`.

**`_index`:** 8 are `_index.yaml` with `kind: design_index`; **1 is an `_index.md`** (non-conforming —
the lone `.md`, surfacing as the one-off node-type `design-bundle-index`). → a real violation the lint
should catch (and the rollout must reconcile).

**Node `type:` values across all bundles (frequency):**

| type | count | disposition (proposed) |
|---|---|---|
| `analysis` | 47 | **canonical** |
| `design` | 20 | **canonical** |
| `contract` | 15 | **canonical** |
| `reference` | 7 | **canonical** |
| `design-node` | 4 | **alias → `design`** (duplicate; reconcile) |
| `pattern` | 2 | **canonical** |
| `decision` | 2 | **canonical** |
| `roadmap` | 1 | fold → `design` (a roadmap is design) OR keep — DECISION below |
| `lessons` | 1 | fold → `analysis` OR keep — DECISION below |
| `evidence` | 1 | fold → `analysis` OR keep — DECISION below |
| `design-bundle-index` | 1 | NOT a node type — it is the non-conforming `_index.md`; reconcile to `_index.yaml` |

## Derived canonical node-`type` set (proposed, closed)

`analysis | design | contract | reference | pattern | decision` — the six recurring, non-redundant
values. Reconcile `design-node → design`; convert the `_index.md` → `_index.yaml`. The three one-offs
(`roadmap`, `lessons`, `evidence`) are the **open taxonomy decision**: fold them into the six (a
roadmap/lessons/evidence node *is* design/analysis content) — RECOMMENDED, smallest closed set — or
admit them as canonical. Lean: fold; keep the set to six.

## What this means for the lint + rollout

- The lint validates node `type` against the closed set — but **only after** the corpus is reconciled
  (rename `design-node`→`design`, fix the `_index.md`, fold/keep the one-offs). Flipping the type
  check fail-closed before reconciling = a red wall.
- This is exactly why the rollout ([22](22-rollout-and-decisions.md)) is **reconcile-then-enforce**,
  not flip-and-break.

## To expand
- Confirm the per-bundle node-type usage (which bundle owns each one-off) before folding, so a fold
  doesn't lose a meaningful distinction.
- Verify the `_index.md` bundle's identity + convert it as the first reconciliation PR.
