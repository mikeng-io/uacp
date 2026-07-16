---
type: decision
title: Build plan — Hermes first, staged; naming; supersession; open questions
description: Staged build with a verification gate per stage — S0 OpenAB lift spike; S1 hermes-bare smoke cell (runner+container+host model, no UACP, no scoring); S2 +UACP cell (plugin/MCP baked in — the first REAL agent-through-tools dogfood); S3 observer port + planted-fault calibration; S4 claude cells + first matrix sweep. Name decided as working title — PROVING GROUND (alternatives recorded). Supersedes design/self-diagnosis's driver, absorbs its observer (mark on merge). Open questions listed for red-pen.
tags: [plan, stages, hermes-first, naming, supersession, open-questions]
timestamp: 2026-07-17
edges:
  - {dst: 00-proving-ground, rel: decides_on, provenance: asserted}
---

# Build plan

## Stages (each gated by its own verification, per the loop)
- **S0 — OpenAB lift spike** *(blocking; 20)*: clone; prove `crates/openab-agent` separability;
  run ONE agent (`Dockerfile.hermes`) end-to-end over ACP from a bare harness; prove
  container→`host.docker.internal:11434` reachability. Exit: a decision record —
  *lift-the-crate* vs *reimplement-the-thin-ACP-client* (pattern-mining fallback).
- **S1 — `hermes-bare` smoke cell**: runner spawns the SUT container, injects a trivial task,
  local model answers, trail exported. No UACP, no scoring — proves the substrate.
  (Environment verified present 2026-07-16: hermes-agent v0.17.0, Docker 29.x running, ollama
  with qwen3-class models on the host.)
- **S2 — `hermes-uacp` cell**: bake the UACP plugin/MCP/hook surface into the image; the agent
  drives a governed run through the REAL tool surface. Exit: one governed run reaches RESOLVE
  agent-through-tools — **the outstanding real dogfood**, and the first closure of
  self-diagnosis's open precondition (30).
- **S3 — observer + calibration**: port L1–L4 as CODE gates over the exported trail; run the
  clean baseline AND the planted-fault runs (30). Exit: the decoupling litmus passes and every
  planted fault is caught. *(Only now do verdicts mean anything.)*
- **S4 — `claude-*` cells + first sweep**: add the Claude Code container (egress: Anthropic API
  only), run the 4-cell matrix over the initial task suite, produce the first scoreboard (40).
- **S5+ (backlog)**: more cells (Pi, opencode — a Dockerfile + adapter each), task-suite
  growth, results-ledger schema hardening, microVM isolation tier (10), CI integration
  (the regression-bench role, 40).

Council checkpoints per repo convention: this bundle (pre-governance) → red-pen → PLAN-gated
build; S2 and S3 exits are evidence-bearing artifacts, not assertions.

## Naming (decision, working title)
**Proving Ground** — where an engine is tested under real conditions; covers both readouts;
repo slug `proving-ground`. Alternatives considered: *Dynamometer/Dyno* (closest to the
engine-prover lineage, narrower), *Crucible* (evocative, less precise). Rename is cheap until
S0 lands; mike has final say.

## Supersession (executed on this bundle's merge)
`design/self-diagnosis` (branch `docs/self-diagnosis-design`, unmerged): mark its spec
**superseded-by → design/proving-ground** for the driver/sessions sections, **absorbed-into →
30-observer** for the L1–L4/calibration/litmus core (its intellectual content survives; only
its manual two-context driver dies). The `engine-prover` working name retires with it.

## Open questions (for red-pen)
1. **Where does the bench live?** Same repo (`bench/` or `tools/proving-ground/`) vs sibling
   repo. Same-repo favors the regression-bench role (CI can run S1 smoke); sibling keeps the
   observer maximally outside. Lean: same repo, separate top-level dir, observer imports
   nothing from `skills/`.
2. **Rust vs Python for the runner glue.** The mined crate is Rust; the observer and UACP
   tooling are Python. Lean: keep the lifted ACP/transport in Rust as a thin CLI the Python
   bench orchestrates — avoids rewriting the crate and keeps the observer in the ecosystem the
   trail parsers already live in.
3. **Claude Code in-container auth** — API-key cell is straightforward; a subscription-auth
   cell may need a different container posture. S4 concern; flag early.
4. **Codex-in-CI interplay** — whether PR CI runs an S1 smoke per push or the bench stays
   operator-triggered. Cost-driven; defer to S5.
