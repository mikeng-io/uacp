---
type: analysis
title: Session-Handoff — Intent & The Reconstructable/Non-Reconstructable Cut
description: Why UACP needs a session-handoff skill — the problem (session context dies at pause/stop), the organizing principle (save only the non-reconstructable), and how it differs from the CC-private memory note, RESOLVE, and the knowledge corpus.
tags: [handoff, session-context, intent, runtime-neutral, non-reconstructable]
timestamp: 2026-06-22
edges:
  - {dst: 02-decisions, rel: relates_to, provenance: asserted}
---

# Session-Handoff — Intent

## The problem

A work **session** (a conversation / context window) accumulates a great deal of
useful information that exists **only in the conversation** and **dies when the
session ends**. When you pause to work on something else, or stop entirely, that
context is lost — and a fresh agent (you, later, or another runtime) restarts
cold or rebuilds a partial, inaccurate picture that needs human re-enrichment.

Today the de-facto capture mechanism is the **Claude Code memory note**. Two
problems: (1) it is **CC-private and per-user** — not runtime-neutral, not in the
repo, invisible to Hermes/Kimi or a teammate; (2) it tends to **"smash everything"**
into one ever-appending blob that mixes workstreams and drifts toward including
reconstructable noise.

## The organizing principle — the reconstructable / non-reconstructable cut

A session transcript holds two kinds of information:

- **Reconstructable** — files changed, what the code does, the mechanical steps,
  status. A fresh agent re-derives this trivially from **the commits, the diff,
  and repo status**. → **Never saved.** Saving it is exactly what bloats the blob.
- **Non-reconstructable** — lives only in the conversation and **requires human
  input to recover**: the **why**, the decisions and their **rationale**, the
  **paths rejected and why-not**, the current intent/goal, open questions, "we
  discovered X", the judgment calls, the things-to-watch-for, the preferences
  voiced. At best you semantically reverse-engineer a partial, inaccurate version
  — and still need the human to enrich it. → **This is what the handoff saves.**

**The contract:** if something can be recovered by reading the repo, it is a
**link (an anchor)**, never inlined prose. The handoff is the serialized
*directional abstraction* over the work; the detail is reached through anchors.

## What it is NOT (boundary vs adjacent UACP pieces)

- **Not the memory note** — it is runtime-neutral, in-repo (committed OKF), and
  structured per-workstream (not a private append-only blob).
- **Not RESOLVE** — RESOLVE closes a *governed run* and distills *lessons*. A
  handoff is **session-scoped** and fires at **pause/stop**, mid-run, post-run, or
  with no run at all. It is orthogonal to the lifecycle.
- **Not the knowledge corpus** — the Oracle corpus holds distilled, cross-project
  knowledge/lessons. A handoff is the *live working context* of one workstream,
  with its own lifecycle; it may later *feed* a lesson, but it is a distinct kind.

## Why it belongs in UACP

It is literally UACP's thesis — *if a relation/intent matters, serialize it; never
re-derive it* — applied to session context. Making it a UACP skill (not a CC
memory note) makes it **runtime-neutral and committed**, and lets each capsule be a
first-class **graph node** (anchors = typed edges), consistent with the graph
engine. See [02-decisions](02-decisions.md) for the choices and their rationale.
