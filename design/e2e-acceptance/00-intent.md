---
type: design
title: Intent — the E2E acceptance harness (real install, real agent, real lifecycle)
description: What the harness is and why; the load-bearing distinction between the in-process INTEGRATION tests (deterministic, CI-gating) and this black-box ACCEPTANCE test (real install + real agent + real model + full lifecycle, non-deterministic, periodic). Names the two pluggable seams and the two designed-in futures (benchmark, multi-runtime).
tags: [e2e, acceptance, smoke, black-box, test-pyramid, benchmark, runtime-neutral]
timestamp: 2026-06-26
edges: []
---

# Intent — the E2E acceptance harness

## In one sentence

Install UACP the way a real user will — **as a coding-agent plugin in a container** — and let a **real agent on a real model** drive **one complete governed run, TRIAGE → RESOLVE**, so the test exercises the *whole shipped path* (install → plugin registration → tool/MCP exposure → lifecycle → gates → resolve) and surfaces the **packaging / install / integration inconsistencies** that no in-process test can see.

## The distinction this bundle rests on

These are two different tests and must not be conflated (the misnaming that motivated this bundle):

| | INTEGRATION test (already the plan) | **ACCEPTANCE test (this bundle)** |
|---|---|---|
| Drives | the engines/adaptor in-process, scripted | a **real agent** in a **container**, on a **real model** |
| Determinism | deterministic | **non-deterministic** (a model is in the loop) |
| Install path | none (imports) | the **real plugin install** into the agent |
| Runs | every `pytest` / **CI merge gate** | a **separate periodic / pre-release** job |
| Proves | the machinery is correct | the **shipped product actually works when installed** |

The integration test gates merges; the acceptance test proves the product. We want **both** — this bundle is only the second. Top of the test pyramid: broad, slow, few, real.

## Why it exists (the failure it catches)

In-process tests import the engines directly, so they never exercise: the plugin manifest (`.claude-plugin/`), the MCP server actually starting and exposing `tool_specs()` over a transport, the skills/hooks registering in a fresh agent, the lifecycle being driven by *tool calls a model emits* rather than Python calls a test writes. A break in any of those is invisible until a user installs the package. The acceptance harness is the only thing that runs that path.

## Two pluggable seams (so the harness core stays neutral)

The harness *core* — scenario, assertions, orchestration, scoring — must not know which agent or which model is under test. Two seams isolate that:

1. **The runner-adapter seam** ([11](11-runner-adapter-seam.md)) — the AGENT under test. **Claude Code now** (consuming the CC adapter built in a parallel session — this bundle references it, does not specify it); **Hermes / Codex / others** later by swapping the runner container behind the same contract.
2. **The model-backend seam** ([12](12-model-backend-seam.md)) — the LLM provider. **Ollama by default** (long, free, local runs), but **backend-NEUTRAL**: an OpenAI-format endpoint, a real Anthropic API URL, or any local server, selected by config — never hardcoded.

## Two futures, designed in from v1 (not bolted on later)

- **(a) Benchmark.** Each run emits a **structured, scored result** ([22](22-benchmark.md)), not a bare pass/fail — so the same harness becomes a cross-agent / cross-model UACP-competence benchmark without re-architecture.
- **(b) Runtime breadth.** The runner-adapter seam means a new agent runtime is a new *container + entrypoint*, not a harness rewrite.

## Priority order (mike): plugin actionability FIRST, lifecycle measurement NEXT

The harness is built in two priorities, not one:

- **Priority 1 — plugin conformance ([13](13-plugin-conformance.md)).** Is the installed plugin *actionable*? Install UACP as a plugin in a fresh agent container and prove every declared capability works — skills load, hooks fire, the MCP server starts and its tools are callable, commands dispatch. If the plugin doesn't function installed, nothing downstream matters. This is the first build.
- **Priority 2 — lifecycle/governance measurement ([20](20-scenario.md)/[21](21-assertions.md)).** Drive a real governed run and measure that the governance held. Deferred to "next time."

The clean seam between them: conformance answers *"can the agent USE UACP?"*; the lifecycle measurement answers *"when it does, does the governance hold?"*.

## What the lifecycle test asserts (Priority 2 — the crux, see [21](21-assertions.md))

Because a weak local model **will not reliably finish the lifecycle**, "the agent reached RESOLVE" cannot be the pass/fail gate. Assertions are **tiered**: **governance-correctness is the HARD gate** (whatever the agent did, the kernel never let an invalid state through — no skipped transition, dirty VERIFY blocked, no self-attested closure); **agent-completion is a SOFT, scored signal**. The harness can be GREEN on a run where the model floundered — because the *governance* held — and that is the correct semantics for an acceptance test of a governance framework.

## To expand
- The CI/scheduling story (nightly vs pre-release tag) and where the containers run (self-hosted runner vs the box).
- How the harness result feeds the future benchmark dashboard.
