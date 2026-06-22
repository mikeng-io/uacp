---
name: uacp-handoff
description: >
  Use at a SESSION boundary — when you pause to work on something else, or stop —
  to save the session's NON-reconstructable context (intent, decisions + why, paths
  rejected and why-not, open threads, watch-outs) as a runtime-neutral, in-repo,
  per-workstream OKF capsule, so a fresh agent on any runtime resumes with reasoning
  continuity. Also use at session START to RESUME from a capsule. Triggers on
  "hand off", "pause this", "stop here", "save the session/context", "where did we
  leave off". NOT a memory note (this is runtime-neutral + committed + structured)
  and NOT RESOLVE (session-scoped, not run-scoped).
kind: orchestration
location: managed
dependencies:
  - uacp-core    # the .uacp/ base-path convention
  - uacp-state   # the active run_id, for a run anchor (optional)
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash(git log *)
  - Bash(git diff *)
  - Bash(git status *)
  - Bash(git branch *)
  - Bash(ls *)
  - Bash(mkdir *)
---

# UACP Handoff — Save / Resume Non-Reconstructable Session Context

A work **session** holds context that lives only in the conversation and dies at
pause/stop. This skill serializes the part that **cannot be reconstructed from the
repo** so reasoning continuity survives the boundary. It is the runtime-neutral,
committed, structured counterpart to a private memory note. Full design + rationale:
`design/handoff/` (read on demand).

## The inclusion contract (the ONE rule)

Before writing any line, apply the test:

> **"Can a fresh agent recover this by reading the commits, the diff, and repo
> status?"**
> - **YES → it is reconstructable.** Do NOT write it as prose. Record it as an
>   **anchor** (a typed link in `edges:` + the Anchors list). Files changed, what
>   the code does, mechanical steps, status — all anchors, never body.
> - **NO → it is non-reconstructable** (the *why*, decisions + rationale, rejected
>   paths + why-not, intent, open threads, judgment, watch-outs). This requires
>   human input to recover — it is the only thing worth saving, and it belongs in a
>   body section.

Saving reconstructable content is exactly what bloats a handoff into a useless
blob. Resist it: when in doubt, make it an anchor, not prose.

## Where capsules live

- One capsule **per workstream**: `.uacp/handoffs/<workstream>.md` (committed OKF).
- The index: `.uacp/handoffs/_index.yaml` (what capsules exist + their status).
- A **workstream** is a coherent thread of work (e.g. `graph-engine-decomposition`),
  NOT a single run or session. **One file per workstream, overwritten in place** —
  never append, never mix workstreams. Git carries the history.

## Verb: WRITE / UPDATE (at pause or stop)

1. **Resolve the workstream** — ask the user or infer from the active context →
   `<workstream>` (kebab-case) → path `.uacp/handoffs/<workstream>.md`.
2. **If the capsule exists, READ it first** — you are updating, not recreating.
3. **Gather anchors (the reconstructable refs)** — current branch + last commit
   (`git branch --show-current`, `git log -1 --oneline`), relevant design nodes,
   the active `run_id` if any. These become typed `edges:` — NOT body prose.
4. **Distill the non-reconstructable** from the session into the six sections
   below, applying the inclusion contract to *every* line.
5. **Write the capsule** from `assets/handoff-template.md`, **overwriting in
   place**. Set `status: active`; set `updated_at` to today.
6. **Update `.uacp/handoffs/_index.yaml`** — the workstream's entry (status +
   one-line hook + updated_at). Create the index (and the dir) if absent.
7. **Tell the user the capsule path.**

### The six body sections (non-reconstructable only)

1. **Intent** — why this workstream exists; the goal/outcome. Not the task list.
2. **Decisions & rationale** — each choice + *why*, marked `[locked]` (do not
   re-litigate) or `[open]`.
3. **Rejected / not-this** — paths dropped + *why-not* (so they are not retried).
4. **Open threads & watch-outs** — unresolved forks, deferred items, non-obvious
   traps discovered.
5. **Now → next** — current position as a *pointer* (branch + last commit, in
   `edges`) + the next *intent* (what to achieve, not the steps).
6. **Anchors** — a rendered list mirroring `edges:` (the click-through to all
   reconstructable detail).

## Verb: RESUME (at session start)

1. Read `.uacp/handoffs/_index.yaml`; pick the `active` capsule for the workstream.
2. Read the capsule → re-establish Intent + `[locked]` decisions + open threads.
3. Follow **anchors** (commits / diff / design nodes) to reconstruct detail **on
   demand** — the capsule intentionally does not inline it.
4. Continue from **Now → next**.
5. RESUME is read-mostly — but if resuming **shifts the intent or state** (a new
   decision, a closed thread), run **WRITE / UPDATE** to refresh the capsule before
   proceeding, so it never goes stale.

## Lifecycle (decay / supersede — keeps it bounded)

- `status: active` → `resolved` when the workstream is done / merged / abandoned
  (it drops out of the active index view; keep the file for lineage).
- `status: superseded` when a newer capsule replaces it (add a `superseded_by`
  edge). **Never hard-delete** — tombstone/keep, so decision lineage survives.
- Bounded by construction: per-workstream + update-in-place means no single capsule
  grows without limit.

## Format

The exact OKF capsule shape (frontmatter + anchors-as-edges + section rules) is in
`references/capsule-format.md`; the empty form is `assets/handoff-template.md`.

> Integration note (future): `.uacp/handoffs/` and the `handoff` / `handoff_index`
> kinds are not yet registered in `layout.py` / `uacp-lint`; the skill uses the
> fixed path directly. Register them when the handoff workstream merges.
