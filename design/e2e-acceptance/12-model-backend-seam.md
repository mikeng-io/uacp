---
type: design
title: The model-backend seam — provider-neutral (Ollama default, OpenAI/Anthropic/local)
description: The contract that keeps the LLM backend pluggable so the harness is not Ollama-bound. Defines backend selection by config, the proxy's normalization role, and the honest reliability boundary (a weak local model proves plumbing + gate-firing, not model competence) that the tiered assertions depend on.
tags: [e2e, model-backend, provider-neutral, ollama, openai, anthropic, proxy]
timestamp: 2026-06-26
edges:
  - {dst: 10-topology, rel: depends_on, provenance: derived}
---

# The model-backend seam — provider-neutral

## Why neutral (mike: "the backend should be neutral")

The harness must not assume Ollama. The same run should be drivable against a **local Ollama model** (the cheap default for long benchmark runs), an **OpenAI-format endpoint**, a **real Anthropic API URL**, or any compatible server — chosen by **config**, never hardcoded. This is what lets one harness serve both "free overnight benchmark" and "pre-release smoke on a strong model."

## The contract

A backend is declared as `{api_flavor, base_url, model_id, auth}`:

- `api_flavor` ∈ {`anthropic`, `openai`, `ollama`} — what the endpoint speaks.
- `base_url` / `model_id` / `auth` — where + which + how (auth may be a dummy token for local).

The **runner** speaks one native flavor (Claude Code speaks `anthropic`). The **`proxy`** ([10](10-topology.md)) normalizes the declared backend INTO the runner's native flavor:

- backend already `anthropic` (real API, or an Anthropic-shaped local server) → proxy is a pass-through.
- backend `openai`/`ollama` → proxy translates `anthropic` ⟷ that flavor (the litellm/router role).

So the matrix is `{runner native flavor} × {backend flavor}`, collapsed to "the proxy makes them meet." Adding a backend = a proxy config, not a harness change. A new runner with a different native flavor = handled by the same proxy in the other direction.

## The honest reliability boundary (load-bearing for [21](21-assertions.md))

A small local model **will not reliably complete a governed multi-tool lifecycle**; even mid models drift on long tool loops, and coding-agent CLIs are tuned for their first-party models. Therefore a backend choice changes **how far the agent gets**, not **whether the test is valid**:

- weak/local backend → the agent likely flounders → the harness is **still GREEN if governance held** (the hard gate) and records a **low completion score** (the soft signal).
- strong backend → higher completion score; the hard gate must STILL hold.

This is exactly why assertions are tiered ([21](21-assertions.md)) and why the benchmark ([22](22-benchmark.md)) records the backend with every result — completion is only comparable *within a fixed backend*.

## To expand
- A minimal capability floor: the smallest model that can plausibly emit valid UACP tool calls at all (below it, even the soft score is noise) — measured, not guessed.
- Whether to pin temperature/seed where the backend allows, to reduce (not eliminate) variance.
- Cost/time budget per backend (the default Ollama profile has none; a real-API profile needs a ceiling).
