---
name: uacp-resolve
description: Use when closing a UACP run, extracting lessons, and deciding memory or skill updates.
---

# UACP Resolve

## Purpose
This skill closes the run, captures lessons, decides what belongs in memory, and determines whether a new skill or doc update is warranted.

## Read first
- `UACP_ROOT/docs/index.md`
- `UACP_ROOT/docs/lifecycle-reference.md`
- `UACP_ROOT/config/memory-policy.yaml`

## Rules
- Keep the learning artifact compact.
- Separate useful lessons from one-off noise.
- Do not put high-volume gate-learning into personal memory.
- Use `knowledge/` for durable run learning.

## Typical outputs
- outputs/
- knowledge/
- lesson artifact or run summary

## Updated doctrine alignment

Read additionally:

- `UACP_ROOT/docs/orchestration-model.md`
- `UACP_ROOT/config/phase-transitions.yaml`

RESOLVE closes the run only after verification evidence, council findings, accepted risks, and human involvement requirements are settled.

Before marking a run resolved, ensure any phase transition that led here was validated by `uacp_heartgate_check`, and ensure canonical docs/config deltas used `uacp_doc_write` / `uacp_config_write` where applicable.

For UACP governance, lifecycle, Heartgate/Guardian, artifact-schema, runtime-enforcement, or Agent Council changes, RESOLVE must also check skill-level orchestration wiring. Do not close as clean pass if the change only updated docs/config/validator while the relevant lifecycle skills do not explain who dispatches councils, what synthesis artifact is produced, how handled negative findings are encoded, and how Heartgate gates progression. If any council finding remains material, require a handled-findings chain or record residual risk/owner/next-phase obligation before closure.

Resolution should record:

- final phase-local and composite granularity,
- remaining accepted risks and owners,
- lessons for `knowledge/`,
- whether UACP skills or validators need updates,
- whether any skill updates happened outside the UACP repo boundary (for example Hermes skill storage),
- whether downstream agent-skills extraction should happen now or remain deferred.
- whether any operationally relevant skill changes live outside the UACP repo commit boundary. If skill alignment was inspected via `skill_view`, state that clearly as an external skill-store dependency rather than implying the change is backed by the UACP git commit.

## Closure sequence checklist

When a run is still in EXECUTE but implementation and council review are complete, do not jump straight to a terminal summary. Close the lifecycle explicitly:

1. Create or refresh a compact verification/readiness artifact that names the proof commands/results, council artifact, residual risks, and whether the work enabled any new runtime authority.
2. Write the `execute -> verify` transition artifact and run `uacp_heartgate_check` on it.
3. Write the `verify -> resolve` transition artifact and run `uacp_heartgate_check` on it.
4. Only after Heartgate returns pass/warn with no blockers, mark the plan/run manifest as resolved and create a compact resolution artifact.
5. If starting the next phase immediately, create a new TRIAGE artifact/run manifest and update `state/current.yaml` after the previous run is resolved.

Heartgate schema pitfalls found in practice:

- `deferred_items` must include `owner`, `condition`, and `accepted_by`; missing `accepted_by` blocks transition.
- `warnings` should be maps with at least `id`, `owner`, and `residual_risk`; plain string warnings can block when accepted-warning metadata is required.
- Transition artifacts commonly require top-level `decision`, `authority`, `phase_local_granularity`, `composite_granularity`, `human_involvement`, `blockers: []`, `artifact_paths: [...]`, and `heartgate_coherence`. Missing these can block otherwise valid `execute -> verify` or `verify -> resolve` transitions.
- Use lowercase transition phase names (`from_phase: execute`, `to_phase: verify`) if Heartgate rejects uppercase identifiers as “transition not allowed.”
- `invariant_summary` and `cluster_summary` must be lists of maps, not a single map. If Heartgate throws `AttributeError: 'str' object has no attribute 'get'`, check for this shape error first.
- If Heartgate says `invariant <name> is missing`, use `invariant_summary` entries with `name` + `status`; if it says `cluster unknown has invalid state: missing`, use `cluster_summary` entries with `id` + `state`. The transition config/examples may mix naming conventions.
- If transition policy requires it, include `heartgate_coherence` with `status`, `artifact_path`, all required lenses (`doctrine_coherence`, `cross_artifact_consistency`, `runtime_state_alignment`, `warning_and_deferred_item_honesty`, `authority_plane_integrity`, `next_phase_readiness`), and a concise `summary`. Use `status: warn` when accepted warnings/deferred items remain; keep invariant/cluster statuses canonical rather than inventing `pass_with_concerns`.
- Evidence-only closure is valid only when the resolution states what was *not* enabled and carries the remaining allow-path work into owned deferred items.
- After Heartgate returns `warn` with no blockers, write a compact run manifest or resolution pointer so future sessions can see the run is resolved for its declared scope without replaying the full conversation.

Reference: `references/phase-resolution-heartgate.md` captures a concrete closure pattern and schema example.
- Evidence-only closure is valid only when the resolution states what was *not* enabled and carries the remaining allow-path work into an owned deferred item.

Reference: `references/phase-resolution-heartgate.md` captures a concrete closure pattern and schema example.

Do not store high-volume gate outcomes in personal memory. Use durable UACP artifacts/knowledge.



## Phase-specific operating contract — RESOLVE

- **What this skill does:** close the run, archive outputs, record lessons, and decide memory/skill/doc follow-up.
- **Why it does it:** prevent unresolved risk or skill drift from being mislabeled complete.
- **How it does it:** load final transitions, verify Heartgate pass/warn, ensure all council findings have handled chain or accepted residual risk, write resolution artifact, update skills/memory only for durable lessons.
- **Constraints:** do not close if Heartgate blocks, follow-through is incomplete, or artifacts disagree; do not save stale task progress to memory.
- **Reason / rational intent / decisions:** intent is durable closure: decisions are resolved scope, residual risks, future work, skill/memory updates, and non-actions.
- **Tools to use / not use:** use: read/validator/session artifacts, skill_manage for durable skill fixes, memory only for stable facts, uacp_heartgate_check when boundary state is touched; avoid: implementation changes, broad memory dumps, public/external actions.

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
