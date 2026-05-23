# Phase 6 Agent Council Operationalization Lessons — 2026-05-15

Use this reference when UACP work touches Agent Council operationalization, council synthesis schemas, retrieval-led councils, or phase transition evidence.

## Reusable pattern

1. **Start with existing doctrine, not a greenfield protocol.** For Agent Council work, baseline against:
   - `docs/orchestration-model.md`
   - `docs/lifecycle-reference.md`
   - `config/review-routing.yaml`
   - `config/phase-transitions.yaml`
   - `plans/uacp-agent-council-followthrough/`

2. **Surface inventory before patches.** Create a verification artifact that inventories canonical docs/config/scripts/skills/prior plans and classifies each as `reuse`, `patch`, `defer`, or `out_of_scope`. This prevents duplicate doctrine and makes EXECUTE bounded.

3. **Retrieval-led council output needs path evidence.** Council prompts should name concrete files/artifacts to inspect. Synthesis artifacts should record `inspected_paths` or equivalent, plus finding evidence with paths. Summary-only council review is not sufficient for runtime/governance correctness claims.

4. **Patch earlier invalid transitions before moving on.** If PLAN council discovers a previous transition artifact fails validator/Heartgate policy (invalid enum, missing required `heartgate_coherence`, etc.), patch the transition artifact immediately. Do not preserve a known-invalid transition as historical truth.

5. **Keep council artifacts separate.** Phase-local Agent Council synthesis belongs in `verification/` as `kind: uacp.council_synthesis` and is referenced by `council_synthesis_artifact`. Heartgate/transition coherence belongs in `heartgate_coherence.artifact_path`. Do not collapse them unless the artifact explicitly covers both roles.

6. **Model routing belongs in operator/runtime config, not canonical doctrine.** It is fine to use a user-preferred delegate route operationally, but canonical proposal/docs/config should remain model-agnostic and refer to configured routing.

7. **Read-only containment syntax checks.** `python -m py_compile` may fail under read-only UACP containment because it writes bytecode. Prefer `PYTHONDONTWRITEBYTECODE=1` with `ast.parse(...)` for syntax checks, then run `scripts/validate_uacp_artifacts.py` separately.

## Common plan-council remediation items

- Add rollback checkpoint and verification command before PLAN→EXECUTE.
- Confirm governed writer tool availability before docs/config mutation.
- Decide validator gaps explicitly: implement now or record accepted risk with owner/condition.
- Defer Kanban-backed council automation unless current operating posture explicitly allows it.
- If skill alignment is conditional, state whether skill files are in-tree or out-of-tree and when they will be patched.

## Verification checklist

Before PLAN→EXECUTE for Agent Council protocol work:

- Surface inventory exists.
- PLAN council synthesis exists with inspected paths.
- Prior transition artifacts pass validator.
- `scripts/validate_uacp_artifacts.py` returns `RESULT PASS`.
- PLAN→EXECUTE transition carries owned warnings/deferred items and Heartgate coherence where policy requires it.
