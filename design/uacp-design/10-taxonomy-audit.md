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

**10 bundles** (incl. `uacp-design` itself): `bridge-containment`, `codeflair`, `comprehend-measure-
serialize`, `e2e-acceptance`, `entrypoints`, `graph-engine`, `handoff`, `uacp-design`, `verification-
method`, `work-unit-status`.

> **The inventory is NOT frozen here — it is the lint's REPORT mode.** A prose frequency table rots
> (a first draft of this node already drifted *and missed `type: prompt`*). So the canonical,
> re-derivable inventory is produced by the lint in report mode ([21](21-lint.md);
> [22](22-rollout-and-decisions.md) step REPORT) — this node records only the *shape* + the *decisions*.

### A node is TOP-LEVEL; nested files are SUB-ASSETS (the file model)

A bundle's **nodes** are its **top-level `*.md`** (excluding `_index*`). Nested `*.md` under a subdir
are **sub-assets, NOT nodes** — confirmed in the corpus: `comprehend-measure-serialize/prompts/` (7
files, `type: prompt`), `codeflair/eval/README.md` (typeless). This one distinction resolves two
would-be lint false-positives at once: `members == files` is **top-level-only** ([21](21-lint.md)
check 2), and the node-`type` vocabulary does **not** include sub-asset types like `prompt` (out of
node scope). The schema's `members` pattern (no `/`) already implies top-level-only — we make it explicit.

### Node `type:` values (the SHAPE, not frozen counts)

Across **top-level nodes**: a recurring CORE — `analysis`, `design`, `contract`, `reference`,
`decision`, `pattern` — plus a duplicate (`design-node`, reconcile → `design`) and a few one-offs
(`roadmap`, `lessons`, `evidence`). Among **sub-assets**: `prompt` (nested; out of node scope).
`design-bundle-index` is NOT a node type — it is `work-unit-status/_index.md` (see below).

## Derived node-`type` set — CORE derived, vocabulary NOT closed in v1

CORE (derived, recurring): `analysis | design | contract | reference | decision | pattern`. Reconcile
`design-node → design`. The one-offs (`roadmap`, `lessons`, `evidence`) are **deferred, not folded**:
the framework's own thesis is *evidence, not assertion*, so collapsing `evidence`→`analysis` would
erase the distinction it cares about most — folding is the wrong default. So the lint's type check is
**two-tier** ([21](21-lint.md) check 5): **hard-fail** on missing/malformed `type`; **warn-only** on
an unknown value against an allowlist (CORE + the known one-offs). **Closing** the vocabulary is a
*later* decision, taken only after the REPORT pass surveys the corpus — not asserted here.

## The hardest reconcile: `work-unit-status/_index.md` is a RECONSTRUCT, not a rename

It is not merely a `.md`-extension slip. As-built it has **no `kind: design_index`, no `members`, no
`edges`** — a single-doc-shaped index (`type: design-bundle-index`). So the lint's `_index` parse must
be **fail-closed against absent keys** (report a clean violation, not crash), and the reconcile pass
must **reconstruct** the index (kind + members + edges), not flip an extension.

## To expand
- The REPORT-mode output is the real per-bundle disposition of each one-off (which bundle owns it)
  before any vocabulary-closure decision.
