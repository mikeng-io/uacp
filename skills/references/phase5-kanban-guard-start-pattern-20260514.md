# Phase 5 Kanban Guard Start Pattern — 2026-05-14

Use this when starting or planning UACP work that changes Hermes Kanban completion semantics or UACP-bound task evidence requirements.

## Context

Phase 5 began after Phase 4B resolved and pushed cleanly. The objective was a Kanban guard: UACP-bound Kanban task completion must carry mandatory UACP evidence and Guardian metadata. Kanban remains coordination memory, not UACP lifecycle state.

## Proven sequence

1. Ground truth current UACP state before starting:
   - `state/current.yaml`
   - `outputs/uacp-current-status.yaml`
   - `git status`, HEAD, and ahead/behind against private remote.
2. TRIAGE as standard UACP when completion/evidence semantics are affected.
3. PROPOSE with explicit non-goals:
   - do not make Kanban the UACP phase state machine;
   - do not alter ordinary non-UACP completion behavior;
   - do not weaken Guardian/Heartgate;
   - do not push public upstream without explicit approval.
4. Run a focused proposal council, but weight outputs by file/path validity. If a council role reports missing artifacts that the main session has verified, record it as low-confidence rather than as a true blocker.
5. Encode accepted council concerns as `warnings` and `deferred_items` in transition artifacts. Keep strict Heartgate cluster/invariant states within accepted vocabulary (`pass`/`block` or supported values); do not use ad hoc values like `pass_with_concerns` in strict fields.
6. PLAN must identify exact implementation surfaces before EXECUTE. For Kanban completion work, candidate surfaces were:
   - `HERMES_ROOT/hermes-agent/hermes_cli/kanban_db.py`
   - `HERMES_ROOT/hermes-agent/tools/kanban_tools.py`
   - `HERMES_ROOT/hermes-agent/hermes_cli/kanban.py`
   - `HERMES_ROOT/hermes-agent/tests/hermes_cli/test_uacp_kanban_guard.py`
7. PLAN -> EXECUTE is acceptable only after Heartgate passes with accepted warnings and the plan names concrete tests/probes.

## Core implementation lesson

Creation-time and dispatch-time UACP checks are not enough. The guarded boundary is the completion edge: before a UACP-bound task transitions to `done`, completion must validate a canonical metadata/evidence payload.

Required semantic fields for UACP-bound completion:

- `uacp_run_id`
- `uacp_phase`
- `authority_artifact`
- `guardian_policy_version`
- `declared_side_effects`
- non-empty evidence references (`evidence_refs` or equivalent)

Missing or inconsistent required metadata should fail closed for UACP-bound tasks only. Non-UACP task completion must remain unchanged.

## Required verification shape

- Positive: UACP-bound completion with complete metadata succeeds.
- Negative: UACP-bound completion missing evidence is blocked.
- Negative: UACP-bound completion missing run/phase/authority/policy metadata is blocked.
- Regression: non-UACP completion still succeeds.
- Traceability: completed UACP-bound task links to active run and evidence artifact.

## Pitfalls

- Do not trust council self-reports blindly. Verify whether the delegate actually read the requested files before treating findings as blockers.
- Do not let Kanban task status become UACP lifecycle state. UACP state remains in `state/current.yaml` and run artifacts.
- Do not globally require UACP completion metadata; scope enforcement to UACP-bound tasks.
- Do not treat low-confidence delegate path confusion as an environment rule or permanent tool limitation. Record the validity weighting and continue with main-session ground truthing.
