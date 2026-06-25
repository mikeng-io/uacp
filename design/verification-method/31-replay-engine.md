---
type: design
title: The Replay Engine — deterministic re-execution of frozen checks
description: >-
  The deterministic consumer of the typed check catalog: it loads every registered uacp.check.* node,
  dispatches each to its kind's predicate evaluator, binds it to reality (node 32), and emits a
  Violation on FAIL or ERROR — fail-closed, ERROR never PASS (closes #503 class A). It is one more
  Engine in the shared run_all_engines sweep, so it inherits the crash-guard, the phase-keyed wiring
  (validate_graph_invariants), and the closure sweep already built. No agent code runs at replay; the
  semantic act happened once, at authoring time.
tags: [verification, generative-gate, replay, engine, fail-closed, run-all-engines]
timestamp: 2026-06-25
edges:
  - {dst: 30-assertion-model, rel: consumes, provenance: derived}
  - {dst: 11-harness, rel: realizes, provenance: asserted}
---

# The Replay Engine

The replay engine is the **deterministic pole** of the gate: the generative step
([10](10-generative-gate.md)) comprehended-and-froze a check *once*; this engine *replays* it, forever,
the same way every time. **No agent / LLM code runs here** — the engine only evaluates a kind's fixed
predicate against the bound reality. That relocation (judgment at authoring, determinism at replay) is
the whole "re-derivable, not a black box" property.

## What it is, in as-built terms

It is **one more `Engine`** in the shared protocol (`engines/base.py` — `Engine`/`Violation`,
block/warn severity). So it does not invent any new run machinery:

- it registers into `ENGINES`, so **`run_all_engines`** sweeps it (each engine wrapped so an unexpected
  raise becomes an `ENGINE_CRASHED` **block**, never a silent pass);
- it therefore runs everywhere the sweep already runs: the **closure** gate
  (`validate_closure` → `run_all_engines`) and the **phase-keyed** transition gate
  (`validate_graph_invariants(..., "<from_phase>_exit")`) — both forced onto the live path this session;
- its findings reconcile with the existing structural checks (`GP_*`, `evidence_completeness`,
  coherence) in the same RUN/RECONCILE pass ([11](11-harness.md)).

## The algorithm (per run)

```
load (nodes, edges) via projection._load_and_project        # NB: requires the new _project arm (below)
for each node n where n.kind startswith "uacp.check.":
    evaluator = CATALOG[n.kind].evaluator                   # closed dispatch; unknown kind -> ERROR (block)
    try:
        reality = bind(n.bind, nodes, edges, workspace)     # node 32 — routed by plane
        verdict = evaluator(n.expect, reality)              # pure: data vs data
    except Exception as exc:
        verdict = ERROR(exc)                                # class A: ERROR is a BLOCK, never PASS
    if verdict in (FAIL, ERROR):
        emit Violation(code=f"CHK_{kind}", severity=n.severity-or-ERROR-block, detail=...)
```

Three fail-closed rules (each closes a #503 class):

- **ERROR ≠ PASS (class A).** A bind failure, an unrunnable predicate, or an unknown kind is a BLOCK,
  not a skip. The default severity of an ERROR is `block` even for a `warn` check.
- **Unverified target is uncovered (class D).** A target with no `measured_by` check is the coverage
  gate's concern ([34](34-adequacy-and-coverage.md)), not silently passed here — this engine proves the
  checks that exist; coverage proves checks exist at all. The two compose; neither alone is enough.
- **Replay reads the frozen check verbatim (class F).** The engine never re-derives criteria; it runs
  exactly what was serialized, under the check's recorded `catalog_version`. The runner cannot drift
  from the declared criteria because it *is* the declared criteria.

## What is built vs new

- **Built / IMPROVISE:** the `Engine`/`Violation` contract, `run_all_engines` + its crash-guard, the
  closure + phase-exit wiring, the `_load_and_project` *manifest-loading* loop (it iterates every
  registered artifact), `artifact_integrity` (the precedent reality-bound engine).
- **New (BUILD, slice 0):** the `uacp.check.*` arm in `_project` that turns a check doc into a `check`
  node + `measured_by` edge (the manifest is loaded for free; the **check nodes are not** — `_project` is
  a hardcoded extractor today, council finding, [30](30-assertion-model.md)); the dispatch table (kind →
  evaluator); the per-kind evaluators for the graph + artifact-content catalog; registering the engine
  into `ENGINES`.
- **New (later):** evaluators for the code/SCIP + behavioral kinds (need the binder's code plane —
  [32](32-reality-binder.md)).

## To build (slice 0)

- `engines/verification/replay.py` (or `engines/manifest/`): the dispatch + the graph/artifact-content
  evaluators, registered into `ENGINES`; reuse `projection._load_and_project` for the graph.
- A keystone test: a run with a registered `field_equals` / `obligation_satisfied` check whose target
  reality FAILS is blocked at the phase gate AND at closure; a satisfied check passes; a check that
  ERRORs (dangling bind) is a BLOCK, not a pass (non-vacuity = each fails for the right reason).
