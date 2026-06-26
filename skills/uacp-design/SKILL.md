---
name: uacp-design
description: >
  The UACP design-bundle convention — how to author a decomposed bundle (facet nodes + _index
  under design/<topic>/) that passes the structural lint AND represents a good design. Read via
  the Read tool when starting a new design bundle, refactoring an existing one, or reviewing a
  design for propagation/over-serialization anti-patterns. UACP's analog of uacp-skills, but
  for design bundles.
kind: reference
---

# uacp-design — Authoring the judgment half

A UACP design is a **decomposed bundle** under `design/<topic>/` — facet nodes plus an `_index.yaml`.
This skill teaches the half that a lint cannot decide: **how to author a good bundle**, not just a
well-formed one. The structural checks (schema, members==files, placement, ≥2 nodes, edges mirror) live
in the lint — see "What you don't need to remember" below.

## The split: SKILL (judgment) vs LINT (structure)

| What | Owner | Mechanism |
|---|---|---|
| Decomposition quality, seam placement, single-source discipline, Status/Checkpoint | **this skill** | taught; reviewed by council |
| `_index.yaml` schema, members==files, ≥2 nodes, placement, node frontmatter, edges mirror | **the lint** | deterministic gate (`design_lint.py`) |

The lint is necessary but not sufficient. A bundle can pass every structural check and still
be a bad design (monolithic nodes, restated concepts, build-detail in prose). That is what
this skill covers.

## Core rule: decompose, don't monolith

A bundle is **one design topic, many facets**. Each top-level `.md` node owns **one concern**.
The `_index.yaml` is the reading order and the inter-node graph — not a summary of the whole topic.

Ask at every node boundary: *"Is this a distinct concern that someone might read in isolation?"*
If yes, it earns its own node. If the answer is "only makes sense together with node X," merge them.

The most common failure: writing one big doc, splitting it at an arbitrary line count, and declaring
it a bundle. The lint catches "fewer than 2 nodes" — the skill catches "the split is not at a real
seam."

**Placement:** always `design/<topic>/`. Never `docs/plans`, never a bare `docs/` file, never a
single doc with no `_index.yaml`. (The lint enforces the structural constraint; the skill tells you
why: design bundles are durable cross-run architecture, not transient docs.)

## Node shape

Every top-level `.md` in the bundle carries this frontmatter (all required by the lint):

```yaml
---
type: <see type set below>
title: <human-readable, one line>
description: <one-line purpose / trigger>
tags: [<topical>, ...]
timestamp: <ISO date, e.g. 2026-06-27>
edges:
  - {dst: <node-stem>, rel: <rel-enum>, provenance: <provenance-enum>}
---
```

Nested `*.md` files under a subdirectory (e.g. `prompts/`, `eval/`) are **sub-assets, not nodes**
— they are not members, not subject to node-type validation, and do not appear in `_index.yaml`.

**Node `type` set (CORE, derived from the live corpus):**

| type | use |
|---|---|
| `analysis` | grounded survey, audit, research — comprehend |
| `design` | proposed model, structure, decisions in context |
| `contract` | exact, decidable spec a gate or tool will enforce |
| `reference` | operational contract or pattern read at runtime |
| `pattern` | reusable approach |
| `decision` | a recorded decision with rationale |

Known one-offs in the corpus: `roadmap`, `lessons`, `evidence`. The vocabulary is **not closed** —
the lint warns (does not hard-fail) on an unknown type. Closing is a later decision.

**Do not invent types** — choose the closest CORE type. If none fit, leave it for the REPORT pass.

## Edges

Edges are **intra-bundle only**. A node declares its own out-edges in frontmatter; the `_index.yaml`
mirrors them (the lint checks the mirror). Cross-bundle references are **prose links**, not edges.

Out-edge shape: `{dst: <node-stem-no-extension>, rel: <rel>, provenance: <provenance>}`

Common `rel` values: `realizes`, `depends_on`, `motivated_by`, `decides_on`, `sequences` (the full
closed enum + when to use which is in `references/edge-rel-provenance.md`).
`provenance` for a hand-authored bundle is `asserted` (author claim) or `derived` (follows from a
structural dependency) — the full enum is `derived | parsed | asserted | inferred`.

The `_index.yaml` carries `{src, dst, rel, provenance}` edges — match key is `{dst, rel}` only
(the lint does not match on `provenance`, which is `_index`-authored metadata).

A node with `edges: []` is a leaf or root — that is legal.

## The reference boundary

Reference peer bundles and the as-built — **do not duplicate** them. When a concept lives in
another bundle, link it in prose. Do not restate it. This is the single-source rule applied to
design docs.

**Read before linking:** check whether the target bundle actually covers what you need. If it does,
one sentence + a file path. If it only partly does, describe the gap explicitly.

## Status/Checkpoint (recommended, not required)

Add a `## Status / Checkpoint` section — a dated block recording what is built vs parked, linked
to the PR(s)/commit(s) that delivered it. The lint checks shape-if-present (a date in the heading
block), not presence. But a bundle without a checkpoint is harder to resume after a long pause.

Template:

```markdown
## Status / Checkpoint

_2026-06-27_ — nodes 00–21 complete; 22-rollout.md drafted; lint implementation in progress
(PR #XX). Node 30-future.md parked (backlog).
```

## Design-review anti-patterns

When reviewing a bundle (or asking a council to review it), avoid two loops:

**Propagation loop** — a concept appears in N nodes (you restated it instead of linking once). A
reviewer flags it in node A; you fix node A; the reviewer flags the same thing in node B. Break by:
identify the single-source node, link from all others, sweep the whole bundle in one pass.

**Over-serialization** — you pre-resolve BUILD detail in the design prose: exact variable names,
function signatures, file offsets. The design should state the model and the decisions; tests
arbitrate the detail at build. A sure sign: you keep "updating the design" as you write code.

## What you don't need to remember (the lint's job)

- `_index.yaml` must exist and pass the `design_index` schema
- `members` in `_index.yaml` must exactly equal the top-level `.md` files (excluding `_index*`)
- Bundle must have ≥2 nodes
- Placement must be `design/<topic>/`
- Node frontmatter must have all required keys; `type` must be present (hard-fail) and known (warn)
- Edges in node frontmatter must mirror edges in `_index.yaml` (match on `{dst, rel}`)

The lint is in `skills/uacp-core/scripts/engines/domain/design_lint.py`. Run it before committing.

## Relationship to other skills

- **uacp-brainstorm** — references this skill when a brainstorm crystallizes into a bundle. This
  skill does not live inside brainstorm; it is invoked independently.
- **uacp-skills** — structural analog: a skill paired with hard lints. Same pattern, different
  domain (skill authoring vs design-bundle authoring).

## Deeper rationale (single-source — this skill references it, doesn't restate it)

When you need the reasoning, read where it already lives — don't duplicate it here (that is this
skill's own reference-boundary rule):

| Topic | Read |
|---|---|
| The node-`type` CORE set + why the one-offs are deferred, not folded | `references/node-type-rationale.md` |
| The full `rel` / `provenance` enums + when to use which | `references/edge-rel-provenance.md` |
| The lint's exact checks (the structure half) | `uacp-core/scripts/engines/domain/design_lint.py` |
