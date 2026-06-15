## Phase 9: Hand Off to TRIAGE

After Guardian admission (and optional Heartgate coherence), the brainstorm is complete. The selected scope package becomes input to TRIAGE.

### Handoff protocol

```bash
# 1. Initialize a new UACP run if one does not exist
python3 skills/uacp-state/scripts/state_machine.py init \
  --run-id {new_run_id} \
  --phase triage \
  --authority user

# 2. Transition from implicit pre-state into formal TRIAGE
python3 skills/uacp-state/scripts/state_machine.py transition \
  --run-id {new_run_id} \
  --to-phase triage \
  --evidence .uacp/brainstorm/{session_id}/07-scope-package.yaml
```

### Evidence passed to TRIAGE

- `.uacp/brainstorm/{session_id}/07-scope-package.yaml`
- Full vault path `.uacp/brainstorm/{session_id}/` (for reference, not as state)
- Guardian warnings (if any)
- Heartgate findings (if any)

### TRIAGE's job

TRIAGE decides:
- Does this scope deserve a full UACP lifecycle run?
- What routing depth? (`direct`, `lightweight`, `standard_uacp`, `full_governance`)
- Is human involvement required?
- Should a local council run before PROPOSE?

Do NOT skip TRIAGE and go directly to PROPOSE. Brainstorm produces a **candidate**; TRIAGE owns the admission decision.

### If the user declines UACP

If at any point the user decides the scope does not need UACP governance, stop. The vault remains in `.uacp/brainstorm/` as reference material. No state is mutated.
