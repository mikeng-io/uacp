---
type: decision
title: Build plan — Hermes-first (automated lane), staged; reconciliations; decisions; open questions
description: Staged build with a verification gate per stage. HERMES-FIRST STANDS (mike's two-lanes ruling — the Proving Ground is the fully-automated GHA/release/benchmark lane; the companion/interactive lane is e2e-acceptance, NOT superseded). The panel's drive-channel blocker is resolved INSIDE Hermes-first — the hermes-uacp cell loads the canonical UACP MCP server via `hermes mcp add` (full tool_specs surface; the uacp_guardian plugin supplies hooks; its missing lifecycle tools are noted, not assumed). Stages re-ordered per the panel — the N-replicate pipeline lands at S1; S2's exit softened (verdict retroactive at S3). Pre-req — commit the self-diagnosis spec (currently UNTRACKED) so its supersession can be stamped. Red-pen decisions recorded; three open questions remain.
tags: [plan, stages, hermes-first, two-lanes, reconciliation, red-pen-decisions, open-questions]
timestamp: 2026-07-17
edges:
  - {dst: 00-proving-ground, rel: decides_on, provenance: asserted}
---

# Build plan

## Reconciliations (panel-blocking, resolved by mike's two-lanes ruling — see 00)
- **e2e-acceptance is NOT superseded.** It is the **companion/interactive lane** (Claude, real
  `claude plugin install`, operator-in-the-loop); the Proving Ground is the **automated lane**
  (headless CI/GHA/benchmark). The Proving Ground **absorbs** from it: the model-normalizing
  proxy (12 → our 10.3), the tiered hard-gate/soft-completion assertions (21 → our 30), the
  plugin-conformance probe (13 → S2 below), and the task/scenario layer (→ our 40). On this
  bundle's merge, a cross-reference lands in `design/e2e-acceptance/` naming the two lanes.
  **Decision-log entry (at merge):** e2e's roadmap deferral ("stop hand-building a bespoke
  harness; dogfood the acceptance run through UACP's lifecycle") concerned the *acceptance*
  purpose; the Proving Ground builds a harness for the *automated* purpose the deferral did
  not cover — recorded explicitly so the deferral is scoped, not silently reversed.
- **self-diagnosis is superseded-and-absorbed** (driver dies, observer lives — 00/30).
  **Pre-req (P0 below):** its `spec.md`/`prior-art.md` are currently **UNTRACKED** (they exist
  only in the `.worktrees/self-diagnosis-design/` working tree — verified by the panel); they
  must be committed to their branch before a supersession stamp can mean anything.
- **The Hermes drive channel is a named prerequisite, not an assumption — and it is the
  NATIVE plugin.** (Corrected per Codex on this PR: an earlier claim that the plugin exposes
  a partial surface was **stale** — `uacp_guardian.register()` registers every `tool_specs()`
  entry, lifecycle tools included, and `tests/integration/test_tool_registry_parity.py` pins
  Hermes registrations == the MCP registry, 18 tools.) The REAL gap is **runtime loading**:
  the plugin is code-complete in-repo but not installed into a given Hermes instance (this
  host's `hermes plugins list` does not show it). So the S2 prerequisite is: **bake the
  plugin's installation/registration into the cell image** and verify it via the
  plugin-conformance probe (a cell where the surface fails to load is a probe FAIL with
  evidence). The canonical MCP server (`hermes mcp add`, image carries `uv`) remains a
  **fallback drive channel** if in-image plugin registration proves brittle — an S2 decision
  recorded either way, not a repair for a missing capability.

## Stages (each gated by its own verification; re-staged per the panel)
- **P0 — commit the self-diagnosis spec** to `docs/self-diagnosis-design` (or fold its text
  into this bundle's 30 with attribution) so the supersession stamp is real.
- **S0 — OpenAB lift spike** *(blocking; 20)*: (a) `crates/openab-agent` separability;
  (b) one agent end-to-end over ACP from a bare harness; (c) container→host-ollama env-contract
  reachability **incl. a multi-turn tool-calling check of ollama's OpenAI-compat path**;
  (d) **server-side adapter verification** — `hermes acp` (confirmed to exist, v0.17.0) runs a
  real session; Zed's `claude-code-acp` evaluated for the claude cells. Exit: a decision
  record — lift-the-crate vs reimplement-the-thin-ACP-client; and a go/no-go per agent cell.
- **S1 — `hermes-bare` smoke cell + the replicate pipeline**: runner spawns the SUT container,
  injects a trivial task, local model answers, trail exported — **N times, aggregated**: the
  replicate/aggregation pipeline is built HERE (40's statistics law), against the cheap smoke
  tier, before anything is scored. Prereqs: pull the official `unsloth/Qwen3.6-35B-A3B-GGUF`
  quant (40).
- **S2 — `hermes-uacp` cell**: bake the canonical MCP server + hooks + `uv` into the image
  (prerequisite above); **plugin-conformance probe first** (absorbed from e2e-13: is the tool
  surface actually loaded and actionable? — a failed load is a probe FAIL with evidence, and
  nothing downstream is attempted); then the agent drives a governed run through the real tool
  surface. Exit (softened per the panel): **terminal state reached + full trail exported** —
  the conformance *verdict* on that trail is applied retroactively when S3 lands. This is
  still the outstanding real agent-through-tools dogfood; it just doesn't grade itself.
- **S3 — observer + calibration**: port L1–L4 as CODE gates over the exported trail (with the
  tiered hard/soft split, the schema contract test, and the kernel fault-flag mechanism — 30);
  run the clean baseline AND the planted-fault runs. Exit: the decoupling litmus passes and
  every planted fault is caught. *(Only now do verdicts mean anything — including S2's,
  retroactively.)*
- **S4 — `claude-*` cells + first scored sweep**: add the Claude container (native Anthropic
  wiring; auth question below), run the matrix with declared N over the initial task suite,
  produce the first aggregated scoreboard (40).
- **S5+ (backlog)**: more cells (Pi, opencode — Dockerfile + verified ACP adapter each),
  task-suite growth, results-ledger schema hardening, microVM isolation tier (10), CI
  integration (smoke tier per-push at most; scored sweeps stay operator-triggered batch — 40's
  time budget).

Council checkpoints per repo convention; S2 and S3 exits are evidence-bearing artifacts, not
assertions.

## Naming (decided)
**Proving Ground** — confirmed by mike 2026-07-17. Repo slug `proving-ground`.
(Alternatives recorded: *Dynamometer/Dyno*, *Crucible*.)

## Decided at red-pen (mike, 2026-07-17)
1. **The bench lives IN THIS REPO** — top-level `tools/proving-ground/`; the observer imports
   NOTHING from `skills/` and consumes only the exported trail, pinned to kernel truth by the
   schema contract test (30).
2. **Model wiring = the provider env contract** (10.3): OpenAI-compatible/Anthropic env vars +
   key; local ollama now, cloud later; cross-flavor via the absorbed e2e proxy.
3. **LLM-judge quarantine confirmed** (40).
4. **Two lanes** (this node, 00): Proving Ground = fully-automated (GHA/release/benchmark);
   e2e-acceptance = companion/interactive — complementary, both live. **Hermes-first stands**
   because the automated lane needs unattended, auth-free, token-free cells.

## Open questions (remaining)
1. **Rust vs Python for the runner glue.** Lean: lifted ACP/transport stays Rust as a thin CLI
   the Python bench orchestrates.
2. **Claude Code in-container auth for the automated lane** — API-key cell is straightforward;
   subscription auth likely excludes claude cells from unattended CI (they may stay
   operator-triggered / companion-lane-verified). S4 concern; flag early.
3. **CI cadence** — smoke tier per-push vs nightly; scored sweeps operator-triggered
   (40's wall-clock budget makes per-push scored sweeps a non-option). Decide at S5.
