---
type: design
title: Assertions — tiered (governance-correctness HARD, agent-completion SOFT)
description: The decision that shapes the harness — what makes a run pass. Governance-correctness is the hard gate (read deterministically from serialized state); agent-completion is a soft, scored, non-blocking signal. Defines each tier's concrete checks and why a flailing-agent run can still be GREEN.
tags: [e2e, assertions, governance-correctness, tiered, fail-closed]
timestamp: 2026-06-26
edges:
  - {dst: 20-scenario, rel: depends_on, provenance: derived}
  - {dst: 00-intent, rel: decides_on, provenance: asserted}
---

# Assertions — tiered

> **Priority 2 (next time).** This node is the **lifecycle/governance** measurement — deferred behind plugin conformance ([13](13-plugin-conformance.md), Priority 1). It is designed now so the seam is right, but built after the plugin is proven actionable.

## How this measurement happens, exactly (reuse the kernel's own predicates)

Governance-correctness is **not** re-implemented in the harness. After the container run, the harness opens the produced workspace and calls the SAME engine predicates the kernel uses, off the real serialized state:

- `validate_graph_invariants(ws, run_id, "<phase>_exit")` — coverage / replay / floor / underclaim / open-investigation at each exit.
- `investigation_status(ws, run_id)` / `convergence_status(...)` — the dry/escalate read.
- the run manifest `state_history` — phase-order legality + per-transition gate-ledger evidence.
- the gate ledger + watermark chain — no ungated close, no raw write.

So "how we measure" = **load the container-produced UACP state, run the kernel's own measurement engines on it, assert their verdicts.** Deterministic despite the non-deterministic run, and single-sourced with the in-process integration tests (no second definition of "what the kernel promises" to drift).

## The decision (mike: "both, tiered")

A run's verdict has two tiers with different force:

- **HARD GATE — governance-correctness.** Did the kernel hold? Read deterministically from the serialized UACP state AFTER the run. A violation here **FAILS** the acceptance test. This is the real product guarantee.
- **SOFT SIGNAL — agent-completion.** How far did the agent get, how cleanly? Recorded + scored ([22](22-benchmark.md)), **never blocks**. This is the benchmark signal and a regression *indicator*, not a *gate*.

**A run where the agent floundered but the governance held is GREEN.** For an acceptance test of a *governance framework*, that is the correct semantics: we are certifying that UACP cannot be made to lie, not that a given model is good at UACP.

## Tier 1 — governance-correctness (HARD, deterministic, from state)

Read the final run manifest + gate ledger + investigation ledger + `uacp.check.*` records and assert the INVARIANTS the kernel promises — independent of the agent's path:

- **No phase was skipped** — `state_history` transitions are all Heartgate-valid; no jump.
- **No ungated close** — every transition that advanced carries its gate-ledger evidence; closure has no open `GP_*` block.
- **Verify integrity** — if the run reached/passed VERIFY, every owned done-claim has a `uacp.check.*` (coverage), no frozen check FAILs/ERRORs unaddressed (replay), no open `GP_OPEN_INVESTIGATION`.
- **For should-block scenarios** ([20](20-scenario.md)) — the run is **stuck at the expected block** with the expected violation code, and did **NOT** reach RESOLVE. (Here, blocked == pass.)
- **No raw writes** — state mutated only via governed writers (the manifest/watermark chain is intact).

These are the same invariants the in-process integration tests assert — but here they are read off state produced by the **real installed stack driven by a real agent**, which is the whole added value.

## Tier 2 — agent-completion (SOFT, scored, non-blocking)

A graded signal, recorded for every run, blocking nothing:

- furthest phase reached; reached RESOLVE? (golden path only)
- gate blocks hit and whether the agent *recovered* (re-authored a check, resolved an investigation) vs got stuck.
- count + shape of authored `uacp.check.*` (did it pick appropriate kinds?).
- turns / wall-time / token estimate to completion.

Tier 2 is the benchmark's raw material ([22](22-benchmark.md)) and a *soft* regression alarm (a sudden completion drop on a fixed backend is worth a look) — but it is **expected to be red/partial on weak backends** and so must never gate.

## Why read state, not the transcript

The transcript is non-deterministic and unreliable; the **serialized UACP state is the ground truth** the kernel itself trusts. Asserting Tier 1 from state makes the hard gate deterministic despite the non-deterministic run — the same comprehend→measure→serialize discipline the framework enforces, applied to testing the framework. The transcript informs only Tier 2.

## To expand
- The exact invariant list as a reusable `assert_governance_correct(workspace, run_id, expected_profile)` (shared with the integration tests — single source of truth for "what the kernel promises").
- Scoring weights for Tier 2 (deferred to [22](22-benchmark.md)).
