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

## Increment 0 — PLUGIN CONFORMANCE (the first build; mike's Priority 1)

Prove the **installed plugin is actionable** — no lifecycle yet ([13](13-plugin-conformance.md)):

- `harness` brings up `model`(Ollama) + `proxy` + `runner:claude-code` and **installs UACP as a plugin** in the runner.
- comprehend the plugin manifest → the declared capabilities; **probe each is actionable** (MCP `tools/list`==`tool_specs()` + a read-only `tools/call`; skills resolve + parse; hooks fire; commands dispatch); emit `conformance.json`.
- assert: **every declared capability is actionable** (fail-closed — a probe that can't run is a FAIL).
- run it by hand (a `make e2e-conformance` / CLI), NOT in CI yet.

Done when: one command spins the stack, installs UACP into a real agent container, and the harness proves every plugin feature is live. This is the foundation — if the plugin doesn't function installed, nothing downstream is meaningful.

## Increment 1 — PRIORITY 2: the lifecycle should-block pipe

NOW drive a lifecycle. One **should-block** scenario (`unchecked-target`) — chosen first because it passes even if the agent barely functions (the kernel blocks regardless), proving the *lifecycle pipe* without depending on model competence. Assert **Tier 1** governance-correctness ([21](21-assertions.md)); the run is correctly blocked with `GP_UNCHECKED_TARGET`.

## Increment 2 — the golden path + tiered scoring

Add the happy-path scenario; add **Tier 2** completion scoring + the full `result.json` ([22](22-benchmark.md)). A run now yields a verdict + a score.

## Increment 3 — the backend seam

Make the model backend config-selected ([12](12-model-backend-seam.md)); prove the same run against {Ollama} and {an OpenAI/Anthropic endpoint} via the proxy. Pins backend-neutrality.

## Increment 4 — scenario ladder + scheduling

The graduated scenario set ([20](20-scenario.md)); wire as a **periodic / pre-release** job (not a merge gate). The acceptance suite runs unattended.

## Increment 5 — the second runtime

`runner:hermes` (or codex) behind the same seam ([11](11-runner-adapter-seam.md)) — reusing conformance/scenarios/assertions/scoring verbatim. Proves the runtime-neutral claim and lights up the cross-runtime benchmark.

## Deliberately deferred

- Leaderboard / aggregation UI (the corpus accrues first).
- Container-grade hardening beyond compose isolation.
- A capability floor study for the smallest viable model.

## Build/improvise/update note

Most of Tier-1 is **IMPROVISE**: `assert_governance_correct(...)` reuses the invariant logic the in-process integration tests already encode — single source of truth for "what the kernel promises," read here off real-stack state. The genuinely NEW build is the **topology + the two seams + the result schema**; the assertions are mostly existing invariants re-pointed at a containerized run.
