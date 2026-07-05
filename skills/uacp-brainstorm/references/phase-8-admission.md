## Phase 8: The Brainstorm Admission Contract

Brainstorm is a **registered lifecycle phase**, and `brainstorm → triage` is a real governed boundary. The run was registered at `phase: brainstorm` on entry (Phase 0/Quick-Start step 1), and the scope package is a governed artifact written with `uacp_entity_write`. The crossing's exit contract — the **brainstorm admission contract** — is enforced **by code, inside the transition** (Phase 9), not by an agent-invoked check here.

### What the gate measures

The codified `brainstorm` phase-exit contract (`skills/uacp-core/scripts/engines/domain/phase_transitions.py` `STAGE_PHASE_EXIT_INVARIANTS["brainstorm"]`, measured by `Heartgate.forced_brainstorm_exit_blockers`) requires a selected scope-package artifact at `brainstorm/*/07-scope-package.yaml` (relative to the `.uacp/` namespace root) that satisfies, as real fields (not mere file-existence):

- `title` — non-empty
- `description` — non-empty
- `in_scope` — non-empty list
- `declared_side_effects` — present (may be an empty list)
- `authority.source` — documented (non-empty)
- `routing_advisory` — one of `direct` | `lightweight` | `standard` | `full_governance`

This is the same shape Phase 7 produces and the entity-writer schema validates at write time; the transition gate re-measures it at the membrane, independent of the writer, and is **fail-closed** (a missing, unparseable, or field-incomplete scope package blocks the crossing).

### How to apply it

You do **not** call a separate validation tool in this phase. The admission contract is enforced where the boundary is — inside `uacp_run_transition` (Phase 9). Phase 8 is your own **pre-flight self-check**: confirm your selected scope package fills the shape above so the Phase 9 crossing passes on the first try. If it does not yet, return to Phase 5 (trim) / Phase 7 (scope package) and fix it before requesting the transition.

> Why no `uacp_heartgate_check` here: that tool validates a transition *artifact* under a managed artifact/state root — the brainstorm scope package is not transition-artifact-shaped, and earlier guidance to hand-assemble an artifact and call it with `from_phase`/`to_phase`/`artifact` passed parameters the handler never read. The fix is structural: the agent **requests** the crossing (Phase 9) and **code measures + effects** it. The agent is barred from stamping its own phase — that is the governance contract, not a tooling detail.

### 8.1 Record the admission intent in `manifest.yaml`

```yaml
admission:
  self_check: pass | needs_refinement   # your Phase-8 pre-flight assessment
  final_decision: proceed_to_triage | refine_scope | stop
```

The authoritative admission result is the outcome of the Phase 9 `uacp_run_transition` call (its `ok` / `blockers`), recorded by the governed transition itself. The scope package remains a governed lifecycle artifact (written via `uacp_entity_write`) and the run is already state-registered at `phase: brainstorm`; brainstorm participates in UACP governance like any other phase — the only difference is that it is optional and its sole exit is TRIAGE.
