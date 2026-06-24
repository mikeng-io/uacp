---
type: design
title: Coverage Serialization (D43) — make the intent→task coverage graph a real producer output
description: >-
  The structural coverage checks (GP_UNCOVERED_INTENT / GP_ORPHAN_WORK_UNIT) read an
  intent→task graph — keyed scope_items + work_units.derives_from — that NO real producer
  emits today, so _coverage_adopted is always false and the checks silently skip (the #503
  coverage-gap class). This node decides D43: serialize that coverage graph at the PROPOSE/PLAN
  producers, REQUIRED, so the now-wired live-path gates (finalize closure sweep + transition
  plan_exit) actually catch a dropped intent. Detection is built; this is the producer-side
  serialization decision that gives it teeth.
tags: [verification, coverage, d43, serialization, graph-projection, propose, plan, producer-gap]
timestamp: 2026-06-25
edges:
  - {dst: 01-evidence-503, rel: motivated_by, provenance: asserted}
  - {dst: 12-phase-profiles, rel: depends_on, provenance: derived}
---

# Coverage Serialization (D43)

## The gap (grounded, as-built 2026-06-25)

The graph-projection engine already owns the "no dropped intent / no orphan task" guarantee. Its coverage checks read a specific shape:

- a **scope_item** per `proposal.scope.in_scope[]` in the **keyed canonical form** `{id, statement}`;
- a **work_unit** per `plan`/`execution` `work_units[]`, carrying `derives_from: [scope_item_id, …]` — the PROPOSE→PLAN coverage edge.

`_check_uncovered` / `_check_orphan` (`engines/manifest/projection.py`) gate behind `_coverage_adopted(edges)` — true only when ≥1 `derives_from` edge exists — to avoid false-flooding a pre-keys run as all-uncovered.

**The defect: no real producer emits that shape.** The PROPOSE producer emits a `uacp.proposal_package_selection` (universal-core concern blocks + selected modules); the PLAN producer emits a `uacp.scope` artifact (write_paths / blast_radius / rollback) plus a `uacp.plan_package_selection`. **There are no keyed `scope_items` and no `work_units.derives_from` anywhere in the real flow** — only the one GP test hand-crafts them. So `_coverage_adopted` is permanently false and `GP_UNCOVERED_INTENT` / `GP_ORPHAN_WORK_UNIT` **never bind on a real run**. This is exactly the #503 coverage-gap class ([01-evidence-503](01-evidence-503.md)): a check that exists, passes, and proves nothing because its input was never produced.

## Why detection is no longer the blocker

As of 2026-06-25 the two enforcement seams the coverage checks ride are **wired onto the live path** (this is the change that makes D43 worth resolving now):

- **Closure sweep at finalize** — `state_machine.handle_finalize` now runs `Heartgate.validate_closure` → `run_all_engines` (which includes `graph_projection`'s terminal checks: uncovered/orphan/phantom/contradicted), fail-closed.
- **Phase-exit gate at transition** — `state_machine.handle_transition` now forces `validate_graph_invariants('<from_phase>_exit')` (the D35 phase-scoped subset; `plan_exit` carries uncovered/orphan/phantom/obligation-coverage), fail-closed.

Both fire on `GP_UNCOVERED_INTENT` / `GP_ORPHAN_WORK_UNIT` **the moment a `derives_from` edge exists**. So the dropped-intent detector is fully built and live; the only missing piece is the **producer emitting the coverage graph**. D43 is that producer-serialization decision — and nothing else.

## The decision (proposed resolution)

Adopt the keyed coverage graph as a **required** producer output, in the direction the projection already canonicalizes:

1. **PROPOSE emits keyed `scope_items`.** `proposal.scope.in_scope[]` becomes a list of `{id, statement}` (the canonical form), each id stable within the run. This is the substantive half of D43 — today proposal scope is unstructured/markdown; this gives intent a serialized identity.
2. **PLAN emits `work_units[].derives_from`.** Each plan `work_unit` declares the `scope_item` id(s) it serves. This is the coverage edge.
3. **Required, not accepted.** To *close* the fail-open (not merely enable it), the PROPOSE/PLAN schema + authoring contract must REQUIRE the coverage layer. An accept-but-don't-require variant leaves `_coverage_adopted` false whenever an agent omits it — the hole stays open. Requiring it is what makes the gates bite.

### Open facets to settle before building

- **Two "scopes" must be reconciled.** PLAN already emits a `uacp.scope` artifact about *write surfaces* (`write_paths`/`blast_radius`/`rollback`). The coverage `scope_items` are about *intent*. These are different axes; the design must say whether intent scope_items live in the proposal package, the scope artifact, or a new artifact — and how the projection loads them (it reads `proposal.scope.in_scope`, so the proposal is the natural home).
- **Required-field ripple.** Making the coverage layer required ripples every proposal/plan producer + every seeder + the e2e lifecycle fixtures. That cost is the reason this is a deliberate decision, not a drive-by edit.
- **Identity + stability of `scope_item.id`.** Ids must be stable across PROPOSE→PLAN→VERIFY so the edges resolve; decide the id scheme (author-assigned vs derived) and how a legacy bare-string scope degrades (the projection already derives a synthetic id that reads as *uncovered* — a safe pre-keys signal, not a silent pass).
- **Semantic correctness stays a council concern.** The graph proves coverage *topology* only — that *some* work_unit derives from each intent, not that it derives from the *right* one. An invented edge to a real-but-unrelated scope_item passes the structural gate; catching that is the PROPOSE→PLAN council gate ([14-council-method](14-council-method.md)), not this engine.

## To build (next session)

- Resolve D43 in the decision-log (the keyed-scope-items + derives_from direction, REQUIRED), with the two-scopes reconciliation recorded.
- Extend the proposal/plan schema (the producer/validator authority) to require keyed `scope_items` (PROPOSE) + `work_units.derives_from` (PLAN); update the authoring contract.
- Update the lifecycle seeders/fixtures to emit the coverage layer.
- TDD the closing proof: a real run that DROPS an intent (a `scope_item` no `work_unit` derives from) is now BLOCKED — at `plan_exit` (transition gate) and at closure (finalize gate) — where today it silently passes. Non-vacuity: the same run with the intent covered advances and finalizes.

---

This node depends on [12-phase-profiles](12-phase-profiles.md) (the `plan_exit` profile is where coverage binds) and is motivated by the coverage-gap class in [01-evidence-503](01-evidence-503.md). It is the producer half of a guarantee whose detector ([10-generative-gate](10-generative-gate.md) / the harness) is already built and live.
