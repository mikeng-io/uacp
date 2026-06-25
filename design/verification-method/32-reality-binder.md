---
type: design
title: The Reality Binder — resolving a frozen check to the real thing (by plane)
description: >-
  BIND is the gate's reality step (the #503 class-C fix): it resolves a check's `bind` reference to the
  ACTUAL artifact / symbol / behavior it must prove, routed by PLANE. RELATION-graph and artifact-content
  binds are buildable now (projection nodes + artifact_integrity / on-disk reads under engines.io); code/SCIP
  symbol binds and behavioral/runner binds are designed here but gated on the code plane (Codeflair). A bind
  that cannot resolve is an ERROR (block), never a silent pass.
tags: [verification, generative-gate, reality-binder, bind, planes, scip, class-c]
timestamp: 2026-06-25
edges:
  - {dst: 30-assertion-model, rel: depends_on, provenance: derived}
  - {dst: 31-replay-engine, rel: realizes, provenance: asserted}
---

# The Reality Binder

A check that runs against a mock, a spec, or a string — never the real artifact — is the #503
**class-C** failure (and class B, the weak proxy). BIND is the step that prevents it: it resolves a
check's `bind: {plane, ref}` to the **actual thing under test** before the predicate runs. If it cannot
resolve, the replay engine ([31](31-replay-engine.md)) records an ERROR (a block), never a pass.

## Routed by plane

`bind` is a small router. Each plane is a resolver from a `ref` to a piece of reality the evaluator can
compare against. This keeps the catalog ([30](30-assertion-model.md)) plane-agnostic and lets planes
land incrementally.

| plane | `ref` resolves to | resolver | status |
|---|---|---|---|
| `graph` | a node/edge in the run's projected manifest graph | `projection._load_and_project` (already loaded) | **now** |
| `artifact` | a field/section of a registered on-disk artifact | `engines.io` loaders + `artifact_integrity` (watermark) | **now** |
| `code` | a symbol / call-site in the codebase | the code plane (SCIP index — Codeflair) | **later** |
| `behavior` | the observed result of exercising the work | a sandboxed runner | **later** (heaviest) |

The first two planes need **no new substrate** — they bind to data the kernel already has (the manifest
graph + governed artifacts). That is why slice 0 is real without Codeflair: it closes class C *for the
RELATION + artifact-content planes* immediately, and the *same envelope* extends to `code` / `behavior`
when those planes exist.

## The code plane (designed, gated on Codeflair)

`symbol_resolves` / `symbol_referenced_by` are the checks that finally kill the #503 weak proxy
(`grep route_mounted`): instead of a textual shadow, they bind to a **SCIP symbol index** and ask
"does `settle_route` resolve?" / "is it referenced by ≥1 caller?". This is the bridge to the Codeflair
code plane (the deterministic SCIP/tree-sitter substrate already built on `main`): the binder's `code`
resolver is a thin adapter over a per-commit symbol index. UACP does not own that index — it *consumes*
it. Until that adapter exists, `code`-plane checks are authored but their bind ERRORs (block) — so a run
that *requires* a code check (per the required-kinds floor, [34](34-adequacy-and-coverage.md)) cannot
falsely pass; it is correctly blocked until the plane is wired. (This is fail-closed-by-construction, not
a gap.)

## The behavioral plane (designed, deferred)

`uacp.check.behavioral` is the reality-binding endgame: exercise the work and bind to the *result*, not
the artifact. It needs an isolated runner (class E — env-fragility — lives here: the run must be
isolated from incidental state). Deliberately last; the graph/artifact/code planes cover the dominant
#503 classes first.

## What is built vs new

- **Built / IMPROVISE:** `projection._load_and_project` (graph resolver), `engines.io` + watermark /
  `artifact_integrity` (artifact resolver).
- **New (BUILD, slice 0):** the plane router + the `graph` and `artifact` resolvers as a small,
  reviewed module the replay engine calls.
- **New (later):** the `code` resolver (SCIP adapter over Codeflair); the `behavior` resolver (runner).

## To build (slice 0)

- `bind(ref, nodes, edges, workspace) -> reality | ERROR` with the `graph` + `artifact` planes only;
  unknown/unresolvable plane → ERROR. A dangling `code`/`behavior` ref ERRORs cleanly (block), proving
  the fail-closed-until-wired property with a test.
