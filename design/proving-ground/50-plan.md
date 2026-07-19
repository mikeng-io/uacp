---
type: decision
title: Build plan — Hermes-first (automated lane), staged; reconciliations; decisions; open questions
description: Staged build with a verification gate per stage. HERMES-FIRST STANDS (mike's two-lanes ruling — the Proving Ground is the fully-automated GHA/release/benchmark lane; the companion/interactive lane is e2e-acceptance, NOT superseded). The drive channel is the NATIVE uacp_guardian plugin (register() exposes the full tool_specs surface, parity-tested vs MCP; the earlier partial-surface claim was stale) — the S2 prerequisite is baking its installation into the cell image, probe-verified, a failed native probe BLOCKS S2 (the MCP server exists only as a separate debugging cell that cannot satisfy the native exit). Stages re-ordered per the panel — the N-replicate pipeline lands at S1; S2's exit softened (verdict retroactive at S3). Pre-req — commit the self-diagnosis spec (currently UNTRACKED) so its supersession can be stamped. Red-pen decisions recorded; three open questions remain.
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
  plugin-conformance probe (13 → S2 below), and the task/scenario layer (→ our 40). Both
  reconciliation artifacts LAND IN THIS PR (Codex): the scope note on
  `design/e2e-acceptance/30-roadmap.md`'s deferral (the deferral concerned the *acceptance*
  purpose and stands; the automated purpose is a scope it did not cover) and the 2026-07-17
  two-lanes **decision-log entry** — the deferral is scoped in the record, not silently
  reversed.
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
  evidence). The canonical MCP server (`hermes mcp add`, image carries `uv`) exists only as a SEPARATE,
  distinctly-named debugging cell (`hermes-uacp-mcp`) — a failed native probe BLOCKS S2
  rather than falling back (see S2), so an MCP pass can never conceal a broken native plugin.

## Stages (each gated by its own verification; re-staged per the panel)
- **P0 — commit the self-diagnosis spec** to `docs/self-diagnosis-design` (or fold its text
  into this bundle's 30 with attribution) so the supersession stamp is real.
- **S0 — OpenAB lift spike** *(EXECUTED 2026-07-17 — (a)/(d) PASS; (b) protocol-level PASS on host; (c) PARTIAL, env-contract-in-container deferred to S1's entry gate; decision:
  REIMPLEMENT the thin ACP client in Python, mine OpenAB's edge-cases; record:
  `tools/proving-ground/records/S0-decision-record.md`; go: hermes GO, claude GO-adapter/
  auth-gated; see 20)*: as executed — (a) client-transport separability: the ACP client is
  `crates/openab-core/src/acp/` (~2.8k LoC; `openab-agent` turned out to be OpenAB's own
  standalone agent, not the client); (b) one agent end-to-end over ACP from a bare host
  harness (protocol-level PASS; the CONTAINERIZED cell image is deliberately out of S0 scope
  and is S1's entry gate); (c) container→host-ollama env-contract reachability incl. a
  multi-turn tool-calling check of ollama's OpenAI-compat path; (d) server-side adapter
  inventory — `hermes acp` built-in (live-verified, v0.17.0); the Claude adapter OpenAB
  installs is `@agentclientprotocol/claude-agent-acp@0.45.0` (npm). Exit delivered: the
  decision record + per-cell go/no-go.
- **S1 — `hermes-bare` smoke cell + the replicate pipeline**: ENTRY GATE (from S0's honest
  scope): build the hermes cell image and prove the containerized boundary — adapter present
  in-image, ACP round-trip from the runner into the container, and the injected env contract received AND USED inside (a model reply arriving via the injected endpoint).
  Then: runner spawns the SUT container,
  injects a trivial task, local model answers, trail exported — **N times, aggregated**: the
  replicate/aggregation pipeline is built HERE (40's statistics law), against the cheap smoke
  tier, before anything is scored. Prereqs: pull the scored model **`qwen3.6:35b-a3b` from the
  ollama library** (mike's pin — the unsloth hf.co GGUF failed to finalize on the local ollama
  runtime with `Error: 400` at the manifest step, so the ollama-library artifact of the same
  official model is the reproducible pin; record its digest at first pull; 40). **Smoke tier =
  criteria** (>=64K reported context + probe-verified tool-calling + replicate speed), **current
  roster: smoke = `qwen3.5:4b`** (mike's preference 2026-07-18, same family as the scored model;
  probe PASS — 262K context, tool-calling OK), fallbacks `qwen3:30b-a3b` (on-disk) / `gemma4:12b`
  (cross-family). (S0 finding: Hermes enforces a hard 64K context floor — `qwen2.5:3b` (32K) is
  REJECTED at session/new, and a context_length override triggers a SILENT prompt-time refusal
  that a naive harness reads as a pass; every hermes-cell model must report >=64K context, and
  scored-cell ollama configs must serve the 35B model with num_ctx >= 65536).
- **S2 — `hermes-uacp` cell**: bake the **native `uacp_guardian` plugin** into the image —
  installed + registered in the in-image Hermes instance — as the PRIMARY drive channel
  (full `tool_specs()` surface + pre/post-tool hooks; prerequisite above); **plugin-conformance
  probe first** (absorbed from e2e-13: is the tool surface actually loaded and actionable? — a
  failed load is a probe FAIL with evidence, and nothing downstream is attempted); then the
  agent drives a governed run through that native surface. **A failed native probe BLOCKS
  S2** — the stage exit cannot be satisfied over any other channel; the probe failure is
  itself S2's finding (a real drive-channel defect, recorded with evidence) and fixing the
  native integration is the path forward. The canonical MCP server (`hermes mcp add`, image
  carries `uv`) exists only as a **separate, distinctly-named cell** (`hermes-uacp-mcp`) for
  substrate debugging and channel comparison — it **cannot satisfy the native cell's exit**,
  and its results are never aggregated as `hermes-uacp`, because an MCP pass while the native
  plugin is broken would conceal exactly the defect the cell exists to catch. Exit (softened
  per the panel): **native probe PASS + terminal state reached + full trail exported** — the
  conformance *verdict* on that trail is applied retroactively when S3 lands. This is still
  the outstanding real agent-through-tools dogfood; it just doesn't grade itself.
  **S2 also lands egress ENFORCEMENT** (10-topology's per-cell policy is declared-advisory at
  S1: cells carry `egress` and every S1 `meta.json` self-reports `egress_enforced: false`).
  Empirical S1 finding (2026-07-18): `docker network create --internal` blocks host-gateway
  too on Docker Desktop, so "host-model-only" needs the **dual-network proxy sidecar** — SUT on
  an internal network, a forward-proxy container attached to internal + bridge that relays only
  to the cell's declared endpoint, `OPENAI_BASE_URL` pointed at the sidecar. This composes with
  the cross-flavor normalizing proxy (10.3): same sidecar seat, two duties. S2 flips
  `EGRESS_ENFORCED` when it lands; until then bare-bridge runs are pipeline checks, not
  containment-valid results.
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
1. ~~Rust vs Python for the runner glue~~ — **RESOLVED by S0**: the protocol proved small
   enough that the bench + its ACP client are pure Python (`tools/proving-ground/`); the
   separable Rust crate (`openab-core/src/acp/`) is the documented fallback only (20).
2. **Claude Code in-container auth for the automated lane** — API-key cell is straightforward;
   subscription auth likely excludes claude cells from unattended CI (they may stay
   operator-triggered / companion-lane-verified). S4 concern; flag early.
3. **CI cadence** — smoke tier per-push vs nightly; scored sweeps operator-triggered
   (40's wall-clock budget makes per-push scored sweeps a non-option). Decide at S5.
