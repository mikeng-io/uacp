---
type: contract
title: Session-Handoff — The Capsule Format (OKF node + typed-edge anchors)
description: The concrete shape of one handoff capsule — OKF frontmatter (incl. anchors as typed edges), the six intent-level body sections, and the inclusion contract (non-reconstructable in body; reconstructable as anchors only).
tags: [handoff, capsule, okf, schema, anchors, edges, template]
timestamp: 2026-06-22
edges:
  - {dst: 00-overview, rel: realizes, provenance: asserted}
---

# The Capsule Format

One capsule = one workstream = `.uacp/handoffs/<workstream>.md`, an **OKF node**
(YAML frontmatter + Markdown body), **updated in place**.

## Frontmatter (typed metadata + anchors-as-edges)

```yaml
---
kind: handoff
workstream: graph-engine-decomposition     # the per-workstream identity (= filename)
title: Decompose core.py into engines/ (Guardian → loaders → Heartgate)
status: active                             # active | resolved | superseded (D18)
scope: { in: [...], out: [...] }           # what this workstream is / is not
attribution:                              # who/what produced it (D33 shape)
  generated_by: { agent: <id>, model: <id>, runtime: <hermes|cc|kimi> }
  updated_at: '2026-06-22'                 # recency (D30 tag)
edges:                                     # ANCHORS = typed edges (H5) — the only place reconstructable refs live
  - {dst: 'branch:graph-engine-next', rel: anchored_to, provenance: parsed}
  - {dst: 'commit:f8459cf',           rel: anchored_to, provenance: parsed}
  - {dst: 'design/graph-engine/31-target-module-graph', rel: relates_to, provenance: asserted}
  - {dst: 'run:<run_id>',             rel: derived_from, provenance: derived}   # if a governed run is involved
---
```

- `workstream` is the stable identity; the file is overwritten per handoff (H4).
- `edges` are the **anchors**: links to commits/branch/design-nodes/runs, carrying
  `rel` + `provenance` (`parsed` for code/git, `asserted` for human links,
  `derived` for run FKs). This makes the capsule a graph node (H5) and enforces
  the inclusion contract structurally — reconstructable refs are edges, not prose.

## Body — six intent-level sections (non-reconstructable only)

Each section is the **directional abstraction**, not the steps. If a line could be
recovered from the repo, it belongs in an anchor, not here.

1. **Intent** — why this workstream exists; the goal/business outcome. The thing a
   bigger context window does not give you.
2. **Decisions & rationale** — choices made and *why*, each marked **`[locked]`**
   (do not re-litigate) or **`[open]`**. The judgment, not the diff.
3. **Rejected / not-this** — paths considered and dropped, with the *why-not*, so a
   fresh agent does not retry them.
4. **Open threads & watch-outs** — unresolved forks, deliberately-deferred items,
   and non-obvious traps discovered (the hard-won gotchas).
5. **Now → next** — current position as a *pointer* (branch + last commit, both in
   `edges`) and the next *intent* (what to achieve next, not the mechanical steps).
6. **Anchors (rendered)** — a human-readable list mirroring the frontmatter `edges`
   (the single click-through to all reconstructable detail).

## The inclusion contract (the test for every line)

> "Can a fresh agent recover this by reading the commits, the diff, and repo
> status?" — **Yes →** it is an anchor (an edge), never body prose. **No →** it is
> non-reconstructable; it belongs in a body section.

This is the whole discipline: the capsule is small because it holds only what dies
with the session. Validation (`uacp-lint`, later) can enforce required sections +
that `edges` carry valid `rel`/`provenance`, exactly as for other OKF nodes.
