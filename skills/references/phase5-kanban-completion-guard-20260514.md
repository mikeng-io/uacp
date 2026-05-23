# Phase 5 Kanban Completion Guard Lessons — 2026-05-14

Use this reference when UACP work touches Hermes Kanban completion semantics, worker completion protocol, or governance evidence attached to task completion.

## Core lesson

Existing UACP Kanban protection may cover task creation and dispatch without protecting the completion edge. For UACP-bound Kanban tasks, completion itself is a governance event: a worker must not be able to mark a governed task `done` without evidence and Guardian metadata.

Kanban remains coordination memory. UACP phase state remains in UACP artifacts (`state/current.yaml`, run manifests, transition artifacts). A Kanban `done` status is not a UACP phase transition.

## Required completion contract

For UACP-bound task completion, require completion metadata/evidence with at least:

- `uacp_run_id`
- `uacp_phase`
- `authority_artifact`
- `guardian_policy_version`
- `declared_side_effects`
- non-empty `evidence_refs`

The payload may be accepted as top-level metadata or nested under `uacp_completion`/`uacp`, but the semantic fields must be present. Compare the completion payload to the stored task governance context for at least run id, phase, and Guardian policy version. Mismatch should block completion before task state changes.

## Implementation pattern

1. Add an explicit `_UACP_COMPLETION_REQUIRED` field list near the existing UACP context schema.
2. Add a helper that extracts completion metadata from either top-level metadata or nested `uacp_completion` / `uacp`.
3. Add a helper that validates:
   - required fields are present,
   - `evidence_refs` is a non-empty string/list,
   - stored governance context exists,
   - run id / phase / policy version match the stored context.
4. In `complete_task()`, run the validation before any `tasks.status = 'done'` mutation.
5. On rejected completion, append an auditable event such as `completion_blocked_uacp_metadata`, then raise/return an error without changing task state.
6. On accepted completion, include a compact `uacp_completion` summary in the completed event payload.
7. Update model tool and CLI help text so workers know UACP-bound completion requires metadata/evidence.

## Verification pattern

Add targeted tests for:

- UACP-bound completion missing evidence is blocked and task remains non-terminal.
- UACP-bound completion with mismatched run/phase/policy metadata is blocked.
- UACP-bound completion with valid evidence succeeds.
- Non-UACP task completion remains unchanged.

Run both syntax checks and targeted tests. If the local pytest wrapper or repository config behaves oddly, the durable lesson is not that pytest is broken; use an explicit fallback such as `python -m pytest -c /dev/null tests/hermes_cli/test_uacp_kanban_guard.py -q` or invoke `pytest.main([...])` directly from Python as an alternate collection path, then record the successful command in the verification artifact.

## Phase-transition artifact pitfall

If council returns concerns that are accepted as non-blocking, keep strict transition `invariant_summary` and `cluster_summary` statuses within Heartgate's accepted vocabulary (usually `pass`). Put the concerns in `warnings` and `deferred_items` with owners, residual risk, acceptance, and conditions. Avoid invented statuses like `pass_with_concerns` unless the config explicitly supports them.

## Boundary reminders

- Do not require UACP completion metadata for ordinary non-governed Kanban tasks.
- Do not treat a Kanban task status as UACP lifecycle state.
- Do not push public Hermes upstream unless explicitly authorized.
- For UACP artifacts/state, use governed UACP writers; for Hermes Agent code, verify diffs/tests before reporting success.
