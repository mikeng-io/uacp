---
kind: handoff
workstream: build-uacp-handoff-skill
title: A runtime-neutral uacp-handoff skill — save/resume non-reconstructable session context
status: active
scope:
  in: [the uacp-handoff skill, the OKF capsule format, the .uacp/handoffs index]
  out: [kernel changes, layout.py/uacp-lint registration, a CC command]
attribution:
  generated_by: { agent: claude-code, model: claude-opus-4-8, runtime: cc }
  updated_at: '2026-06-22'
edges:
  - {dst: 'branch:handoff', rel: anchored_to, provenance: parsed}
  - {dst: 'commit:b267811', rel: anchored_to, provenance: parsed}
  - {dst: 'commit:df07074', rel: anchored_to, provenance: parsed}
  - {dst: 'design/handoff/_index', rel: relates_to, provenance: asserted}
  - {dst: 'design/handoff/02-decisions', rel: relates_to, provenance: asserted}
---

# Handoff — build-uacp-handoff-skill

## Intent
Give UACP a runtime-neutral, in-repo way to preserve the part of a session that
dies at pause/stop. The problem: a session holds judgment/intent/decisions that
only exist in the conversation; the de-facto capture (the CC memory note) is
private, per-user, and "smashes everything" into one append-only blob. The goal is
the opposite: committed, per-workstream, structured, intent-level.

## Decisions & rationale
- [locked] **Save only the non-reconstructable.** If a fresh agent can recover it
  from commits/diff/status, it is an *anchor* (a link), never body prose. This is
  the whole discipline and the anti-bloat rule.
- [locked] **Skill, NOT a command.** A `/uacp:handoff` is a Claude-Code-specific
  dependency; UACP is runtime-neutral pure-skills, so the skill triggers by
  description and via the `uacp` router. (A CC-only command is an optional personal
  add-on later, never core.)
- [locked] **One capsule per workstream, update-in-place** (git carries history) —
  the structural cure for the blob.
- [locked] **Capsule = OKF node; anchors = typed edges** → handoffs are first-class
  graph nodes (graph-engine fit). Index = `_index.yaml` (D28). Decay = D18 lifecycle.
- [locked] **Compose existing primitives** (OKF + edges + D18 + D28 + D30) — not a
  new mechanism.

## Rejected / not-this
- A flat `HANDOFF.md` in the project root (the reference skill) — mixes workstreams,
  drifts toward reconstructable noise, not runtime-governed.
- Folding into `uacp-context` — handoff is a distinct, user-initiated responsibility;
  it earns its own door.
- Putting the capsules in the Oracle knowledge corpus — different lifecycle + would
  trip the corpus boundary; handoffs are live working context, not distilled knowledge.

## Open threads & watch-outs
- **Kernel registration (deferred):** `.uacp/handoffs/` and the `handoff` /
  `handoff_index` kinds are not yet in `layout.py` / `uacp-lint`; do this when the
  branch merges to main.
- watch-out: a fresh worktree off main has **no `.mcp.json` on disk** (main
  untracked it); `test_mcp_manifests` / `test_cc_install_readiness` then fail —
  restore it with `git show 43071d1:.mcp.json > .mcp.json` (untracked, gitignored).
- open: should the index-update be a tiny helper script, or stay an agent step?
  (Kept as an agent step for now — no code, max portability.)

## Now → next
- **Position:** see Anchors (branch + commits live there). The skill is built and
  suite-green; the working tree is clean.
- **Next intent:** merge `handoff` → main when ready; then register `.uacp/handoffs/`
  + the handoff kinds in `layout.py` / `uacp-lint`. Optionally dogfood a capsule for
  the graph-engine workstream from its own worktree.

## Anchors
- branch: `handoff` (off `main`)
- commit: `b267811` — built the uacp-handoff skill (SKILL.md + template + reference + seed index)
- commit: `df07074` — the design bundle `design/handoff/`
- design: `design/handoff/` (_index, 00-overview, 02-decisions, 10-capsule-format, 20-skill-and-lifecycle)
