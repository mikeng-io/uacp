---
type: design
title: Roadmap — walking skeleton first, then scale
description: The build order — design bundle first, then a walking skeleton (mike's sequencing). What the minimal end-to-end pipe is, what each later increment adds, and what is deliberately deferred — so v1 proves the pipe on the simplest case before scenarios/runtimes/benchmark scale.
tags: [e2e, roadmap, walking-skeleton, build-order]
timestamp: 2026-06-26
edges:
  - {dst: 00-intent, rel: sequences, provenance: asserted}
  - {dst: 11-runner-adapter-seam, rel: depends_on, provenance: derived}
---

# Roadmap — walking skeleton first

## Prerequisite (parallel track, not this bundle)

The Claude Code adapter (the `runner:claude-code` install path + whatever lifecycle exposure it lands) is built in a **separate session**. The walking skeleton **consumes** it; if it is not ready, the skeleton stubs the runner with a scripted driver to prove the harness/topology halves first.

## Increment 0 — walking skeleton (the first build)

The thinnest END-TO-END pipe, one scenario, governance-correctness only:

- `harness` brings up `model`(Ollama) + `proxy` + `runner:claude-code`.
- one **should-block** scenario (`unchecked-target`) — chosen FIRST because it passes even if the agent barely functions (the kernel blocks regardless), so the skeleton proves the *pipe* without depending on model competence.
- assert **Tier 1** only (the run is correctly blocked with `GP_UNCHECKED_TARGET`); emit a minimal `result.json`.
- run it by hand (a `make e2e` / CLI), NOT in CI yet.

Done when: one command spins the stack, installs UACP into a real agent, drives it far enough to hit the gate, and the harness reads state + asserts the block. That single green proves install + plugin + MCP + lifecycle + gate through the real path.

## Increment 1 — the golden path + tiered scoring

Add the happy-path scenario; add **Tier 2** completion scoring + the full `result.json` ([22](22-benchmark.md)). Now a run yields a verdict + a score.

## Increment 2 — the backend seam

Make the model backend config-selected ([12](12-model-backend-seam.md)); prove the same scenario against {Ollama} and {an OpenAI/Anthropic endpoint} via the proxy. Pins backend-neutrality.

## Increment 3 — scenario ladder + scheduling

The graduated scenario set ([20](20-scenario.md)); wire as a **periodic / pre-release** job (not a merge gate). The acceptance suite now runs unattended.

## Increment 4 — the second runtime

`runner:hermes` (or codex) behind the same seam ([11](11-runner-adapter-seam.md)) — reusing scenarios/assertions/scoring verbatim. Proves the runtime-neutral claim and lights up the cross-runtime benchmark.

## Deliberately deferred

- Leaderboard / aggregation UI (the corpus accrues first).
- Container-grade hardening beyond compose isolation.
- A capability floor study for the smallest viable model.

## Build/improvise/update note

Most of Tier-1 is **IMPROVISE**: `assert_governance_correct(...)` reuses the invariant logic the in-process integration tests already encode — single source of truth for "what the kernel promises," read here off real-stack state. The genuinely NEW build is the **topology + the two seams + the result schema**; the assertions are mostly existing invariants re-pointed at a containerized run.
