---
type: design
title: Layer 2 — the Generative Gate (comprehend → measure → serialize)
description: The dynamic gate whose verification ACTIONS are generated from the artifact's content/context, not hardcoded. The understanding→measurement→serialize operation; its trustless property (semantic generates, deterministic runs, generation recorded); the antidote to #503's weak-proxy + coverage-gap classes.
tags: [verification, generative-gate, adaptive, comprehend-measure-serialize, trustless]
timestamp: 2026-06-21
edges:
  - {dst: 00-the-primitive, rel: realizes, provenance: asserted}
---

# Layer 2 — the Generative Gate

## The distinction it embodies

Some parts of verification are an **activity** (a fixed procedure — the [harness](11-harness.md)). Other parts must be a **dynamically-defined gate** whose *actions are generated from the content/context*, because the set of things to verify and the right way to verify each cannot be hardcoded without decaying into weak proxies (#503 classes **B** and **D**).

The generative gate is the operation that produces those actions: **`comprehend → measure → serialize`** run in *generate* mode.

## The operation — `comprehend → measure → serialize`

- **comprehend** (semantic, judgment, recorded): read the artifact's actual intent — *"this proposal wires a route / adds a settlement path / changes an invariant."*
- **measure** (structural, deterministic): synthesize the *specific measurements* that would prove it — an executable assertion, a `constraint`+`metric` ([graph-engine D7](../graph-engine/15-constraints-metrics.md)), a symbol-resolution check — **not** "does the file exist."
- **serialize** (freeze): commit those measurements as auditable assertions that then **run fail-closed, deterministically, forever.**

## Why it is trustless (the load-bearing property)

The semantic touch is **bounded to generation** and is **recorded**; the **run is deterministic**. Same trick as the graph-engine's `asserted` edge — *judgment made once, serialized, verified deterministically after.* The gate does not "use AI to check"; it uses comprehension to **author a deterministic check**, freezes it, then the [harness](11-harness.md) replays it. The investigation ledger ([13](13-investigation-ledger.md)) records what was generated and why, so the generation is auditable, not a black box.

## The antidote to #503

#503's gate had a *hardcoded* `grep route_mounted` — a weak proxy that couldn't tell a symbol's *use* from its *name*, and churned rounds. A generative gate *comprehends* "route wiring" → *measures* by symbol resolution → *serializes*. **Hardcoded checks can't adapt to content; generated measurements do.** That is the difference between 7 rounds and one.

## What UACP already provides
- The **measurement primitive**: D7 `metric`/`constraint` = a deterministic measurable check.
- The **generation precedent**: #503's own "propose emits executable assertions" — generalize it to every phase.
- Missing piece (the BUILD, see [20](20-build-improvise-update.md)): *the gate that generates them from comprehension* + binds them to reality.

## The generative moves (content-derived)
`ENUMERATE` (targets from the manifest/content) → `ROUTE` (per target's provenance D17/D23) → `BIND` (resolve to the real artifact/symbol/infra). These feed the fixed harness's `RUN/RECONCILE/LOOP/ESCALATE`.

## To expand
- The assertion model + schema (what a serialized measurement looks like; reuse the graph-engine schema registry).
- The reality binder (how BIND resolves spec→real; ties to artifact_integrity + the code plane / SCIP).
- The synthesis rules per phase (how PROPOSE/PLAN/VERIFY each generate their measurements from content).
