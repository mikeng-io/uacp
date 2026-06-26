---
type: design
title: Intent — the design-bundle convention, gated by decidability
description: What uacp-design is and why; the comprehend->measure->serialize split that decides what is enforced by a SKILL (judgment) vs a LINT (decidable structure); why guidance-only has empirically failed; and why this is a dedicated meta-skill, not part of uacp-brainstorm.
tags: [uacp-design, convention, meta, skill, lint, comprehend-measure-serialize]
timestamp: 2026-06-26
edges: []
---

# Intent — the design-bundle convention, gated

## In one sentence

A UACP design is a **decomposed bundle** under `design/<topic>/` (facet nodes + an `_index`), and
`uacp-design` makes that convention **hold** — by splitting it the way UACP splits everything:
**comprehend → measure → serialize**.

## The problem (why this exists)

"Design = decomposed bundle, never a single doc, never `docs/plans`" is a *documented* convention
(`CONTRIBUTING.md`, the `design_index` schema, a memory note) — and it has been violated **100+
times**, including by this agent. That is the empirical proof that **guidance-only does not hold**.
And UACP's own thesis says why: *determinism belongs to the gate, not the agent's judgment.* Relying
on the author to remember the convention is the self-attestation pattern UACP exists to kill. The
as-built audit ([10](10-taxonomy-audit.md)) confirms drift in the live corpus (a non-conforming
`_index`, an 11-value node-`type` sprawl).

## The split — what's a SKILL vs what's a LINT (by DECIDABILITY)

| | Owner | Covers | Mechanism |
|---|---|---|---|
| **STRUCTURE** (decidable) | the **LINT** ([21](21-lint.md)) | `_index` validates the schema; `members == files`; edges mirror node frontmatter; ≥2 nodes + `_index` (a real bundle, not a single doc); under `design/<topic>/` not `docs/plans`; node frontmatter has required fields + a valid `type` | a deterministic gate in `uacp-lint`, fail-closed (staged — [22](22-rollout-and-decisions.md)) |
| **JUDGMENT** (not decidable) | the **SKILL** ([20](20-skill.md)) | decomposition quality, no over-serialization, single-source-not-propagation, the Status/Checkpoint discipline, the reference boundary | taught by the skill; reviewed by council |

This is literally CMS turned on design docs: the **skill** carries the *comprehension* (how to author
a good bundle), the **lint** is the *measure* (the decidable shape), and a valid bundle is the
*serialized* result. A schema cannot catch "this is over-serialized"; the author cannot be trusted to
remember "≥2 nodes, under design/." So each gets the half it can actually own.

## Why a dedicated skill, not inside uacp-brainstorm

`uacp-skills : skills :: uacp-design : design-bundles` — and like `uacp-skills`, it is a **skill paired
with hard lints**, not skill-only. It is NOT folded into `uacp-brainstorm` because brainstorm is a
**per-run lifecycle phase** producing a transient scope package, whereas design bundles are **durable,
cross-run architecture** that is maintained outside any one run (this very bundle, and the
Status/Checkpoint we add to old ones, are not brainstorm runs). `uacp-brainstorm` *references*
`uacp-design` when a brainstorm crystallizes into a bundle; it does not own the convention.

## To expand
- The precise authority chain vs `CONTRIBUTING.md` (consolidate the design-placement policy into the
  skill, reference not duplicate) — single-source per the skill's own anti-propagation rule.
