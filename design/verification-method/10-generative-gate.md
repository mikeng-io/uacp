---
type: design
title: Layer 2 — the Generative Gate (comprehend → measure → serialize)
description: The dynamic gate whose verification ACTIONS are generated from the artifact's content/context, not hardcoded. The comprehend→measure→serialize operation; its re-derivable property (semantic generates, deterministic runs, generation recorded); the antidote to #503's weak-proxy + coverage-gap classes. Grounded in the as-built schema registry + projection enumerator.
tags: [verification, generative-gate, adaptive, comprehend-measure-serialize, re-derivable]
timestamp: 2026-06-24
edges:
  - {dst: 00-the-primitive, rel: realizes, provenance: asserted}
---

# Layer 2 — the Generative Gate

## What this does, and why it matters (plain language — read this first)

**The problem.** When an AI agent says *"I verified this — it's done,"* you usually can't tell
whether it ran a real check, a fake one, or just asserted "looks good." A real verification feature
(Trustless #503, used here as evidence only — [01](01-evidence-503.md)) went through **7 rounds of
automated review and still shipped live bugs**, because its checks were rubber stamps: a
`grep "route_mounted"` "passed" but only proved the *string* existed, not that the route worked.

**What the generative gate does.** It forces the agent to write a **specific, runnable check for
each thing it claimed to do** — derived from what it actually built — freezes those checks, and the
kernel **re-runs them automatically and blocks "done" if any are missing, fake, or failing.**

> Example. A plan task says *"wire up the /settle payment route."* Today the agent marks it done,
> maybe greps a string, and a broken route ships. With this gate the agent must emit a check derived
> from that task — `symbol_resolves(settle_route) == true` — frozen as a record. The kernel then
> (1) refuses to close unless **every** claimed target carries a check (no silent gaps),
> (2) requires the **right kind** of check (a "wires up X" claim needs a *resolution* check, not
> "a file exists"), (3) **re-runs the check** deterministically and blocks on FAIL/ERROR (an error is
> never a pass), and (4) lets a reviewer panel refute checks that are present-but-weak. The agent
> cannot skip a target, rubber-stamp it, or let the criteria drift from what is actually run.

**How it differs from CI.** CI runs *fixed* tests a human wrote in advance. This makes the **agent
generate the right checks from what it actually did** (coverage adapts to the work, not a stale test
file), freezes them so they cannot drift, and makes passing them a **hard gate on declaring work done.**

**Where it sits.** The coverage work already shipped ([15](15-coverage-serialization.md)) answers
*"did the agent cover every declared intent with a task?"* This gate goes one level deeper:
*"and is each task actually proven to work — by a real check, not a rubber stamp?"* Together: nothing
is dropped, and nothing is falsely claimed verified.

> **What ships when (council honesty — the route example is later).** The `symbol_resolves(settle_route)`
> example above is a **code-plane** check, which lands in **Slice 3** (it depends on the Codeflair SCIP
> index — [32](32-reality-binder.md)). **Slice 0** (RELATION graph + artifact-content, buildable now)
> closes #503 classes **A** (ERROR≠PASS), **D** (every target has a check — partial: keyed/graph targets),
> and **F** (frozen checks replayed verbatim, no spec↔runner drift); it does **not** yet close **B**
> (weak-proxy) for *code* claims — those `wires_symbol` checks correctly **block** (fail-closed) until the
> code plane is wired, rather than passing on a textual shadow. So Slice 0 makes "done" *fail-closed and
> drift-proof for what it can prove now*, and *refuses to close on a weak proxy for what it can't yet* —
> the headline `grep route_mounted` killer (class B) arrives with the code plane, not at Slice 0.

The rest of this node is the mechanism behind that guarantee.

## The distinction it embodies

Some parts of verification are an **activity** (a fixed procedure — the [harness](11-harness.md)). Other parts must be a **dynamically-defined gate** whose *actions are generated from the content/context*, because the set of things to verify and the right way to verify each cannot be hardcoded without decaying into weak proxies (#503 classes **B** and **D**).

The generative gate is the operation that produces those actions: **`comprehend → measure → serialize`** run in *generate* mode. This is the verification instantiation of CMS — the canonical principle lives in [`design/comprehend-measure-serialize/`](../comprehend-measure-serialize/00-the-axiom.md); this node does not re-derive it.

## The operation — `comprehend → measure → serialize`

- **comprehend** (semantic, judgment, recorded): read the artifact's actual intent — *"this proposal wires a route / adds a settlement path / changes an invariant."*
- **measure** (the agent's **grounded judgment** of *which specific check would prove it* — author an executable assertion, **not** "does the file exist"). This is a *semantic* act, **not** deterministic — determinism is relocated to where the authored check is replayed (the CMS thesis: [11-measure](../comprehend-measure-serialize/11-measure.md), [25-enforcement-surfaces](../comprehend-measure-serialize/25-enforcement-surfaces.md)).
- **serialize** (freeze): canonicalize those measurements as auditable assertions that then **run fail-closed, deterministically, forever.**

## Why it is re-derivable (the load-bearing property)

The semantic touch is **bounded to generation** and is **recorded**; the **run is deterministic** — *semantic generates, deterministic runs*. Same move as the graph-engine's `asserted` edge — *judgment made once, serialized, replayed deterministically after.* The gate does not "use AI to check"; it uses comprehension to **author a deterministic check**, freezes it, then the [harness](11-harness.md) replays it. The investigation ledger ([13](13-investigation-ledger.md)) records what was generated and why, so the generation is auditable, not a black box. This *is* the CMS determinism-relocation framing ([25-enforcement-surfaces](../comprehend-measure-serialize/25-enforcement-surfaces.md)): the agent's `measure` is grounded, not deterministic; determinism belongs to the replaying gate.

## The antidote to #503

#503's gate had a *hardcoded* `grep route_mounted` — a weak proxy that couldn't tell a symbol's *use* from its *name*, and churned rounds. A generative gate *comprehends* "route wiring" → *measures* by symbol resolution → *serializes*. **Hardcoded checks can't adapt to content; generated measurements do.** That is the difference between 7 rounds and one.

## What is already built vs. what is genuinely new

The substrate exists — be honest about which is which:

- **The serialization sink (BUILT).** The per-kind schema registry — `engines/domain/schema.py`: a `kind → JSON-Schema` map + `validate(kind, doc)` that never raises (malformed input returns error strings). This is the real **IMPROVISE** target: a new generated assertion / check is a new `kind` added here, validated at write time via the entity-writer's `has_schema`-gated path. The `Engine`/`Violation` model (`engines/base.py`) is the matching run-side contract — a generated check is an engine returning `Violation`s.
- **The ENUMERATE substrate (BUILT).** `engines/manifest/projection.py:_load_and_project` already loads a run's manifest and projects **every** artifact into `(nodes, edges)`; the `artifact_integrity` engine is the reality-binder precedent (a deterministic check bound to on-disk reality). `graph_projection.py` is now a re-export shim → `engines.manifest.projection`.
- **The designed measurement primitive (NOT built).** D7's `metric` / `prohibition` / `method_constraint` nodes + `constrains` / `measured_by` / `violated` edges ([graph-engine D7](../graph-engine/15-constraints-metrics.md)) are **graph-engine Slice 3, design-only** — the projection emits no such kinds and the schema registry has none. This is the *designed* deterministic-measurable-check primitive, to be built; do **not** present it as something UACP already provides.
- **The generation precedent (BUILT, narrow).** #503's own "propose emits executable assertions" — generalize it to every phase.
- **The BUILD (genuinely new).** The **generator** itself (comprehend content → author a check) is new. **ROUTE-by-provenance** and **symbol-resolution BIND** are also new: the projection types edges only by `rel` (no provenance routing), and symbol BIND needs the not-yet-built code / SCIP plane. See [20](20-build-improvise-update.md).

## The generative moves (content-derived)
`ENUMERATE` (targets from the manifest/content — the projection enumerator is the substrate) → `ROUTE` (per target's provenance D17/D23 — new) → `BIND` (resolve to the real artifact/symbol/infra — `artifact_integrity` is the precedent; symbol BIND awaits the code plane). These feed the fixed harness's `RUN/RECONCILE/LOOP/ESCALATE`.

## To expand
- The assertion model + schema (what a serialized measurement looks like as a `kind` in the registry — extends `engines/domain/schema.py`; D7 supplies the *designed* `metric`/`constraint` shapes once Slice 3 lands).
- The reality binder (how BIND resolves spec→real; ties to `artifact_integrity` + the code plane / SCIP).
- The synthesis rules per phase (how PROPOSE/PLAN/VERIFY each generate their measurements from content).
