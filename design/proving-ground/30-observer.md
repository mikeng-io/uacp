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
decide — itself a finding (*make the mechanism observable*). Run-level: engine-conformant iff
L1–L4 all PASS. Every finding cites its trace signal (non-vacuity). In telos terms
(`design/telos/20`): the observer is a **deterministic gate** — critique base case #1 — which
is precisely why an LLM judge is banned here: it would demote the bench's floor from
deterministic to semantic and reintroduce the regress the base case exists to stop.

## The decoupling litmus *(kept)*
- garbage plan + working engine → **PASS** (content is not the concern)
- good plan + deadlocked gate → **FAIL**

A content-auditor gets these backwards. This litmus is the acceptance test for the observer
itself.

## Calibration — planted faults, mandatory *(kept)*
1. **Clean run** → L1–L4 all PASS (baseline).
2. **Inject a KNOWN engine break** (e.g. force a gate always-pass) → the matching L **must
   FAIL**. A prover never run against a known-broken engine is theater.

Calibration doubles the run count and is cheap on local cells; it is not optional and it is
re-run whenever the observer's checks change (the observer, too, sits in a conformance loop).

## Signals *(kept, plus the container boundary)*
- **Engine self-record** — gate ledger, `.uacp/state/runs/…` — checked FOR mechanism function,
  never trusted as narrative.
- **Machine ground truth the SUT cannot author** — the ACP transcript captured on the RUNNER
  side of the boundary, workspace git log/diff, Guardian hook log, container resource/exit
  records. The container boundary strengthens self-diagnosis here: ground truth is now
  collected *outside* the jail by construction, not by convention.

## What self-diagnosis's open precondition becomes
Its blocker — *"the `uacp_*` governed writers were not present; resolve before the first
run"* — stops being an open question and becomes **cell configuration**: the +UACP cells bake
the plugin/MCP surface into the image (20). A cell where the surface fails to load is an
**L4 FAIL with evidence**, not an excuse.
