## Phase 9: Transition Forward to TRIAGE

After the brainstorm exit invariant passes (Phase 8), transition the **already-registered** brainstorm run forward to TRIAGE. The run was registered at `phase: brainstorm` on entry — do NOT `init` a new run here. There is no implicit pre-state to promote; brainstorm is a real registered phase whose sole onward edge in the codified phase graph is `brainstorm → triage`.

### Handoff protocol

Use the governed state-writer to advance the existing run's phase, gated by the same `uacp_heartgate_check` transition validated in Phase 8:

```
# 1. (Phase 8) Validate brainstorm -> triage with the Heartgate tool — must pass.
uacp_heartgate_check(
  from_phase = "brainstorm",
  to_phase   = "triage",
  artifact   = ".uacp/brainstorm/{session_id}/07-scope-package.yaml",
)

# 2. Advance the existing run from brainstorm to triage via the governed
#    state-writer (no new run is created):
uacp_state_write(
  run_id = {existing_run_id},
  phase  = "triage",
  evidence = ".uacp/brainstorm/{session_id}/07-scope-package.yaml",
)
```

### Evidence passed to TRIAGE

- `.uacp/brainstorm/{session_id}/07-scope-package.yaml` — the governed scope-package artifact
- Full session vault `.uacp/brainstorm/{session_id}/` — supporting evidence
- Heartgate findings (if any warnings were accepted)

### TRIAGE's job

TRIAGE decides:

- Does this scope deserve a full UACP lifecycle run?
- What routing depth? (`direct`, `lightweight`, `standard_uacp`, `full_governance`, `block_or_clarify`)
- Is human involvement required?
- Should a local council run before PROPOSE?

Do NOT skip TRIAGE and go directly to PROPOSE. Brainstorm produces a **candidate**; TRIAGE owns the admission decision.

### If the user declines to continue

If the user decides the scope should not advance, stop before the TRIAGE transition. The run remains at `phase: brainstorm` and the vault stays under `.uacp/brainstorm/{session_id}/` as recorded evidence. Closing a brainstorm run that will not advance uses the `aborted`-status path rather than a forward transition.
