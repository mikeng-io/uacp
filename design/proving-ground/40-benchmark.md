---
type: analysis
title: The benchmark — the cell matrix, two metric classes, and the friction-budget feed
description: The benchmark readout scores the SAME runs the test readout gates. Cell matrix — {claude-code, hermes, later pi/opencode} x {bare, +UACP}, with claude-bare as the strong control and hermes-bare as the weak floor; the question is whether UACP lifts a weak/local harness toward governed-strong quality AND what it costs. Two metric classes — objective task oracles (deterministic pass/fail) and governance metrics (rework rounds, evidence completeness, scope drift, tokens/wall-clock). Feeds the telos friction budget its quantitative proxy (design/telos/40 Lock 2 — removing a guardrail requires measured evidence). LLM-judged quality (e.g. Strands Agents eval) is a clearly-labeled OPTIONAL semantic layer, never the engine-conformance floor.
tags: [benchmark, cell-matrix, oracles, governance-metrics, friction-budget-feed, llm-judge-quarantine]
timestamp: 2026-07-17
edges:
  - {dst: 00-proving-ground, rel: depends_on, provenance: derived}
---

# The benchmark

## The cell matrix
| cell | agent | model | UACP | role |
|---|---|---|---|---|
| `claude-bare` | Claude Code | Anthropic API | off | strong control |
| `claude-uacp` | Claude Code | Anthropic API | on | governed-strong |
| `hermes-bare` | Hermes | host ollama (local) | off | weak floor |
| `hermes-uacp` | Hermes | host ollama (local) | on | **the thesis cell** |
| *(later)* `pi-*`, `opencode-*` | … | … | ± | added as cells (20 — a Dockerfile + adapter each) |

The question the matrix isolates: **does UACP lift a weak/local harness toward governed-strong
quality — and what does the lift cost?** Both ablations matter: agent held constant (±UACP =
governance ablation) and governance held constant (across agents = harness ablation).
Reference local model: **Qwen3.6-35B-A3B** (official quant, e.g. `unsloth/...-GGUF:Q4_K_M` —
not a community finetune; a benchmark baseline must be reproducible by others). Small models
(qwen2.5:3b) serve as cheap smoke cells, not scored cells.

## Task suite
Fixed, versioned, pinned-workspace tasks with **deterministic oracles** — reusing the
e2e-acceptance harness's task/oracle layer where it lands. Every task ships: a pinned repo
state, a prompt, an oracle script (compiles? tests pass? artifact exists and validates?), and
a time/token ceiling. Calibration variants (30) are part of the suite, not an afterthought.

## Two metric classes (and only these two are scores)
1. **Objective task oracles** — deterministic pass/fail per task. The headline.
2. **Governance metrics** — what the trail already contains, counted: rework rounds to green,
   evidence completeness (did VERIFY carry real artifacts), scope drift (declared-vs-touched —
   the codeflair witnesses' own signal), gate outcomes, tokens + wall-clock + container CPU.
   This class is where +UACP must earn its cost even when raw pass-rate ties — and it is the
   **friction-budget feed**: `design/telos/40` (Lock 2) requires *measured evidence* to remove
   a guardrail; these numbers are that evidence (cost of a gate vs the defects it caught).

## The LLM-judge quarantine
Semantic quality scoring (e.g. **Strands Agents SDK's eval**, LLM-as-judge trajectory review)
is **permitted only as a third, clearly-labeled advisory layer** — never as the
engine-conformance floor (30's ban stands: the floor is a deterministic gate) and never
silently blended into the two score classes above. If used, the judge is itself a semantic
gate in telos terms and subject to recursive critique (`design/telos/20`) — cross-provider,
never the SUT's own model family. Prefer extending the oracle set over reaching for a judge.

## Output
Per run: the observer verdict (L1–L4) + the two metric classes, serialized to a versioned
results ledger (schema at build). Per matrix sweep: a scoreboard diffable across UACP versions
— which makes the Proving Ground double as UACP's **regression bench**: a kernel change that
degrades `hermes-uacp` pass-rate or inflates its governance cost is visible before merge.
