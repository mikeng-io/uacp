# Surface Inventory — Council Follow-Through Gate

Run: `council-followthrough-gate-20260514-201718`
Phase: PLAN
Status: patched after PLAN council

## Canonical docs

- `docs/lifecycle-reference.md`
  - Disposition: **patch**
  - Required delta: define follow-through gate; separate TRIAGE council from PROPOSE council; state high-granularity governance-core TRIAGE may require Agent Council and TRIAGE→PROPOSE Heartgate coherence.

- `docs/runtime-enforcement.md`
  - Disposition: **patch**
  - Required delta: describe Heartgate detection of handled negative findings; require fail-closed behavior when required follow-up evidence is missing; preserve council-as-evidence / Heartgate-as-approval separation.

- `docs/orchestration-model.md`
  - Disposition: **patch**
  - Required delta: define follow-through council as bounded rerun/follow-up under existing Agent Council routing; include scope bounds and `max_followup_depth_default: 1` policy.

- `docs/index.md`
  - Disposition: **defer / maybe patch**
  - Reason: Patch only if EXECUTE changes document registry/decision log requirements.

## Canonical config

- `config/phase-transitions.yaml`
  - Disposition: **patch with schema extension**
  - Required delta:
    - Add optional `handled_findings_chain` under `artifact_schema.fields` with item fields from `02-requirements-and-design.md`.
    - Add `accepted_exceptions` to `artifact_schema.fields` if absent, matching existing Heartgate-compatible transition practice.
    - Add `followthrough_gate` or equivalent config block with `max_followup_depth_default: 1`, hard/conditional handling classes, and fail-closed defaults.

- `config/review-routing.yaml`
  - Disposition: **patch**
  - Required delta:
    - Add TRIAGE-local council trigger rule: phase `triage` plus granularity >= 7 or governance-core domains.
    - Add follow-through council tier selection: tier_1 for material concerns, tier_2 for blockers/invariant failures/authority-boundary changes.
    - Ensure `triage` is represented where council modes are enumerated, if such an enum exists.

- `config/gate-selection.yaml`
  - Disposition: **patch**
  - Required delta: add handled-negative-result classification inputs/evidence selection semantics and material warning threshold, without fixed numbered gates.

- `config/evidence-clusters.yaml`
  - Disposition: **patch unless exact equivalent exists at EXECUTE inspection time**
  - Required delta: promote `handled_negative_result_followthrough` from generated cluster into a universal cluster family or a named generated-template cluster.

## Validator/runtime surfaces

- `scripts/validate_uacp_artifacts.py`
  - Disposition: **patch**
  - Required delta:
    - Validate transition `handled_findings_chain` shape when present.
    - Validate `handling_classification` vocabulary.
    - Validate `followup_required: true` implies non-empty `followup_council_synthesis_artifact`.
    - Validate non-waivable invariants in transition `invariant_summary` use `pass|block` only.
    - Validate warnings/deferred items keep owner/residual-risk/acceptance fields.

- Heartgate runtime/tool implementation
  - Disposition: **inspect then patch only if UACP-owned and necessary**
  - Reason: Prefer config/validator/doc enforcement first; do not broaden runtime edits unless the live Heartgate tool has an owned policy hook for handled findings.

## Skills

Skill targets live under `HERMES_ROOT/skills/devops/uacp/`, not under `UACP_ROOT`.

- `HERMES_ROOT/skills/devops/uacp/SKILL.md`
  - Disposition: **verify then patch if stale**
  - Reason: It already contains follow-through gate notes; align wording after canonical docs/config patches.

- `HERMES_ROOT/skills/devops/uacp/uacp-triage/SKILL.md`
  - Disposition: **patch**
  - Required delta: warn not to compress TRIAGE into PROPOSE for high-granularity governance-core work; require TRIAGE council where routing selects it.

- `HERMES_ROOT/skills/devops/uacp/uacp-propose/SKILL.md`
  - Disposition: **patch if needed**
  - Required delta: reference follow-through gate and preserve TRIAGE correction boundary.

- `HERMES_ROOT/skills/devops/uacp/uacp-plan/SKILL.md`
  - Disposition: **patch if needed**
  - Required delta: require surface inventory/gap map and follow-through negative/regression verification.

## Prior artifacts

- `plans/uacp-agent-council-followthrough/`
  - Disposition: **reuse as background only**
  - Reason: Older package may contain implementation context, but this run owns the specific negative-result follow-through gate and TRIAGE sequencing correction.

- Current early PROPOSE artifacts
  - Disposition: **adopted after correction**
  - Reason: TRIAGE council and TRIAGE→PROPOSE transition now exist; PROPOSE artifacts are valid upstream inputs.

## Out of scope

- Production infrastructure changes.
- External public posting or messaging.
- Credential/secret handling.
- Broad Hermes core edits unless a missing extension seam is documented and separately authorized.
