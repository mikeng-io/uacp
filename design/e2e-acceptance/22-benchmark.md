---
type: design
title: Benchmark — the structured scored-result artifact
description: The forward-looking seam that turns each acceptance run into a comparable, scored record so the same harness becomes a cross-agent / cross-model UACP-competence benchmark without re-architecture. Defines the result schema, what is comparable vs not, and that v1 only EMITS it (no leaderboard).
tags: [e2e, benchmark, scoring, result-schema, runtime-comparison]
timestamp: 2026-06-26
edges:
  - {dst: 21-assertions, rel: extends, provenance: derived}
---

# Benchmark — the structured scored-result artifact

## The future, seamed in now (mike: "we can turn this into a benchmark")

Every acceptance run emits ONE structured `result.json` — the Tier-1 verdict + the Tier-2 signals + the full provenance of *what was tested* — so that the identical harness, run across `{agent} × {backend} × {scenario}`, yields a comparable corpus. v1 only **emits and stores** this; ranking/dashboards are later. Designing the record now is what avoids re-running history to score it.

## The record (shape, not final schema)

```yaml
result:
  harness_version: ...
  scenario: {id, version, profile: golden|should-block-<kind>}
  runner:  {runtime: claude-code|hermes|codex, version, install: plugin}   # the 11 seam
  backend: {api_flavor, model_id, base_url_kind: local|remote}             # the 12 seam
  run:     {run_id, started, duration_s, turns}
  tier1_governance:                  # the HARD gate — the pass/fail
    pass: bool
    invariants: [{name, status: pass|fail, evidence}]   # phase-order, no-ungated-close, verify-integrity, ...
    expected_block: {code, hit: bool}                   # for should-block scenarios
  tier2_completion:                  # the SOFT score — never gates
    furthest_phase: triage|...|resolve
    reached_resolve: bool
    checks_authored: [{kind, target, verdict}]
    blocks_hit: [{code, recovered: bool}]
    score: 0..1                      # weighted; comparable ONLY within a fixed backend+scenario
```

## What is comparable — and what is NOT (the integrity rule)

- **tier1_governance.pass** is comparable across everything — it is the binary "did UACP hold." A backend/agent can only ever make governance *fail*; it cannot make a worse model "look governed."
- **tier2_completion.score** is comparable **only within a fixed `{backend, scenario}`** — a stronger model scoring higher is expected and uninteresting across backends. The schema records backend+scenario with every result precisely so a future leaderboard cannot accidentally compare across them.

## Anti-gaming (consistent with the framework's own thesis)

The score is computed by the **harness from serialized state**, never self-reported by the runner — the same "no self-attestation" rule UACP enforces on agents, applied to the benchmark. A runner cannot inflate its own score; it can only leave state the harness reads.

## To expand
- The Tier-2 scoring weights (recovery-after-block should weigh heavily — it is the loop-engineering signal UACP cares about).
- Where results are stored/aggregated (a results volume → later an artifact store) and the minimum N for a stable per-cell score given the non-determinism.
