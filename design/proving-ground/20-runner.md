---
type: analysis
title: The runner — mined from OpenAB (ACP transport + per-agent containers)
description: The runner is MINED from OpenAB (github.com/openabdev/openab, Rust, MIT, 0.9-beta, active) — S0 EXECUTED 2026-07-17, decision REIMPLEMENT the thin ACP client in Python (the client transport is crates/openab-core/src/acp/, ~2.8k LoC — NOT openab-agent, which is OpenAB's own standalone agent; the crate remains the documented fallback). Keep mining the per-agent Dockerfiles (Dockerfile.claude/.hermes/.codex/.opencode/.pi; Claude adapter = @agentclientprotocol/claude-agent-acp@0.45.0 npm) + the sandbox posture; DROP the chat/ops front-end, k8s/helm, and the AWS agentcore. Model endpoint via the cell env contract (host.docker.internal:11434 + pinned model_id for local cells). S0 scope note — the e2e check passed at protocol level on the HOST; the containerized boundary is S1's entry gate. Side effect — one ACP adapter can eventually collapse the per-runtime bridge sprawl.
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
  (`claude-agent-acp`, `hermes-acp`, `codex-acp`, `gemini --acp`, opencode, **Pi**, …). **S0
  correction:** the client transport lives in `crates/openab-core/src/acp/` (~2.8k LoC core:
  connection/protocol/pool; 5 trivial externals + 1 config struct) — NOT `openab-agent`,
  which is OpenAB's own standalone native agent (a server-side ACP speaker), workspace-
  excluded. See `tools/proving-ground/records/S0-decision-record.md` (a).
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
container, **and (d) the SERVER-side per-agent ACP adapters actually exist and run** — the
panel's key correction: the client fallback below de-risks only the client; the real external
dependency is each agent's ACP adapter binary. Verified (S0, live): **Hermes ships `hermes
acp` built-in** (v0.17.0, `--check` OK, full round-trip with a genuine model reply proven from
a ~150-line bare harness); the Claude adapter OpenAB actually installs is
**`@agentclientprotocol/claude-agent-acp@0.45.0`** (npm; the earlier "it's Zed's
claude-code-acp" note was inverted — corrected per `Dockerfile.claude:24-27`); Codex/Pi
adapters are asserted by OpenAB and unverified. An agent with no working ACP adapter simply
has no cell until one exists — that is a cell-inventory fact, not a substrate failure.
If (a) fails, fall back to *pattern-mining* (reimplement the thin ACP client — the protocol is
small) rather than dragging the broker in; if (d) fails for Hermes, S1 is blocked and the plan
re-sequences.

> **S0 EXECUTED (2026-07-17) — decision: REIMPLEMENT the thin ACP client.** Checks (a)/(d)
> PASS in full; (c) PARTIAL (container→host network + host-side tool-calling verified; the
> runner-injected env contract in-container is UNVERIFIED); check (b) PASS **at protocol
> level on the host** (`hermes acp` spawned
> directly — no cell image was built, per the record's honest disclosure), so the
> **containerized boundary is NOT yet verified**: building and running the actual hermes cell
> image (adapter present, env contract received in-container) is **S1's entry gate**, not a
> settled fact. (Record: `tools/proving-ground/records/S0-decision-record.md`; raw ACP
> exchange: `S0-acp-exchange.log`.) The protocol proved small — a ~150-line stdlib Python harness did
> the full client (initialize → session/new → prompt → streaming reply) against the real
> `hermes acp` with a genuine model round-trip; the hard dependency is the per-agent adapter
> *binaries* (spawned either way), not OpenAB's transport code. The lift target it corrects:
> the separable client is `crates/openab-core/src/acp/` (~2.8k LoC) and remains the documented
> fallback. What we MINE rather than re-derive: `openab-core/src/acp/connection.rs:845-885`
> (`build_permission_response` — the per-agent permission option-ID map), session-resume,
> watchdog, and stale-response handling. This resolves 50's open question #1: the bench and
> its ACP client are **Python** (`tools/proving-ground/`); no Rust CLI is lifted.
