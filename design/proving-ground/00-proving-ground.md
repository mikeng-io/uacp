---
type: analysis
title: The Proving Ground — the fully-automated lane; one apparatus, two readouts (root)
description: A contained REAL-agent substrate for the FULLY-AUTOMATED lane — headless, GHA/release-test/benchmark grade, no human in the loop (mike's ruling 2026-07-17). The companion/interactive lane is e2e-acceptance (Claude, real plugin install, operator-in-the-loop) — complementary, NOT superseded; the Proving Ground absorbs specific pieces of it (model proxy, tiered assertions, plugin-conformance probe, task/oracle layer). One apparatus, two readouts — a conformance TEST verdict and BENCHMARK scores. Supersedes self-diagnosis's scripted driver while absorbing its objective observer core. Deliberately thin.
tags: [proving-ground, automated-lane, test-bench, benchmark, dogfood, root]
timestamp: 2026-07-17
edges: []
---

# The Proving Ground (root)

> **DRAFT v2 — post-panel.** v1 was reviewed by a 3-way panel (2× adversarial technical/
> coherence + cross-provider gemini); v2 folds the findings and mike's rulings (2026-07-17):
> in-repo `tools/proving-ground/`; provider env contract; LLM-judge quarantine; and the
> **two-lanes ruling** below. Substance in 10–50.

## The two lanes (mike's ruling, 2026-07-17)
UACP has two testing surfaces with different purposes, and this bundle is ONE of them:

- **Companion / interactive lane = `design/e2e-acceptance/`** — Claude Code, a REAL
  `claude plugin install`, the operator in the loop ("inline testing / I test myself").
  Merged design, Increment 0 built (PR #36). **Not superseded by this bundle.**
- **Automated lane = the Proving Ground (this bundle)** — **headless, no human in the loop**:
  CI / GitHub-Actions release tests and benchmark sweeps. Cells must be drivable unattended,
  which is why the lane leads with Hermes + a local model (no interactive auth, no per-token
  cost) and treats cloud cells as auth-gated extras (50).

The lanes are complementary and share substance: the Proving Ground **absorbs** from
e2e-acceptance its model-normalizing proxy concept (10), its tiered hard-gate/soft-completion
assertion split (30), its Priority-1 plugin-conformance probe (30), and its task/oracle layer
(40) — and it **reuses** e2e's containment posture. Where e2e-acceptance's roadmap deferred
"hand-building a bespoke harness" for the *acceptance* purpose, this bundle builds a harness
for the *automated* purpose — a scope the deferral did not cover; the distinction is recorded
in the decision-log entry planned in 50.

## What it is
A **universal substrate** that runs a **real agent** (Hermes first; Claude and others as
cells) **inside a container**, with or without the UACP runtime (MCP server + hooks) **inside
that container with it**, against a model reached through a standard provider env contract
(local host ollama now; cloud later) — driven over **one transport** (ACP), and observed
**from outside the jail** by a deterministic observer that reads the exported trail.

## One apparatus, two readouts
1. **Test verdict** — *does UACP run normally when a real agent consumes it?* The observer's
   L1–L4 engine-conformance gates (30), with e2e's tiered split: governance-held is the hard
   gate; task completion is a soft score. This is the **real agent-through-tools dogfood**.
2. **Benchmark scores** — *does governance help, and at what cost?* N-replicated cells (40),
   objective oracles + governance metrics consumed from the existing witness/forecast ledgers.
   This feeds the telos **friction budget** its quantitative proxy
   (`design/telos/40-derivations.md`, Lock 2 — the hook is explicit on both sides; canonical encoding: `docs/policy/first-principles.md` + ADR-0021).

Two readouts, not two systems: the benchmark is the test run *scored*; the test is the
benchmark run *gated*.

## Why self-diagnosis was not enough (supersede + absorb)
`design/self-diagnosis` (branch `docs/self-diagnosis-design`) got the **observer** right —
content-independent L1–L4, fail-closed CODE gates, the decoupling litmus, mandatory
planted-fault calibration — absorbed into 30. What it could not deliver was the **driver**:
two manually-coordinated Claude contexts, no plugin/MCP surface, and its own open
precondition ("the `uacp_*` governed writers were not present"). The Proving Ground replaces
that driver with a real contained agent hitting the real tool surface. (Its "breaking-change stimulus" survives as a load-bearing part of calibration — every
planted fault ships with a must-block stimulus whose rejection must visibly disappear under
the fault — and regression detection additionally lives in scoreboard diffs across UACP
versions; 30, 40.)

## Placement
**In this repo** (mike's ruling): `tools/proving-ground/`. Operational tooling, not kernel —
the observer imports nothing from `skills/` and consumes only the exported trail, with a
schema **contract test** pinning it to kernel truth (30).
