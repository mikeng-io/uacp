---
type: evidence
title: Evidence — the Trustless #503 autopsy + the T9 verify-as-investigation handoff
description: The failure taxonomy (6 classes) that this method is built to prevent, drawn from a real conformance/verification feature that survived 7 Codex review rounds with bugs still live; and the T9 reframe of Verify as an iterative root-cause investigation. NOT Trustless work — lesson/evidence only.
tags: [verification, evidence, failure-taxonomy, 503, t9]
timestamp: 2026-06-21
edges: []
---

# Evidence — #503 autopsy + T9 handoff

> **Scope guard:** this is a *lesson transferred from another project (Trustless PR #503)*. It is **not** UACP working on Trustless. It is the concrete failure data that motivates the [primitive](00-the-primitive.md) and the [generative gate](10-generative-gate.md).

## The failure taxonomy (what verification kept doing wrong)

A verification feature went through **7 rounds** of automated (Codex) review and still shipped live bugs. The failures cluster into six classes — each is a place the `measure` discipline was missing:

| Class | Name | What happened | The discipline it violates |
|---|---|---|---|
| **A** | fail-open / silent-pass | a check that errors or finds nothing is treated as PASS | `measure` must keep PASS/FAIL/**ERROR** distinct; ERROR ≠ PASS |
| **B** | weak-proxy | `grep`-for-a-string stands in for "the thing actually works" | a measurement must bind to the real property, not a textual shadow |
| **C** | reality-binding gap | the check runs against a mock/spec, never the real artifact/infra | `bind` (the gate's reality step) was skipped |
| **D** | coverage-gap | only some of the targets were checked; the rest silently unverified | targets must be *enumerated from the content*, not hardcoded |
| **E** | env-fragility | the check passes/fails on environment, not on the code under test | the measurement wasn't isolated from incidental state |
| **F** | spec↔runner drift | the declared criteria and the executed checks diverge over time | criteria must be *serialized* and the runner replays them, not a parallel hand-coded set |

Each class maps to a discipline in [00-the-primitive](00-the-primitive.md): A/E/F are `measure`+`serialize` failures; B/C/D are `comprehend`→`measure` generation failures (the checks weren't *derived from the content*) — exactly what the generative gate fixes.

## The T9 handoff — Verify as investigation, not a checklist

The companion lesson: **redesign Verify as an iterative root-cause investigation**, on a systematic-debugging + sequential-thinking mindset — not a one-pass checklist. Its moves (developed in [11-harness](11-harness.md) and [10-generative-gate](10-generative-gate.md)):

`ENUMERATE → ROUTE → BIND → RUN → RECONCILE → ESCALATE`, wrapped in a **convergence loop** with adaptive depth, written to a **revisable investigation ledger** ([13-investigation-ledger](13-investigation-ledger.md)), and **phase-parameterized**. `enumerate/route/bind` are the generative (content-derived) moves; `run/reconcile/loop/escalate` are the fixed harness.

## To expand
- The per-round diff of #503: which class each round failed to close, and why a round "fixed" a symptom but not the class.
- The mapping table: failure class → which UACP gate/discipline closes it → which node specifies it.
