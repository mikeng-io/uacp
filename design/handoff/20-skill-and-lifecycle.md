---
type: contract
title: Session-Handoff — The Skill, the Index, and the Lifecycle
description: The uacp-handoff skill (topology, its two verbs write/resume, runtime-neutral trigger), the per-collection _index.yaml, and the D18 decay/supersede lifecycle that keeps capsules bounded.
tags: [handoff, skill, index, lifecycle, decay, supersede, uacp-skills]
timestamp: 2026-06-22
edges:
  - {dst: 10-capsule-format, rel: depends_on, provenance: asserted}
  - {dst: 02-decisions, rel: relates_to, provenance: asserted}
---

# The Skill, the Index, and the Lifecycle

## The skill (topology + kind)

Per the `uacp-skills` convention:

```
skills/uacp-handoff/
├── SKILL.md                 # kind: orchestration; the two verbs + the inclusion contract
├── references/
│   └── capsule-format.md    # points to design/handoff/10 (the OKF shape)
└── assets/
    └── handoff-template.md  # the empty capsule (frontmatter + the six sections)
```

- `kind: orchestration` (sibling of `uacp-context`); cross-cutting, user-initiated.
- **Runtime-neutral**: no command. The skill triggers by its `description` /
  `when_to_use` on the intent — *"pause / stop / hand off / save the session
  context"* — and via the `uacp` router. Hermes/Kimi invoke the skill directly
  (H2). No `/uacp:` dependency.

## Two verbs

**WRITE / UPDATE** (at pause or stop):
1. Resolve the **workstream** (from the user or the active context) → the capsule
   path `.uacp/handoffs/<workstream>.md`. If it exists, **read it first**.
2. Distill the session through the **inclusion contract** (10-capsule-format): only
   the non-reconstructable; reconstructable refs become **anchors (edges)**.
3. **Overwrite in place** (H4) — refresh the six sections + `edges`; bump
   `updated_at`. Do not append, do not mix workstreams.
4. Update `_index.yaml` (status + one-line hook + last-updated).
5. Tell the user the capsule path.

**RESUME** (at session start):
1. Read `_index.yaml`; pick the `active` capsule(s) for the workstream.
2. Load the capsule → re-establish intent + locked decisions + open threads.
3. Follow **anchors** to reconstruct detail on demand (commits/diff/nodes) — the
   capsule deliberately does not inline it.

## The index — `.uacp/handoffs/_index.yaml` (D28 aggregate-as-node)

```yaml
kind: handoff_index
members:                       # canonical list (one per workstream)
  - graph-engine-decomposition.md
entries:                       # derived view for fast lookup
  - {workstream: graph-engine-decomposition, status: active, updated_at: '2026-06-22',
     hook: "core.py decomposition A1+A2 done; A3 (Heartgate split) next"}
```

The committed, structured counterpart to `MEMORY.md` — but OKF + per-workstream.

## Lifecycle — decay/supersede (D18 reuse, no new mechanism)

| status | when | effect |
|---|---|---|
| `active` | workstream in progress | shown in the index's active view; loaded on resume |
| `resolved` | workstream done / merged / abandoned | drops out of the active view; kept for lineage; optionally moved to `.uacp/handoffs/archive/` |
| `superseded` | a newer capsule replaces it | `superseded_by` edge to the successor; old one kept |

- **Never hard-delete** — tombstone/keep, so decision lineage survives (D18).
- **Bounded by construction** — per-workstream (H4) + update-in-place + status
  transitions mean no single file grows without limit; git holds the history.
- **Contradiction = supersede by recency/evidence** (D30) — a later capsule's
  decision supersedes an earlier one, traceably.

## Build note (not part of the design)

Build directly as a small skill (TDD where there's logic — the inclusion-contract
distillation + the index update). The capsule format + `_index` should validate as
OKF (reuse the node-kind validation path; add a `handoff` / `handoff_index` kind to
`uacp-lint` when that lands). No kernel change required.
