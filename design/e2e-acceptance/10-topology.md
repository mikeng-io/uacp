---
type: design
title: Topology — the multi-container compose stack
description: The separate-container topology (model backend, model proxy, runner/agent-under-test, harness orchestrator) and why each is its own service; the data/control flow from "harness starts the stack" to "harness collects the result"; the network + mount boundaries.
tags: [e2e, topology, docker-compose, containers, mcp]
timestamp: 2026-06-26
edges:
  - {dst: 00-intent, rel: realizes, provenance: asserted}
---

# Topology — the multi-container compose stack

## Services (each its own container — mike: "everything in separate containers")

| Service | Role | Pluggable? |
|---|---|---|
| `model` | serves the LLM (default: Ollama; or none, when the backend is a remote URL) | via [12](12-model-backend-seam.md) |
| `proxy` | normalizes the model API to what the runner expects (e.g. Anthropic `/v1/messages` ⟷ OpenAI/Ollama) | via [12](12-model-backend-seam.md) |
| `runner` | the AGENT UNDER TEST — the coding agent with UACP installed as a plugin + the UACP MCP server registered; drives the scenario | via [11](11-runner-adapter-seam.md) |
| `harness` | orchestrator: brings the stack up, seeds the scenario, triggers the run, **collects the result artifact, asserts, scores, tears down** | NO — the neutral core |

The `harness` is the test process (`pytest` or a CLI); the other three are the system under test.

## Control / data flow

```
harness ── compose up ──▶ {model, proxy, runner}
harness ── seed scenario (a task + a fresh UACP workspace volume) ──▶ runner
runner  ── plugin-install UACP, register MCP, drive TRIAGE..RESOLVE ──▶ (model via proxy; UACP tools via MCP; lifecycle via the adapter)
runner  ── write a RESULT ARTIFACT (run manifest + ledger + a result.json) ──▶ shared volume
harness ── read the workspace + result.json, ASSERT (governance-correctness) + SCORE (completion) ──▶ verdict
harness ── compose down ──▶ teardown
```

The **assertion input is the serialized UACP state itself** (the run manifest, the gate ledger, the investigation ledger, the `uacp.check.*` records) on a shared volume — NOT the agent's chat transcript. Governance-correctness is read from state, deterministically, after the (non-deterministic) run. The transcript feeds only the soft benchmark score.

## Boundaries

- **Network.** `runner → proxy → model` only; the runner reaches the model exclusively through the proxy (so the backend is swappable without touching the runner). No outbound internet from `runner` by default (offline-capable acceptance run; closes "did it secretly call a real API").
- **Mounts.** A fresh per-run **workspace volume** (the UACP run lives here; the harness reads it after). The UACP **package** enters the runner the way a user gets it — a plugin install from the published artifact / repo, NOT a source bind-mount (that is the point: test the install).
- **Isolation = containment.** Real-agent code execution (incl. UACP's behavioral plane) is confined to the `runner` container — the container IS the Tier-3 sandbox the in-repo runner cannot be.

## Why separate containers (not one big image)

Each seam swaps independently: change the model backend → only `model`/`proxy` change; change the agent → only `runner` changes; the `harness` (assertions + scoring) never changes. A monolith would couple them and defeat both futures (benchmark, multi-runtime).

## To expand
- Whether `proxy` is always present (it is a no-op pass-through when the backend already speaks the runner's native API).
- Compose profiles for {local Ollama} vs {remote backend} vs {real-agent-strong-model smoke}.
- Resource limits per container (the model container dominates; the runner needs the behavioral-plane timeout budget).
