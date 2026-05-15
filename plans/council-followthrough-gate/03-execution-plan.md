# Execution Plan — Council Follow-Through Gate

Run: `council-followthrough-gate-20260514-201718`
Phase: PLAN
Status: patched after PLAN council

## Authority and side-effect boundary

Authorized in EXECUTE after PLAN→EXECUTE Heartgate passes:

- Patch UACP canonical docs/config listed in the surface inventory.
- Patch UACP lightweight validator and lifecycle skills only if required to align with canonical docs/config.
- Write verification artifacts.

Not authorized:

- Production infrastructure changes.
- External posts/messages.
- Credential/secret handling.
- Broad Hermes core edits.
- UACP runtime adapter edits unless the target is identified as UACP-owned and necessary after inspection.

## Work package E1 — canonical doctrine patches

Targets:

- `docs/lifecycle-reference.md`
- `docs/runtime-enforcement.md`
- `docs/orchestration-model.md`

Actions:

1. Add follow-through gate language to lifecycle reference.
2. Add TRIAGE council/Heartgate selection rule for high-granularity governance-core admission:
   - phase is `triage`, and
   - composite or phase-local granularity >= 7, or domains include `agent_council`, `heartgate`, `guardian`, lifecycle semantics, artifact schema, runtime enforcement, or protected state.
3. State TRIAGE council scope: admission/routing/scope/granularity only.
4. State PROPOSE council scope: authority/side effects/proposal quality.
5. Add Heartgate enforcement responsibility for handled findings.
6. Add Agent Council rerun/follow-up scope and recursion cap to orchestration model.

Write surface: `uacp_doc_write`.

## Work package E2 — canonical config patches

Targets:

- `config/phase-transitions.yaml`
- `config/review-routing.yaml`
- `config/gate-selection.yaml`
- `config/evidence-clusters.yaml` unless exact equivalent exists.

Actions:

1. Add optional `handled_findings_chain` under `config/phase-transitions.yaml#artifact_schema.fields`.
2. Add `accepted_exceptions` under `artifact_schema.fields` if absent, because current Heartgate-compatible transitions already use it.
3. Add a machine-readable follow-through policy block, preferably under `phase-transitions.yaml`, containing:
   - `max_followup_depth_default: 1`
   - hard follow-up handling classes: `remediated`, `expanded`, `justified`
   - conditional handling classes: `deferred`, `accepted_warning`, `rejected_with_reason`
   - fail-closed behavior for missing required follow-up evidence.
4. Add TRIAGE-local council trigger rule to `review-routing.yaml` and include `triage` in council-mode enums if present.
5. Add follow-through council tier selection rule to `review-routing.yaml`:
   - tier_1 bounded for concerns/material warnings
   - tier_2 role-diverse for blockers, invariant failures, authority-boundary changes, lifecycle schema/runtime changes.
6. Add handled-negative-result evidence selection semantics and material warning threshold to `gate-selection.yaml`.
7. Promote `handled_negative_result_followthrough` into `config/evidence-clusters.yaml` as a universal cluster family or named generated-template cluster.
8. Preserve adaptive gate selection; do not introduce fixed numbered gates.

Write surface: `uacp_config_write`.

## Work package E3 — validator alignment

Target:

- `scripts/validate_uacp_artifacts.py`

Minimum validator checklist:

1. `handled_findings_chain` item shape when present:
   - required: `original_finding_id`, `finding_classification`, `handling_classification`, `handling_artifact_path`, `followup_required`, `owner`, `residual_risk`, `heartgate_validation`.
   - optional but validated if present: `original_artifact_path`, `followup_council_synthesis_artifact`, `next_phase_obligation`.
2. Classification vocabulary:
   - finding: `blocker`, `concern`, `invariant_failure`, `negative_finding`, `material_warning`.
   - handling: `remediated`, `expanded`, `justified`, `deferred`, `accepted_warning`, `rejected_with_reason`.
3. Consistency:
   - `followup_required: true` requires non-empty `followup_council_synthesis_artifact`.
   - `handling_classification` in hard follow-up classes should normally set `followup_required: true` unless an accepted exception exists.
4. Invariant vocabulary:
   - transition `invariant_summary[].status` must be `pass` or `block`; reject `warn`, `deferred`, or ad-hoc variants.
5. Warning/deferred shape:
   - warnings require `owner`, `residual_risk`, `next_phase_acceptance`.
   - deferred items require `id`, `cluster_id`, `owner`, `condition`, `accepted_by`.

Avoid overbuilding into a full schema engine.

Write surface: guarded code/artifact path if available. If no governed code writer exists for scripts, record writer-surface gap and defer validator code changes rather than using ungoverned mutation.

## Work package E4 — skill alignment

Targets under `HERMES_ROOT/skills/devops/uacp/`:

- `SKILL.md`
- `uacp-triage/SKILL.md`
- `uacp-propose/SKILL.md`
- `uacp-plan/SKILL.md`

Actions:

1. Ensure skills match canonical docs/config after E1/E2.
2. Add explicit warning not to compress TRIAGE into PROPOSE when TRIAGE council is selected.
3. Keep skills downstream; if conflict appears, docs/config win.

Write surface: `skill_manage` after canonical docs/config are patched.

## Work package E5 — verification artifacts and transition

Actions:

1. Run YAML parse and UACP validator.
2. Run synthetic transition tests:
   - valid remediated finding with follow-up council passes/warns appropriately
   - remediated blocker missing follow-up council blocks
   - deferred warning missing owner/next-phase acceptance blocks
   - non-waivable invariant with `warn` blocks
   - high-granularity governance-core TRIAGE without selected council/Heartgate evidence warns or blocks according to implemented routing policy.
3. Run EXECUTE phase-local council if selected.
4. Create EXECUTE→VERIFY transition only after patches and tests.

## Execution topology

- Main session orchestrates and verifies.
- Delegate/Agent Council used for PLAN council and later verification critique.
- Kanban not required unless EXECUTE becomes long-running or split across workers.
- External coding agents not required unless validator/runtime adapter changes become broad or subtle.

## Rollback

Before canonical mutation, record current git diff / file contents. Rollback is revert of changed docs/config/scripts/skills. No external side effects are expected.
