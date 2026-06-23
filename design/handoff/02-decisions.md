---
type: analysis
title: Session-Handoff — Decision Ledger
description: The design decisions for the handoff skill, each as options → verdict → rationale. Captures the judgment from the 2026-06-22 brainstorm so it does not evaporate.
tags: [handoff, decisions, verdict, rationale]
timestamp: 2026-06-22
edges:
  - {dst: 00-overview, rel: decides_on, provenance: asserted}
---

# Decision Ledger

## H1 — Save only the non-reconstructable; link the rest

**Verdict.** The capsule serializes ONLY non-reconstructable session context
(intent / decisions+rationale / rejected-paths / open-threads+watch-outs /
now→next intent). Anything recoverable from commits/diff/status is a **link
(anchor)**, never inlined.

**Rationale.** Reconstructable content has no reason to be saved — reading the
repo recovers it. Non-reconstructable context requires human input to recover; it
is the only thing worth the bytes. This is the inclusion contract; it is also what
keeps capsules small.

## H2 — A skill, NOT a command (runtime-neutral)

**Options.** (a) A CC plugin command `/uacp:handoff`. (b) A skill only. (c) Skill +
thin CC command.

**Verdict: (b) — skill only.** `skills/uacp-handoff/` (`kind: orchestration`,
sibling of `uacp-context`).

**Rationale.** UACP is **runtime-neutral** and pure-skills by design; a `/uacp:`
command is a **CC-specific surface** and would put a runtime dependency on the
trigger of a thing whose whole purpose is runtime neutrality. The skill is the
portable unit (Hermes/Kimi invoke it directly). It is triggered by its
`description`/`when_to_use` on the user's intent ("pause / stop / hand off / save
the session context") and via the `uacp` router — no command needed. A thin CC-only
`/uacp:handoff` is an **optional personal add-on later**, never part of the design.

## H3 — Home: `.uacp/handoffs/<workstream>.md`, committed OKF

**Verdict.** Capsules live at `.uacp/handoffs/<workstream>.md` — git-tracked OKF,
a peer of `.uacp/knowledge/` (which is already committed OKF; only runtime/
rebuildable dirs are gitignored).

**Rationale.** Committed → survives, shareable, runtime-neutral. OKF → consistent
with the rest of the control plane. A distinct dir (not under `knowledge/`) keeps
it out of the Oracle corpus boundary and out of the unsettled knowledge
sub-structure question.

## H4 — One capsule per workstream, UPDATE-IN-PLACE (the anti-blob rule)

**Verdict.** One capsule per **workstream/topic**, **overwritten in place** on each
handoff; git carries the history. Never append; never mix workstreams in one file.

**Rationale.** The blob problem (the memory note) comes from one ever-appending
doc. Per-workstream + update-in-place keeps each capsule bounded and focused, and
makes "pause this, start that" clean. History is git's job, not the file's.

## H5 — Capsule = OKF node; Anchors = typed edges (graph-engine fit)

**Verdict.** Each capsule is an OKF node: YAML frontmatter (`workstream`, `status`,
`scope`, `attribution`, `edges:`) + Markdown body. The **Anchors are typed
`edges:`** (`rel` + `provenance`): `--anchored_to(parsed)--> <commit>`,
`--relates_to(asserted)--> <design-node>`, `--derived_from(...)--> <run>`.

**Rationale.** This makes a handoff a **first-class graph node**, queryable and
projectable by the same engine as everything else — the non-reconstructable
context becomes serialized typed edges, exactly the graph-engine thesis. Anchors
being edges (not body prose) enforces H1 structurally.

## H6 — Indexing: `.uacp/handoffs/_index.yaml` (aggregate-as-node, D28)

**Verdict.** An `_index.yaml` aggregate root (per graph-engine D28): `members` (the
capsules) + each one's `status` + a one-line hook + last-updated. Reuses the
design-bundle index pattern.

**Rationale.** The lookup surface — "what handoffs exist, which are active" —
committed and structured, the counterpart to `MEMORY.md` but OKF + per-workstream.

## H7 — Decay/suppress: reuse the D18 node lifecycle (no new mechanism)

**Verdict.** Each capsule carries `status`: `active → resolved` (workstream
done/merged) → `superseded` (newer capsule, with `superseded_by` edges) → tombstone
(kept for lineage, never hard-deleted). Resolved capsules drop out of the active
index view; optionally archived under `.uacp/handoffs/archive/`. Recency is a
frontmatter tag (D30).

**Rationale.** UACP already has node lifecycle (D18) and contradiction-by-
supersede; the handoff reuses it rather than inventing decay. Combined with H4
(update-in-place), capsules never grow unboundedly.

## H8 — Dedicated skill, not folded into `uacp-context`

**Verdict.** A new dedicated `uacp-handoff` skill, sibling of `uacp-context`.

**Rationale.** Single, clear responsibility (user-initiated session capture at a
boundary) distinct from the context plane's broader concern; self-containment per
the `uacp-skills` convention. It composes the same primitives but earns its own
door.
