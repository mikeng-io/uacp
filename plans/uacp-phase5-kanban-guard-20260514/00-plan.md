# Phase 5 Plan — Kanban Guard

## Objective

Implement a bounded UACP Kanban completion guard: UACP-bound Kanban tasks must not be marked complete unless completion carries mandatory UACP evidence and Guardian metadata.

Kanban remains coordination memory. UACP lifecycle state remains in `state/current.yaml` and per-run artifacts.

## Authority

- Request: Mike, private Telegram, "Let go"
- Run: `uacp-phase5-kanban-guard-20260514-130416`
- Triage: `state/runs/uacp-phase5-kanban-guard-20260514-130416-triage.yaml`
- Proposal: `proposals/uacp-phase5-kanban-guard-20260514.yaml`
- Council synthesis: `verification/uacp-phase5-kanban-guard-proposal-council-synthesis-20260514.yaml`

## Scope

### In scope

1. Inspect current Hermes Kanban completion surfaces.
2. Define canonical UACP completion metadata/evidence schema.
3. Add completion-time enforcement for UACP-bound tasks only.
4. Preserve ordinary non-UACP Kanban completion behavior.
5. Add tests/probes:
   - UACP completion with complete metadata succeeds.
   - UACP completion missing evidence is blocked.
   - UACP completion missing run/phase/authority/policy metadata is blocked.
   - Non-UACP completion remains unchanged.
6. Record verification evidence under `verification/`.

### Out of scope

- Making Kanban the UACP lifecycle state machine.
- Public upstream Hermes push/PR.
- Broad Kanban redesign.
- Disabling Guardian/Heartgate.
- Requiring UACP metadata for non-governed tasks.

## Expected implementation surfaces

Exact file inventory must be confirmed at EXECUTE entry before edits. Candidate surfaces from proposal council:

- `HERMES_ROOT/hermes-agent/hermes_cli/kanban_db.py`
- `HERMES_ROOT/hermes-agent/tools/kanban_tools.py` or equivalent tool wrapper if completion is exposed as a tool
- `HERMES_ROOT/hermes-agent/hermes_cli/kanban.py` if CLI completion needs metadata support
- `HERMES_ROOT/hermes-agent/tests/hermes_cli/test_uacp_kanban_guard.py`
- UACP verification artifacts under `verification/`

## Completion contract draft

For UACP-bound task completion, require a completion metadata payload with:

- `uacp_run_id`
- `uacp_phase`
- `authority_artifact`
- `guardian_policy_version`
- `declared_side_effects`
- `evidence_refs` or equivalent non-empty evidence reference list

The task's stored UACP context must be consistent with the completion payload where both are present. Missing or inconsistent required metadata blocks completion.

## Legacy and compatibility stance

- Non-UACP tasks: unchanged.
- UACP-bound tasks without context: fail closed for governed completion; PLAN/EXECUTE must decide whether to provide an explicit migration/audit path or leave them blocked with clear diagnostics.
- Board-level UACP fallback must not silently surprise ordinary boards; tests must cover the selected behavior.

## Execution topology

- Main session remains orchestrator and verifier.
- Use direct source inspection first because proposal council had mixed file-path reliability.
- Use focused delegate/council only after exact file surfaces are known, if uncertainty remains.
- Do not use Kanban itself for this planning phase; Kanban is the subject under modification.

## Verification

Required before EXECUTE → VERIFY:

1. Syntax/test run for changed Hermes files.
2. Targeted Kanban guard tests pass.
3. Live or near-live negative probe demonstrates UACP-bound completion missing metadata is rejected.
4. Regression proof demonstrates non-UACP completion still succeeds.
5. UACP state/artifact YAML parses.

## Rollback

- Revert local implementation commit if completion behavior regresses.
- If a guard hook/config is introduced, disable the UACP-specific guard rather than affecting global Kanban.
- Preserve UACP artifacts as authority; do not use Kanban task status as rollback source of truth.

## PLAN exit criteria

Before moving to EXECUTE:

- Exact file surfaces are inspected.
- Completion schema is finalized.
- Test list is concrete.
- Plan gate-selection exists.
- Heartgate validates PLAN → EXECUTE transition with warnings carried forward if needed.
