---
type: design
title: The uacp-design skill — the judgment layer
description: The uacp-design SKILL (kind reference, authored per uacp-skills/ADR-0017) — what it teaches that a lint cannot decide — the decomposition discipline, the frontmatter/edge shape, the reference boundary, the Status/Checkpoint pattern, and the design-review anti-patterns. The comprehension half of the split.
tags: [uacp-design, skill, judgment, convention, adr-0017]
timestamp: 2026-06-26
edges:
  - {dst: 00-intent, rel: realizes, provenance: asserted}
  - {dst: 10-taxonomy-audit, rel: depends_on, provenance: derived}
---

# The uacp-design skill — the judgment layer

## What it is

A `kind: reference` meta-skill (authored per `uacp-skills` / ADR-0017, self-contained, OKF
frontmatter) — UACP's analog of skill-creator, but for **design bundles**. It carries the half of the
convention a lint cannot decide: **how to author a *good* bundle**, not just a *well-formed* one.

## What it teaches (the non-decidable half)

- **Decompose, don't monolith** — a design is a bundle of facet nodes + an `_index`, each node one
  concern; never a single doc, never `docs/plans` (placement is lint-checked, but *what to split and
  where the seams go* is judgment). One concern per node; the `_index` is the reading order + the
  inter-node graph.
- **The node shape** — frontmatter (`type` from the closed set [10](10-taxonomy-audit.md),
  `title`, `description`, `tags`, `timestamp`, `edges`), and the `edges` graph (each node declares its
  own out-edges; the `_index` mirrors them — the lint enforces the mirror, the skill teaches *which
  edges mean what*: `realizes` / `depends_on` / `motivated_by` / `decides_on` / `sequences` / …).
- **The reference boundary** — a design bundle references peer bundles + the as-built; it does not
  duplicate them (single-source). When a concept lives in another bundle, link it, don't restate it.
- **The Status/Checkpoint pattern** — a dated block (and an `_index` status line) recording built-vs-
  parked, linked to its PRs/commits, so a bundle carries its own state. Skill-RECOMMENDED, not lint-
  required ([22](22-rollout-and-decisions.md)).
- **The design-review anti-patterns** (the loops to avoid when councilling a design):
  - *propagation* — point-fixing one flagged copy of a concept restated in N nodes (fix the single
    source + sweep the set);
  - *over-serialization* — pre-resolving BUILD detail in prose instead of letting tests arbitrate at
    build (a design states the model + decisions, not the implementation).

## What it does NOT own

The decidable structure ([21](21-lint.md)) — schema conformance, members==files, edges-mirror, ≥2
nodes, placement, valid `type`. The skill points at the lint; it does not re-implement it (its own
single-source rule).

## To expand
- The exact SKILL.md sections + the progressive-disclosure split (a lean SKILL.md + references), per
  uacp-skills.
- Whether `uacp-brainstorm` invokes this skill at the brainstorm→design crystallization point.
