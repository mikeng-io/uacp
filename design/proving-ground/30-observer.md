---
type: analysis
title: The observer — self-diagnosis's objective core, absorbed
description: The observer is ABSORBED nearly verbatim from design/self-diagnosis (its objective core was right; only its driver was scripted). Content-independent L1-L4 mechanism properties; per-property fail-closed CODE gates (PASS/FAIL/ERROR distinct — NEVER an LLM judge); the decoupling litmus (garbage plan + working engine = PASS; good plan + deadlocked gate = FAIL); MANDATORY planted-fault calibration (a prover never run against a known-broken engine is theater); signals = engine self-record checked for function plus machine ground truth the runner cannot author. Generalized — any throwaway probe task, not the fixed blog.
tags: [observer, l1-l4, fail-closed, planted-fault, calibration, decoupling-litmus, self-diagnosis-absorbed]
timestamp: 2026-07-17
edges:
  - {dst: 10-topology, rel: realizes, provenance: asserted}
---

# The observer (absorbed from self-diagnosis)

> Provenance: `design/self-diagnosis/spec.md` (branch `docs/self-diagnosis-design`). Its
> observer design survives intact; what 00 supersedes is only its *driver* (two manual Claude
> contexts, no tool surface). Kept-verbatim principles are marked.

## Subject under test *(kept)*
The **UACP lifecycle ENGINE** — phases, transitions, gates, governed writers, handoffs — never
the content of any run. The probe task exists to make the engine run; its quality is
explicitly not checked.

## The probe *(generalized)*
Any **throwaway real task** with a pinned workspace (the original fixed "Astro blog" becomes
one row of the task suite, 40). The observer is task-agnostic by construction — its properties
are content-independent.

## The measure — L1–L4 *(kept)*
- **L1 transitions-through-apparatus** — every phase hop went through Heartgate with a real
  evaluation; not bypassed, forced, or skipped.
- **L2 gates-non-vacuous** — each gate actually evaluated and derived a verdict; not
  always-pass, short-circuited, or deadlocked (the PR#96 gate-deadlock class).
- **L3 terminal-reached** — the engine drove to RESOLVE via a legal path; no stall, deadlock,
  or mid-lifecycle error (the runner's watchdog timeout serializes an L3 deadlock as evidence
  rather than a silent hang).
- **L4 plumbing** — governed writers persisted, the ledger appended, handoffs carried state.

## The gate — fail-closed CODE, never an LLM judge *(kept, and now telos-grounded)*
Per property: PASS = held; FAIL = mechanism defect; ERROR = the trail lacks the signal to
decide — itself a finding (*make the mechanism observable*). Every finding cites its trace
signal (non-vacuity). In telos terms (`design/telos/20`): the observer is a **deterministic
gate** — critique base case #1 — which is precisely why an LLM judge is banned here: it would
demote the bench's floor from deterministic to semantic and reintroduce the regress the base
case exists to stop.

**Tiered verdicts (absorbed from e2e-acceptance `21-assertions`, per the panel):** the four
properties do not all carry the same meaning against a weak model, so the run-level verdict is
split:
- **Hard gate — governance-held:** L1 (transitions through apparatus), L2 (gates non-vacuous),
  L4 (plumbing). A violation here is an engine/conformance FAIL regardless of the model.
- **Soft score — completion:** L3 (terminal reached). A weak local model that flounders and
  never reaches RESOLVE *while governance holds* is a **low completion score with
  governance-held = PASS** — not a hard engine FAIL. (Prior art says this will happen:
  e2e-12's own boundary note — small/mid models drift on long tool loops.) L3 remains a hard
  FAIL only when the *engine* stalls (deadlock/illegal path), which the trail distinguishes
  from the *agent* giving up.

**Honesty about L2 (panel):** on a clean run, a correct gate and an always-pass gate emit an
identical trail — per-run L2 is a *structural* check (a verdict exists, evidence is cited,
ERROR when the signal is absent). **Non-vacuity proper is only decidable differentially**, via
the planted-fault runs below; today's gate ledger does not carry the counterfactual fields a
per-run proof would need (that observability gap is itself a standing finding the bench
reports, not hides).

## The decoupling litmus *(kept)*
- garbage plan + working engine → **PASS** (content is not the concern)
- good plan + deadlocked gate → **FAIL**

A content-auditor gets these backwards. This litmus is the acceptance test for the observer
itself.

## Calibration — planted faults, mandatory *(kept, mechanism now specified)*
1. **Clean run** → hard gate PASS (baseline).
2. **Inject a KNOWN engine break** (e.g. force a gate always-pass) → the matching L **must
   FAIL**. A prover never run against a known-broken engine is theater.

**The mechanism (panel: it was missing):** faults are injected via **kernel fault flags** — a
small, test-only fault-injection switch in the UACP runtime (env-triggered, e.g.
`UACP_FAULT=gate_always_pass`), OFF and inert by default, compiled into the *same* +UACP image
rather than a matrix of patched images. The runner flips the env var per calibration cell.
This keeps images pre-baked (10), makes the fault set version-controlled next to the kernel,
and is budgeted as real S3 work (50) — not a platitude. Calibration is token-cheap on local
cells but **wall-clock serial** like everything on the shared host GPU (40's time budget); it
is not optional and re-runs whenever the observer's checks change (the observer, too, sits in
a conformance loop).

## Signals *(kept, with the two-class split of 10)*
- **Runner-side ground truth** (the SUT cannot author it): the ACP transcript captured on the
  RUNNER side of the boundary, container exit/resource records, wall-clock.
- **SUT-authored exports** (weighted evidence): gate ledger, `.uacp/state/runs/…`, workspace
  git log/diff, Guardian hook log — checked FOR mechanism function, cross-checked against the
  runner-side transcript, never trusted as narrative (see 10, "Two classes of trail
  evidence").

**Schema contract test (panel):** the observer imports nothing from `skills/` (50) but must
parse kernel-owned formats (gate-ledger JSONL, `.uacp/state` shapes). To stop copy-drift, the
kernel test-suite exports a **versioned trail fixture** (generated by the real writers) and
the observer's parsers are contract-tested against it — one definition of the format, two
independent consumers. A fixture-version bump the observer doesn't handle is a loud test
failure, not silent mis-grading.

## What self-diagnosis's open precondition becomes
Its blocker — *"the `uacp_*` governed writers were not present; resolve before the first
run"* — stops being an open question and becomes **cell configuration**: the +UACP cells bake
the plugin/MCP surface into the image (20). A cell where the surface fails to load is an
**L4 FAIL with evidence**, not an excuse.
