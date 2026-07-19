---
type: analysis
title: The benchmark — N-replicated cells, honest causal claims, and the friction-budget feed
description: The benchmark readout scores the SAME runs the test readout gates — with STATISTICS AS FIRST-CLASS (panel-critical fix). Every cell is N replicates of a stochastic agent — means, variance, confidence intervals; single runs are anecdotes and are never reported as scores. The only CAUSAL claim is ±UACP within one agent on a fixed model (governance ablation); cross-agent comparisons are confounded (agent x model move together) and reported as descriptive only. Metrics — deterministic task oracles + governance metrics CONSUMED from the existing #80 witness/forecast ledgers (never re-counted). Reference local model (scored) — qwen3.6:35b-a3b from the ollama library (mike's pin; the unsloth hf.co GGUF failed to finalize on the local ollama runtime with Error 400 at the manifest step, so the ollama-library artifact of the same official model is the reproducible pin, digest recorded at first pull; the locally-present community finetune is forbidden as a baseline). Smoke tier is criteria (>=64K reported ctx + probe-verified tool-calling + replicate speed), current roster smoke=qwen3.5:4b, fallbacks qwen3:30b-a3b / gemma4:12b. Explicit wall-clock budget — the host GPU is one serialized resource. LLM-judge quarantined to a labeled advisory layer.
tags: [benchmark, replicates, statistics, confounds, oracles, governance-metrics, friction-budget-feed, llm-judge-quarantine]
timestamp: 2026-07-17
edges:
  - {dst: 00-proving-ground, rel: depends_on, provenance: derived}
  - {dst: 10-topology, rel: depends_on, provenance: derived}
  - {dst: 30-observer, rel: consumes, provenance: asserted}
---

# The benchmark

## Statistics first (the panel's critical fix)
Agents are stochastic: a single pass/fail per cell is one Bernoulli draw — an anecdote, not a
score. Therefore, as design law:

- **A cell result is N replicates** (N declared per sweep, ≥5 for smoke, ≥20 for a scored
  sweep), reported as mean ± a confidence interval, with per-replicate records kept. No
  single-run number is ever presented as a score.
- The **replicate/aggregation pipeline is built in S1** (50) — before any scored sweep exists —
  so the data-handling reality (and the wall-clock bill) is confronted first, not discovered
  at S4.
- Governance metrics are per-run **random variables** and get the same treatment (distributions,
  not point values).

## Honest causal structure (the confound, named)
Agent and model move **together** across rows (`claude-*` = Claude+Anthropic; `hermes-*` =
Hermes+Qwen). Consequently:

- The only **causal** claim the matrix supports is the **governance ablation**: ±UACP *within
  one agent on one fixed model* (e.g. `hermes-bare` vs `hermes-uacp`).
- **Cross-agent** comparisons (hermes-vs-claude anything) are **descriptive context only** —
  harness⊗model entangled, never attributed to UACP. The "does UACP lift a weak harness toward
  governed-strong quality" phrasing is an *interpretive frame* over the descriptive rows, not
  a measured effect; the measured effect is the within-agent delta on each side.

## The cell matrix (automated lane; two-lanes ruling in 00)
| cell | agent | model | UACP | role |
|---|---|---|---|---|
| `hermes-bare` | Hermes | host ollama (local, env contract) | off | automated-lane floor |
| `hermes-uacp` | Hermes | host ollama (local, env contract) | on | **the thesis cell** (vs `hermes-bare`) |
| `claude-bare` | Claude Code | Anthropic API | off | descriptive strong reference; parity check vs the companion lane (auth-gated, 50) |
| `claude-uacp` | Claude Code | Anthropic API | on | governance ablation on the strong side |
| *(later)* `pi-*`, `opencode-*` | … | … | ± | added as cells (20) |

**Reference local model (scored tier):** `qwen3.6:35b-a3b` **from the ollama library** (mike's
pin) — pinned per cell via the REQUIRED `model_id` in the env contract (10.3) and recorded in
each replicate's provenance. *Honest provenance note:* the intended artifact was the official
`unsloth/Qwen3.6-35B-A3B-GGUF` hf.co quant, but it **failed to finalize on the local ollama
runtime** (`Error: 400` at the manifest step); the **ollama-library artifact of the same
official model** is therefore the reproducible pin, and its **digest is recorded at first pull**
so the baseline is reproducible by others. The `Qwen3.6-35B-A3B` variant already on the host
(`HauhauCS…Uncensored…Aggressive`) is a community finetune and **forbidden as a baseline**.
Scored local cells must serve their model with >=64K runtime context (ollama `num_ctx`).

**Smoke tier = criteria, not a fixed model.** The cheap smoke tier is defined by *properties* a
model must satisfy — **(1)** reports **>=64K context** (Hermes's hard floor, an S0 finding:
`qwen2.5:3b`'s 32K is rejected at `session/new`, with a silent-refusal trap under a context
override), **(2)** **probe-verified tool-calling**, and **(3)** replicate speed cheap enough for
per-push use. Current roster: **smoke = `qwen3.5:4b`** (mike's preference 2026-07-18 — same
family as the scored model; probe PASS: 262K reported context, tool-calling OK), with
**fallbacks `qwen3:30b-a3b`** (already on-disk) and **`gemma4:12b`** (cross-family). Smoke =
pipeline checks, never scored cells.

## Wall-clock budget (the host GPU serializes everything)
Local cells contend for ONE Metal GPU — replicates run **serially**. Order-of-magnitude: a
governed multi-tool run on a 35B-A3B ≈ minutes-to-tens-of-minutes; × tasks × cells ×
calibration × N replicates = **hours-to-days per scored sweep**. Consequences, by design:
scored sweeps are operator-triggered batch jobs (overnight), never per-push CI; per-push CI
gets the smoke tier at most (50); every sweep declares its run-count budget up front. Cheap in
dollars is not cheap in time — the bench says so instead of discovering it.

## Task suite
Fixed, versioned, pinned-workspace tasks with **deterministic oracles** — absorbing the
e2e-acceptance task/scenario layer (two-lanes ruling, 00). Every task ships: a pinned repo
state, a prompt, an oracle script (compiles? tests pass? artifact exists and validates?), and
a time/token ceiling. Calibration variants (30) are part of the suite.

## Two metric classes (and only these two are scores)
1. **Objective task oracles** — deterministic pass-rate over N replicates. The headline.
2. **Governance metrics** — **consumed from the machinery that already owns them** (panel:
   never re-counted in parallel): scope drift from the #80 witness ledgers
   (`witness_promotion_report` / `scope_conformance` outputs), forecast precision from the
   cascade-forecast records, gate outcomes and rework rounds from the gate ledger, evidence
   completeness from the closure engines' own verdicts — plus runner-side cost (tokens,
   wall-clock, container CPU). The bench is a *consumer and aggregator* of the witness lane,
   not a second implementation of it. This class is the **friction-budget feed**
   (`design/telos/40`, Lock 2: removing a guardrail requires measured evidence — these are the
   numbers).

## The LLM-judge quarantine
Semantic quality scoring (e.g. Strands Agents eval — LLM-as-judge against prose criteria) is
**permitted only as a third, clearly-labeled advisory layer** — never the engine-conformance
floor (30's ban stands) and never blended into the two score classes. If used, the judge is a
semantic gate in telos terms, subject to recursive critique (`design/telos/20`) —
cross-provider, never the SUT's own model family. Prefer extending oracles over judges.

## Output
Per replicate, **by cell kind** (bare cells run with UACP off and emit no lifecycle trail —
grading one would be spurious):
- **`*-uacp` cells**: observer verdict (hard gate + soft completion, 30) + BOTH metric classes.
- **`*-bare` cells**: task oracles + runner-side cost only; **engine-conformance and
  governance metrics are N/A** — recorded as N/A (never as zeros or failures) and **excluded
  from those aggregates**, so bare-vs-uacp comparisons happen only on the fields both kinds
  possess (task pass-rate, cost), never on governance fields only one kind can emit.

All serialized to a versioned results ledger (schema at build). Per sweep: an aggregated
scoreboard (means, CIs, N, with per-field cell-kind eligibility) diffable across UACP versions
— the **regression bench** role: a kernel change that degrades `hermes-uacp` or inflates its
governance cost is visible before release.
