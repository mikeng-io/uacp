---
name: uacp-propose
description: Use when creating governed UACP proposals, bootstrap artifacts, or authority declarations.
---

# UACP Propose

## Purpose
This skill creates the proposal artifact that states why the work exists, who authorized it, what changes are in scope, and what side effects are declared.

## Read first
- `UACP_ROOT/docs/index.md`
- `UACP_ROOT/docs/constitution.md`
- `UACP_ROOT/docs/lifecycle-reference.md`
- `UACP_ROOT/config/evidence-clusters.yaml`

## Rules
- Capture authority, scope, side effects, and containment explicitly.
- Keep the proposal bounded and reviewable.
- Do not jump into planning before the proposal is viable.
- **Do not skip TRIAGE adoption** — Before treating a proposal as adopted, verify that the originating TRIAGE phase is complete enough for the request class. For governance-core work touching lifecycle semantics, Agent Council, Heartgate/Guardian, protected state, artifact schemas, or runtime enforcement, check for TRIAGE council/transition evidence when selected. If proposal artifacts were drafted early, mark them provisional and adopt/patch them only after TRIAGE→PROPOSE transition.
- **Reference the triage artifact** — Every proposal must link to its originating triage artifact (`state/runs/*-triage.yaml`) to maintain traceability.
- **Scope must be implementable** — If the user says "this is a medium spec", treat it as a signal to keep the proposal bounded and avoid over-engineering.
- **MUST create gate-selection artifact** — Per `lifecycle-reference.md`, PROPOSE requires an `initial gate-selection artifact` with:
  - `selection_id`, `run_id`, `phase`
  - `domains`, `artifact_types`
  - `risk_level`, `granularity_level`
  - `invariant_checks` (all non-waivable invariants with pass/block status + reason)
  - `selected_clusters` (required / optional / generated)
  - `not_applicable` clusters with reason
  - `transition_requirements`
  - `reasoning`
  See `config/gate-selection.yaml` for full schema.
- **Agent council review is context-selected, not automatically external** — If user requests council review or the proposal risk/routing requires it, select the council surface from UACP routing doctrine. Delegate Task / Kimi-style local council is acceptable for bounded proposal critique when it provides sufficient perspective; external bridges are escalation paths only when scale, runtime diversity, independence, or verification confidence materially justify them.
- **Audit trail is required** — Record all significant events (issue report, diagnosis, council dispatch, operator decisions) with timestamps and actors.
- **Validator shape matters** — Proposal artifacts should include validator-required fields (`phase: propose`, `triage_artifact`, `objective`, `scope.in_scope`, `scope.out_of_scope`, `declared_side_effects`, `authority.status`, and `human_involvement`) even when richer aliases such as `originating_triage_artifact` are also present.

## Typical outputs
- proposal artifact in `proposals/`
- gate-selection artifact in `proposals/` (name: `<proposal-id>-gate-selection.yaml`)
- reference to originating triage artifact

## Updated doctrine alignment

Read additionally:

- `UACP_ROOT/docs/orchestration-model.md`
- `UACP_ROOT/config/review-routing.yaml`
- `UACP_ROOT/config/phase-transitions.yaml`

Do not require external bridge dispatch merely because work is medium-sized. Select Agent Council mode/tier from phase-local granularity, risk, domains, side effects, and evidence need.

PROPOSE should record:

- phase-local granularity entry/exit estimate,
- updated downstream projections,
- human involvement requirement if authority or side effects are unclear,
- Agent Council proposal critique only when selected by routing policy or requested.

If the proposal changes canonical docs/config or will end in a phase transition, state that the eventual implementation must use `uacp_doc_write` / `uacp_config_write` for docs/config and `uacp_heartgate_check` for the transition artifact.

If council is used, record a council synthesis artifact matching `config/phase-transitions.yaml#council_synthesis_schema` instead of ad hoc `agent_council:` prose.

## Proposal-council remediation pattern

For UACP governance/runtime/council proposals, proposal council findings should be converted into concrete proposal/gate-selection patches before PROPOSE→PLAN. If TRIAGE council was selected or later found necessary, do not treat PROPOSE as adopted until the TRIAGE council synthesis and TRIAGE→PROPOSE transition are recorded.

For handled negative council findings, use the follow-through gate: remediated/expanded/justified material findings require handling evidence and follow-up Agent Council where selected; deferred/accepted_warning/rejected_with_reason findings require Heartgate-visible owner, residual risk, and next-phase obligation.

For UACP governance/runtime/council proposals, proposal council findings should be converted into concrete proposal/gate-selection patches before PROPOSE→PLAN:

1. Record the council as a `uacp.council_synthesis` artifact with reviewed/inspected paths and file/path evidence.
2. Patch the proposal and gate-selection artifacts for council concerns when they affect scope, artifact contracts, model routing, or transition requirements. Do not leave actionable proposal concerns as vague PLAN warnings.
3. Keep canonical artifacts model-agnostic. Operational model preferences may be recorded as operator constraints, but avoid hardcoding transient model names in docs/config/proposal design rules.
4. If prior planning packages exist, require PLAN to inventory them and mark items `reuse`, `patch`, `defer`, or `out_of_scope`; this prevents Phase 6-style duplicate doctrine drift.
5. When dispatching proposal council via bounded delegates, explicitly state whether file writes are allowed. For critique-only councils, forbid writes and keep toolsets narrow. After delegates return, inspect the target workspace for untracked/modified files and record any out-of-band side effects in the council synthesis before advancing.
6. For full-governance/high-granularity transitions, check current `phase-transitions.yaml` policy before assuming `heartgate_coherence` is optional. If the validator or Heartgate requires it, add the coherence block rather than rationalizing the omission.

When proposal council returns CONCERNS but no blockers, do not advance by summary alone. First write the council synthesis artifact, patch the proposal and gate-selection artifacts to resolve or explicitly carry each concern, run artifact validation, then create the PROPOSE→PLAN transition. Keep transient model/provider names out of canonical proposal text; record them as operator constraints or runtime routing evidence rather than doctrine.

### Validator and Heartgate artifact-shape pitfalls

Recent runs showed that proposal/council/transition artifacts can be logically correct but still fail validators or Heartgate because their shape is too freeform. Preserve these concrete requirements when preparing PROPOSE→PLAN:

- Proposal artifacts must include validator-required top-level fields: `phase: propose`, `triage_artifact`, `objective`, `scope.in_scope`, `scope.out_of_scope`, `declared_side_effects`, `authority.status` as `pass|warn|block`, and `human_involvement`. Richer aliases such as `originating_triage_artifact` are fine but do not replace the required fields.
- Council synthesis artifacts must use canonical shape, not prose only: `council_id`, `mode`, `tier`, `phase`, `phase_local_granularity`, `roles`, `dispatch_surfaces`, `findings`, `verdict`, `artifact_paths`, and `inspected_paths`. Convert delegate summaries into `findings` with accepted states such as `resolved`, `deferred`, `accepted_risk`, `not_applicable`, or `open`.
- Transition artifacts consumed by Heartgate should use list-shaped `invariant_summary` and `cluster_summary` entries (`id/status/evidence`, `cluster_id/state/artifact_path`). Avoid mapping-shaped summaries that may parse as YAML but break item-based Heartgate checks.
- Heartgate warning/deferred encoding must include owner and carry-forward details. For warnings use `owner`, `residual_risk`, and `next_phase_acceptance`; for deferred items use `id`, `cluster_id`, `owner`, `condition`, and `accepted_by`; add `accepted_exceptions` for warning clusters intentionally carried into PLAN.
- Run both checks: first the lightweight artifact validator, then `uacp_heartgate_check`. Patch any Heartgate blockers into the artifact contract instead of bypassing the gate.



## Phase-specific operating contract — PROPOSE

- **What this skill does:** produce bounded proposal: objective, authority, in/out scope, side effects, non-goals, gate-selection, and proposal council response.
- **Why it does it:** ensure work is authorized and coherent before planning implementation.
- **How it does it:** load triage/gate policy, draft proposal artifacts, run proposal council when selected, classify council findings, require follow-through before proposal adoption, prepare PROPOSE→PLAN transition.
- **Constraints:** do not execute implementation; do not silently accept concerns; no destructive/external actions; no bypass of missing TRIAGE evidence.
- **Reason / rational intent / decisions:** intent is authority framing: decide what is being proposed and why it is allowed; decisions are scope, side effects, risks, accepted non-goals, required gates.
- **Tools to use / not use:** use: file reads, delegate_task council, validator, uacp_heartgate_check; avoid: implementation tools except artifact drafting, direct production/runtime mutation.

This phase-specific contract complements `references/agent-council-followthrough.md`; the shared reference supplies the common follow-through gate, while this section defines this phase's own job, intent, constraints, decisions, and tool boundary.

## Agent Council follow-through wiring

When this phase invokes or consumes Agent Council output, execute `references/agent-council-followthrough.md` rather than treating council review as prose advice. In brief:

1. Select mode/tier/dispatch surface from UACP routing config and phase-local risk.
2. Dispatch retrieval-led roles when governance, runtime, artifact schema, Guardian/Heartgate, lifecycle, protected state, or skill behavior is involved.
3. Save `kind: uacp.council_synthesis` under `verification/` with `inspected_paths`, verdict, roles, findings, and evidence.
4. Extract all blockers, concerns, invariant failures, negative findings, and material warnings.
5. Do not advance the phase until every material finding is classified into the handled-findings matrix.
6. For `remediated`, `expanded`, or `justified` material findings, run one focused follow-up council unless a Heartgate-visible exception artifact is recorded.
7. Encode `handled_findings_chain`, `source_negative_findings_present`, and `followup_depth` in the transition artifact.
8. Run Heartgate after follow-through evidence exists; Agent Council synthesis is evidence, not transition approval.
9. Refuse next-phase adoption if the follow-through reference lists a refusal condition.
