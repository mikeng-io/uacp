## Phase 8: Admission Check Before TRIAGE

Brainstorm is a **registered lifecycle phase**, and the `brainstorm → triage` transition is a real governed boundary. The run was registered at `phase: brainstorm` on entry (Phase 0/Quick-Start step 1), and the scope package is a governed artifact written with `uacp_entity_write`. Before transitioning forward to TRIAGE, validate that the scope package satisfies the codified brainstorm exit invariant.

### Step 8.1: Validate the brainstorm exit invariant via `uacp_heartgate_check`

`core.py` has **no CLI**. Phase-transition validation is performed by calling the `uacp_heartgate_check` TOOL with a transition artifact. Heartgate enforces the codified `brainstorm` phase-exit invariant from `skills/uacp-core/scripts/engines/domain/phase_transitions.py` (`STAGE_PHASE_EXIT_INVARIANTS["brainstorm"]`): the selected scope-package artifact must exist at `brainstorm/*/07-scope-package.yaml` (relative to the `.uacp/` namespace root) with non-empty `title`/`description`/`in_scope`, `declared_side_effects` present, `authority.source` documented, and a valid `routing_advisory`.

Call the tool for the `brainstorm → triage` transition:

```
uacp_heartgate_check(
  from_phase = "brainstorm",
  to_phase   = "triage",
  artifact   = ".uacp/brainstorm/{session_id}/07-scope-package.yaml",
  declared_side_effects = {declared_side_effects},
)
```

Heartgate checks, among the coherence rules:

- `title` and `description` are non-empty
- `in_scope` is non-empty
- `declared_side_effects` is present (may be an empty list)
- `authority.source` is documented
- `routing_advisory` is valid
- the proposed scope does not conflict with any active UACP run in `state/current.yaml`

**Results:**

- **pass** (no blockers) → proceed to Phase 9 and transition forward to TRIAGE.
- **warn** → record warnings; proceed only if the user accepts the recorded risk.
- **block** → return to Phase 5 to refine scope. Do NOT transition to TRIAGE.

Fail-closed: a missing or unreadable scope-package artifact is a blocker, not a warning.

### 8.2 Record the admission result in `manifest.yaml`

```yaml
admission:
  heartgate_status: pass | warn | block
  heartgate_findings: []
  final_decision: proceed_to_triage | stop | refine_scope
```

The scope package itself is a governed lifecycle artifact (written via `uacp_entity_write`) and the run is already state-registered at `phase: brainstorm`. There is no separate "informal, not registered" tier — brainstorm participates in UACP governance like any other phase; the difference is only that it is optional and its sole exit is TRIAGE.
