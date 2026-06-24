---
type: design
title: Coverage Serialization (D43) — as-built + the package-selection residual
description: >-
  D43 (keyed scope_items at PROPOSE + work_units.derives_from at PLAN) is ALREADY BUILT and
  enforced — schema.validate at write time, the offline PIV/proposal validators, the entity-writer,
  the SKILL contracts, and a passing graph-gate activation e2e. The real remaining gap is narrower:
  the kernel's gate-REQUIRED PROPOSE artifact is uacp.proposal_package_selection (scope in markdown),
  NOT the keyed uacp.proposal — so coverage does not bind for the package-selection representation,
  which is the path the lifecycle fixture exercises. This node records that as-built reality and the
  open decision (close the package-selection residual), plus three review-surfaced blind spots
  (inherited_artifacts invisible to projection; no transition-time referential check on derives_from;
  topology-only gate is gameable). CORRECTED 2026-06-25 after an independent cross-provider review
  (kimi + Claude subagent) caught the original "no producer emits it" framing as false.
tags: [verification, coverage, d43, serialization, graph-projection, propose, plan, package-selection, as-built]
timestamp: 2026-06-25
edges:
  - {dst: 01-evidence-503, rel: motivated_by, provenance: asserted}
  - {dst: 12-phase-profiles, rel: depends_on, provenance: derived}
---

# Coverage Serialization (D43)

> **Correction note (2026-06-25).** The first draft of this node claimed "no real producer emits
> keyed `scope_items` + `work_units.derives_from`, so the coverage checks silently skip" and framed
> D43 as an unbuilt decision. An independent review (cross-provider **kimi** + a **Claude subagent**),
> grounded in the code, found that **false** — D43's producer-serialization is already built and
> enforced. This node is the corrected record. Verifying reviewer claims against the code is the
> discipline that caught it; the original framing was grounded only on the package-selection test
> seeders and `projection.py`, and missed the schema/validator/entity-writer enforcement.

## D43 is built (the keyed coverage graph is REQUIRED, not aspirational)

The intent→task coverage graph the GP engine reads — keyed `scope_items {id, statement}` +
`work_units[].derives_from` — is emitted and enforced today:

- **Keyed `scope_items`, write-time.** `engines/domain/schema.py` types `uacp.proposal.scope.in_scope`
  as keyed `{id, statement}` items (`required: [id, statement]`, `minItems: 1`) — its own comment calls
  this "the LOAD-BEARING enforcement of the keyed shape," run at write time via
  `entity_writer.create_entity` → `schema.validate`.
- **`derives_from`, two ends.** `engines/domain/schema.py` requires `derives_from` (`minItems: 1`) on
  every PIV `work_unit` at write time; `scripts/validate_uacp_artifacts.py::validate_piv_contract`
  BLOCKs a `work_unit` missing it at the Heartgate transition (the intentional shape-vs-referential
  asymmetry: proposal scope is self-contained so it is shape-checked; `derives_from` is a cross-artifact
  reference so it is contract-checked at the transition). `validate_proposal` likewise blocks bare-string
  `in_scope`.
- **Authoring contracts + proof.** `skills/uacp-propose/SKILL.md` and `skills/uacp-plan/SKILL.md`
  instruct producers to emit both; `tests/integration/test_graph_gate_activation_e2e.py` proves
  `GP_UNCOVERED_INTENT` binds end-to-end on an entity-written run (and clears when covered).

So the coverage checks are **not** permanently skipped: for a run authored via the keyed
`uacp.proposal` + PIV path, `_coverage_adopted` is true and the (now live-wired) gates enforce it.

## The real residual: package-selection mode carries scope in markdown

The kernel's PROPOSE/PLAN **gates require the `*_package_selection` envelope**, never a bare
`uacp.proposal`/`uacp.plan` (`adaptive_proposal_package_gate`; `config/phase-transitions.yaml` requires
`proposals/{run_id}-package-selection.yaml`; `design/graph-engine/24-asbuilt-manifest-taxonomy.md`).
In **package-selection mode** the scope concern is a **markdown module**, not a keyed
`uacp.proposal.scope.in_scope` — so there are no `scope_item` nodes to project and coverage does not
bind. `engines/domain/schema.py` documents this exactly: *"package-selection-mode runs carry scope in
markdown … so the two coverage checks do not bind for that representation — a documented residual."*
The lifecycle fixture (`tests/e2e/test_full_lifecycle.py::_seed_proposal_package` / `_seed_plan_package`)
is precisely this path: it emits `uacp.proposal_package_selection` + a write-paths `uacp.scope`, with no
keyed scope and no `work_units` — so a dropped intent on that path is **not** caught today.

That — not "D43 is unbuilt" — is the open problem.

## DECISION + as-built update (2026-06-25, session 2)

**Decided (mike): Option C — keyed scope MODULE + register PIV.** Grounded follow-up changed the
picture: the governed entity-writer `engines/manifest/entity_writer.py::create_entity` **auto-registers**
every entity it writes into `manifest.artifacts` (`artifact_type = kind.removeprefix("uacp.")`). So a run
authored the governed way — `uacp_entity_write` of a keyed `uacp.proposal` (the substantive scope module)
+ the PIV — already registers both, projection loads them, and **coverage is enforced on the LIVE path**:
`tests/e2e/test_transition_coverage_enforced.py` proves a dropped intent (keyed proposal declares si-1+si-2,
PIV covers only si-1) is BLOCKED by `state_machine.handle_transition(plan→execute)` with `GP_UNCOVERED_INTENT`,
and a fully-covered run advances. So Option C's mechanism (keyed `uacp.proposal` as the scope module + the
auto-registered PIV) is **already wired and now regression-tested end-to-end** for governed runs.

**Enforcement increment LANDED (2026-06-25, session 2b).** `validate_adaptive_proposal_package_gate` now
REQUIRES the `scope` universal-core concern be `covered` by a keyed scope module
(`scope.in_scope:[{id,statement}]`, ≥1) — `not_applicable` / unstructured-markdown scope is now a blocker
(`_scope_concern_is_keyed`). So structured intent scope is **mandatory** for the package-selection
PROPOSE→PLAN. TDD: `tests/e2e/test_proposal_scope_gate.py` (na + bare-string scope blocked; keyed passes;
non-vacuity proven). The shared `_seed_proposal_package` now emits a keyed scope module (one fix
cascade-cleared the 49 fixtures that drive this gate). Suite 1881 green.

**Honest residual (two precise gaps that remain, smaller and separable):**
1. **The gate is in `validate_transition` (agent-invoked), not the forced `handle_transition` path** — like
   *all* the adaptive package gates. A non-compliant agent that never calls `uacp_heartgate_check` bypasses
   it. Closing that is the broader "force `validate_transition`" concern (the package gates aren't forced),
   an initiative-level item, not specific to coverage. The forced structural coverage (my `plan_exit`
   `GP_UNCOVERED`) still fires for governed entity-write runs (keyed proposal + PIV auto-register).
2. **The required scope module is referenced, not registered.** In package-selection mode the seeder writes
   the scope module + points the scope concern at it, but does not `register_artifact` it — so
   `projection._load_and_project` (reads `manifest.artifacts`) does not project its scope_items, and the
   coverage *check* (GP_UNCOVERED) does not BIND for package-selection runs (only the gate *requirement* is
   enforced). Full binding on the package-selection path additionally needs: register the scope module +
   register the PIV + fire `_check_uncovered` on scope-presence (drop the `_coverage_adopted` skip when
   scope_items exist). For **governed entity-write runs this already fully binds + is enforced** (auto-register
   + the forced plan_exit gate — proven by `test_transition_coverage_enforced.py`).

## The open decision (what to actually settle) — RESOLVED to Option C above; kept for context

Close the package-selection coverage residual. Two options (reviewers favored the first as less
disruptive):

1. **Carry the coverage graph in the gate-required artifact.** Add a machine-readable `scope_items`
   block to `uacp.proposal_package_selection` (and require `derives_from` coverage in the plan
   package), enforced by `validate_proposal_package_selection`. Because that envelope is what every
   real run already produces, coverage then binds on the live path with no new required artifact.
2. **Make the kernel require the keyed `uacp.proposal`/PIV** (today only the SKILLs require them; the
   *kernel gate* requires only the package_selection). More disruptive; introduces a second required
   PROPOSE artifact.

Either way: update `_seed_proposal_package`/`_seed_plan_package` to exercise the coverage layer and add
a negative test — a lifecycle run that **drops an intent** must block at `plan_exit` (transition gate)
and at closure (finalize gate). Today it silently passes; that test is the real non-vacuity proof.

## Review-surfaced blind spots (verified against the code)

- **`inherited_artifacts` are invisible to projection.** `RunManifest.inherited_artifacts` (goal-driven
  runs copy reused parent proposal/plan refs here) is **not** in `projection._load_and_project`'s load
  set (it iterates only `manifest["artifacts"]`). A child run reusing a parent proposal/plan projects
  no scope_items/work_units → coverage silently passes. Decide: project `inherited_artifacts` too, or
  fail closed when coverage inputs are inherited but unprojected.
- **No transition-time referential check on `derives_from`.** `validate_piv_contract` checks that
  `derives_from` is a non-empty list, not that each id resolves to a declared `scope_item`. Only
  `graph_projection`'s `GP_PHANTOM_EDGE` catches a dangling id, and only if a keyed proposal is
  registered + loaded. A referential check at the transition would catch forged ids earlier with a
  clearer blocker.
- **Topology-only ⇒ gameable.** The structural gate proves coverage *topology*, not that an edge points
  at the *right* intent: pointing every `work_unit` at one throwaway `scope_item` passes. The council
  PROPOSE→PLAN gate ([14-council-method](14-council-method.md)) is the only semantic backstop, and it is
  author-triggered. Document this as the known limit of the as-built gate (already disclaimed in
  `projection.py`'s engine docstring).

## To build (next session)

- Decision-log entry recording: D43 producer-serialization is built; the open decision is closing the
  package-selection residual (option 1 vs 2 above).
- Implement the chosen option; update `_seed_proposal_package`/`_seed_plan_package`; add the
  drop-an-intent negative test on the lifecycle path (blocks at `plan_exit` + closure).
- (Optional hardening, separable) the transition-time `derives_from` referential check; the
  `inherited_artifacts` projection fix.

---

This node depends on [12-phase-profiles](12-phase-profiles.md) (the `plan_exit` profile is where
coverage binds) and is motivated by the coverage-gap class in [01-evidence-503](01-evidence-503.md).
The detector and its live-path wiring are built; the residual is making the kernel-required
package-selection artifacts carry and enforce the coverage graph.
