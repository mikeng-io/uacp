---
type: design
title: The runner-adapter seam — the agent under test (CC now, Hermes/Codex later)
description: The contract that makes the AGENT runtime pluggable so a new runtime is a new container, not a harness rewrite. Defines what the harness requires of any runner image, references the Claude Code adapter (built in a parallel session) as the first implementation, and records the open lifecycle-exposure dependency the harness must tolerate either way.
tags: [e2e, runner, adapter, runtime-neutral, claude-code, hermes, codex, mcp]
timestamp: 2026-06-26
edges:
  - {dst: 10-topology, rel: depends_on, provenance: derived}
---

# The runner-adapter seam — the agent under test

## The contract (what ANY runner image must provide)

The harness core treats the agent as a black box behind a fixed contract. A runner image, given a seeded workspace + a task + a model endpoint, must:

1. **Install UACP** the user-real way for that runtime (a plugin install — not a source mount).
2. **Expose UACP's governed tools** to the agent (the MCP server / the runtime's tool mechanism).
3. **Drive the lifecycle** when prompted with the scenario task — emit the tool calls that advance TRIAGE → RESOLVE.
4. **Run headless + non-interactive** (no human approval — UACP's Guardian/gates are the control, not a prompt).
5. **Leave the UACP state on the shared workspace volume** and exit; the harness reads state, the runner does not self-assert.

A runner is therefore: `{base image + the agent CLI + the UACP install recipe + an entrypoint that feeds the task and points at the model endpoint}`. Everything runtime-specific lives here; the harness never branches on runtime.

## First implementation: Claude Code (consumed, not specified)

The `runner:claude-code` image wraps the Claude Code CLI + UACP installed as a CC plugin (`.claude-plugin/`) + the UACP MCP server registered (`--mcp-config`) + `--dangerously-skip-permissions` + `ANTHROPIC_BASE_URL` → the proxy ([12](12-model-backend-seam.md)).

**The Claude Code adapter itself is built in a PARALLEL session.** This bundle DEPENDS ON it as a black box and does not re-specify it. Whatever that work decides, the harness consumes it.

## The open dependency the harness must tolerate

UACP today exposes the governed **writers** as MCP tools but **not the lifecycle ops** (init / transition / register / finalize) — those run via the `uacp-state` skill scripts (where the verify gate fires). So a runner advances phases either by (i) the skill scripts over the agent's shell, or (ii) lifecycle ops newly exposed as tools (if the parallel adapter session adds them).

**The seam is defined so EITHER resolution works on the ASSERTION side:** the harness asserts on the resulting *state*, not on *how* the transition was issued — so the adapter session can choose the mechanism and the harness needs no change to *measure*.

**But the DRIVE side is a HARD Priority-2 dependency, not a symmetric "either works" (council).** The runner still has to *issue* init/transition/register/finalize somehow, and today there is **no MCP/tool channel** for them — they exist only as Python callables in `state_machine.py`. So Increment 1 (the lifecycle pipe) is **blocked until** the adapter session delivers a real drive channel: either (i) lifecycle ops exposed as governed tools, or (ii) a sanctioned way for the runner to invoke the `uacp-state` skill scripts in-container. Asserting on state does not conjure that channel. Priority 1 (plugin conformance) does **not** need it — which is another reason it goes first.

## Why this seam is the multi-runtime future

Hermes / Codex become `runner:hermes` / `runner:codex` — same contract, different install recipe + entrypoint + tool mechanism (Hermes already consumes `tool_specs()`; Codex via its own bridge). The scenario, the assertions, and the scoring are reused verbatim. That reuse is the whole point of the seam.

## To expand
- The exact env/volume interface the harness passes every runner (task file, workspace path, model URL, result path).
- A conformance check: a tiny "does this runner satisfy the contract" probe run before the real scenario, so a broken runner image fails fast and legibly.
