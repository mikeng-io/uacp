---
type: analysis
title: The runner — mined from OpenAB (ACP transport + per-agent containers)
description: The runner is MINED from OpenAB (github.com/openabdev/openab, Rust, MIT, 0.9-beta, active) — lift the ACP-transport core (crates/openab-agent, JSON-RPC over stdio + session pool) and the per-agent Dockerfiles (Dockerfile.claude/.hermes/.codex/.opencode/.pi already exist, plus its mandated sandbox posture); DROP the chat/ops front-end (src/ Discord/Slack/Telegram dispatcher), k8s/helm, and the AWS agentcore. Model endpoint injected via the agent env (host.docker.internal:11434 for local cells). Side effect — one ACP adapter can eventually collapse the per-runtime bridge sprawl. Verification spike required before lift (crate separability; one Dockerfile run end-to-end).
tags: [runner, openab, acp, dockerfiles, mined-not-adopted, transport]
timestamp: 2026-07-17
edges:
  - {dst: 10-topology, rel: realizes, provenance: asserted}
---

# The runner (mined from OpenAB)

## Source and verdict
**OpenAB** (`github.com/openabdev/openab`) — Rust, MIT, `0.9.0-beta`, actively developed
(release Jul 2026). A chat→agent broker whose two load-bearing parts are exactly the runner's
two hard problems, already built:

- **Universal ACP transport** — every agent invoked identically over ACP stdio JSON-RPC
  (`claude-agent-acp`, `hermes-acp`, `codex-acp`, `gemini --acp`, opencode, **Pi**, …), living
  in `crates/openab-agent` (transport + session pool, with tool-call / thinking / permission
  auto-reply handling).
- **Per-agent containers** — `Dockerfile.claude`, `Dockerfile.hermes`, `Dockerfile.codex`,
  `Dockerfile.opencode`, `Dockerfile.pi`, … plus `Dockerfile.unified`; its DESIGN mandates
  sandbox-only containment (process isolation, read-only root, agent never outside the jail).

**Verdict: mine, don't adopt** (consistent with the 2026-06-25 research note). Lift the crate +
the Dockerfiles + the sandbox posture; **drop** `src/` (the Discord/Slack/Telegram dispatcher
and ops surface), `k8s/`/`charts/`, and `agentcore/` (AWS Bedrock). UACP is a governance plane,
not a chat surface; the Proving Ground needs the boundary-crossing machinery only.

## What the runner does (and only this)
1. **Bake** the cell image: agent runtime + (per cell) the UACP plugin/MCP/hooks + pinned
   dependencies. Images are pre-baked so runs make no registry calls (10, egress).
2. **Spawn** a fresh SUT container per run: clean task workspace (pinned git ref), cell env
   (model endpoint / API key injected via the agent's `env` map — OpenAB's existing pattern),
   egress policy applied.
3. **Drive** over ACP stdio: inject the task prompt, relay permission auto-replies per the cell
   policy, stream the transcript out.
4. **Collect**: on terminal state (or watchdog timeout — an L3 signal, not a crash), export the
   trail for the observer (30): workspace git log + diff, `.uacp/` state, gate ledger,
   transcript, hook log, resource counters.

The runner **knows nothing about scoring** — it returns artifacts, never judgments (the seam
between runner and observer is the same declared-vs-witnessed seam the framework governs).

## Cells are containers
Adding an agent = adding a Dockerfile + an ACP adapter — both of which OpenAB already carries
for every runtime currently on the roadmap (including Pi and opencode). ±UACP = same image with
the plugin surface toggled. The "Pi vs Hermes adoption" question dissolves into cell inventory.

## Side effect worth naming
UACP's per-runtime bridges (claude/codex/gemini/hermes/kimi/opencode/reasonix references) each
re-solve dispatch. A proven ACP runner is the seed of **one ACP adapter** replacing that sprawl
— out of scope here, but the runner should be built as a reusable library (not a bench-only
script) so that collapse stays open.

## Pre-lift verification spike (blocking S0, 50)
Before any code is lifted: clone OpenAB, confirm (a) `crates/openab-agent` builds/runs without
`src/` (clean separability), (b) one agent (`Dockerfile.hermes`) runs end-to-end over ACP from
a bare Rust harness, (c) the env-injection path reaches `host.docker.internal:11434` from the
container. If (a) fails, fall back to *pattern-mining* (reimplement the thin ACP client —
the protocol is small) rather than dragging the broker in.
