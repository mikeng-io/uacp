---
name: uacp-verify
description: Use when validating completed UACP work with adaptive evidence clusters
  and review routing.
phase: verify
allowed_tools:
- uacp_artifact_write
- uacp_state_write
- uacp_gate_ledger_append
- uacp_heartgate_check
- uacp_sandbox_check
- uacp_contained_shell
- uacp_run_registry_update
- uacp_escalation_event
forbidden_tools:
- terminal
- execute_code
phase_exit_invariants:
- artifact_glob: verification/{run_id}*
  required: true
- gate_ledger_entry: EXECUTE->VERIFY
  required: true
authority_source: config/phase-transitions.yaml (mirror; config wins on conflict)
---
# UACP Verify

## Heartgate Council distinction

VERIFY may run phase-local Agent Council to check the work product, but Heartgate owns transition-boundary coherence before VERIFY -> RESOLVE. Do not collapse these jobs. Phase-local review asks whether the verification package is good; Heartgate coherence asks whether the phase truthfully satisfied its lifecycle contract and whether docs/config/state/runtime/artifacts agree. Heartgate Council/coherence outputs belong under `verification/` and should be referenced from transition artifacts via `heartgate_coherence.artifact_path`; keep them separate from `council_synthesis_artifact`.

## Purpose
This skill verifies completed work against the actual artifact set using context-selected evidence clusters and councils when risk justifies it.

## Read first
- `UACP_ROOT/docs/INDEX.md`
- `UACP_ROOT/docs/lifecycle/lifecycle-reference.md`
- `UACP_ROOT/config/evidence-clusters.yaml`
- `UACP_ROOT/config/review-routing.yaml`

## Rules
- Do not use a fixed software-only checklist.
- Select verification evidence based on the task context.
- Record pass, warn, block, and deferred outcomes.
- Stop if the artifacts do not match the proposal or plan.
- When verification is intentionally scoped to a local branch / dry-run proof and remote or live side effects are held, label the result honestly as `pass_with_deferred_items` or equivalent, not full production readiness. Record non-actions explicitly (no push/PR, no DB mutation, no schedule mutation, no public delivery) and list the deferred proof boundary (for example: no Temporal workflow dry-run yet).

## Typical outputs
- verification artifact in `verification/`

## Updated doctrine alignment

Read additionally:

- `UACP_ROOT/docs/lifecycle/orchestration-model.md`
- `UACP_ROOT/config/phase-transitions.yaml`

VERIFY consumes actual artifacts, execution evidence, council synthesis artifacts, and selected evidence clusters.

Verification must check:

- phase-local granularity exit actual and composite granularity update,
- council findings use canonical states: `open`, `resolved`, `accepted_risk`, `not_applicable`, `deferred`,
- no unsupported finding dispositions are introduced,
- human involvement is required for unresolved CRITICAL findings or protected-action uncertainty,
- Evidence-Domain Registry is not claimed runtime-active while `implementation_status: not_runtime_active`.

Use Agent Council in verify/audit/review mode when phase-local risk, findings, or operator request justify it. For governance/runtime/artifact-management changes, make verification retrieval-led: first inspect the actual docs/config/scripts/runtime artifacts and require file/path/line or command evidence. A verification council must also check whether the behavior is wired into the relevant lifecycle skills/SOPs, not only described in canonical docs or config.

If the council returns blockers, concerns, invariant failures, negative findings, or material warnings, VERIFY must not normalize them into pass after explanation. Require a handled-findings chain: handling artifact, follow-up council when `remediated`/`expanded`/`justified` affects a boundary, or owner/residual risk/next-phase obligation when deferred/accepted/rejected. Cap follow-up council at one rerun and then block or escalate through Heartgate. docs/config/scripts/state artifacts, then dispatch role-diverse council reviewers, then synthesize blockers/concerns with file/path evidence. The council synthesis artifact should use `kind: uacp.council_synthesis` and record `inspected_paths` for ground-truth files, directories, commands, or evidence artifacts. Do not claim coherence from the main session's inferred understanding alone. Do not let a deterministic VERIFY evidence package substitute for council synthesis when the plan or operator requires a VERIFY council; create both artifacts and link the council synthesis from the transition.

## Phase-end council default

For UACP work, treat phase-end Agent Council as the default before formal RESOLVE, especially after phases that change governance, runtime bindings, Guardian/Heartgate behavior, lifecycle state, protected write paths, or execution policy. Run deterministic verification first, then a role-diverse Agent Council (Primary Reviewer, Devil's Advocate, Integration Checker, Synthesis Lead) to catch assumptions, boundary leaks, integration gaps, and governance drift.

Risk tiering:

- Low-risk docs/status-only updates: deterministic verification is sufficient; council optional.
- Medium-risk implementation/governance phases: deterministic verification + Agent Council before RESOLVE.
- High-risk enforcement, authority, lifecycle, profile-boundary, or containment phases: deterministic verification + Agent Council + formal audit/deep review when independent/runtime diversity materially improves confidence.
- If the run crosses a lifecycle boundary, verify the transition artifact through `uacp_heartgate_check` before claiming the boundary is valid. When `heartgate_coherence` is present, verify the referenced coherence artifact exists and covers doctrine coherence, cross-artifact consistency, runtime-state alignment, warning/deferred-item honesty, authority-plane integrity, and next-phase readiness. If Heartgate blocks on evidence disposition, add the required `Fact:`/`Disposition:` evidence files rather than weakening the transition artifact.

If the council returns CONCERNS, do not claim final RESOLVE unless concerns are explicitly resolved, accepted as non-blocking risk, or deferred with owner/phase and acceptance criteria.

When council concerns touch a boundary that the next phase will build on (for example Guardian writer path containment, policy classification, Heartgate transition authority, or runtime tool exposure), prefer a small hardening patch before RESOLVE instead of carrying vague warnings forward. See `references/phase-end-council-hardening.md` for the concern-to-fix pattern, verification artifact shape, and manual-drill fallback rules.

## Containment hardening verification
When the remaining blocker is UACP-bound shell/code containment, verify fail-closed behavior explicitly instead of waiting for a future sandbox to exist. See `references/fail-closed-containment-proof.md` for the probe shape and artifact expectations.

When VERIFY runs Python validation under read-only UACP containment, do not treat bytecode-write failures as source failures. `python -m py_compile` may try to create `__pycache__` under the read-only tree. Prefer `PYTHONDONTWRITEBYTECODE=1` plus AST parsing for syntax checks, then run the artifact validator with bytecode writes disabled. See `references/read-only-containment-validation.md` for the command pattern and evidence fields.

For governance/runtime VERIFY phases, use `references/retrieval-led-phase-verify.md`: run deterministic validation first, explicitly validate current council synthesis artifacts, check `council_synthesis_artifact` vs `heartgate_coherence` separation, ground-truth any out-of-repo skill alignment, and only carry honest residuals into RESOLVE.

For EXECUTE evidence sufficiency, use `references/piv-execution-evidence-contract.md`: VERIFY should judge the PLAN-authored PIV/evidence contract against EXECUTE checkpoints, semantic execution package, diffs/tests/probes, council synthesis, and handled findings. If the PIV contract is missing for non-trivial/governed work, or EXECUTE evidence is YAML-only/raw-file-list without rationale, decision, invariant, drift, and evidence mapping, return to EXECUTE or PLAN rather than improvising a pass.

For Heartgate-bound VERIFY→RESOLVE, use `references/heartgate-evidence-disposition-and-reload.md`: create per-cluster `verified-facts` and `assumptions` files with required `Fact:` / `Disposition:` markers when Heartgate asks for evidence disposition, prove both positive and negative enforcement fixtures, and record a runtime reload warning when plugin/kernel file edits are verified on disk but not hot-reloaded in the live tool process.

For EXECUTE phases that reference `kind: uacp.phase_intent_verification_contract`, use `../uacp-execute/references/phase-intent-verification-execute-evidence-20260519.md`: VERIFY must judge Phase Intent Verification satisfaction by inspecting the PLAN PIV contract, EXECUTE checkpoints, semantic execution package, evidence-obligation coverage, drift dispositions, and next-phase readiness. Do not reduce PIV to code implementation or raw test success.

## Pre-PLAN codebase verification review
When acting as a verification reviewer before PLAN (e.g. the operator asks "what tests/dry-run fixtures and acceptance evidence are required before implementing or enabling live changes?"), use `references/codebase-verification-review-pattern.md`. This pattern inspects the existing codebase, maps test coverage, identifies gaps between design intent and implementation, defines required tests/fixtures, compiles blockers/concerns/suggestions, and produces a structured review artifact that gates PROPOSE → PLAN.

## Adversarial runtime review
Before claiming Guardian/Heartgate is production-complete, or after any host-runtime change that affects tool dispatch, run an adversarial review of the actual runtime source to find bypasses, hook gaps, and fail-open paths. See `../references/adversarial-runtime-review.md` for the methodology, known bypass classes, and the mandatory questions that must be answered before enforcement can be claimed complete.



## Phase-specific operating contract — VERIFY

- **What this skill does:** prove implemented work satisfies proposal/plan and all carried findings are handled.
- **Why it does it:** separate actual correctness from implementation claims before RESOLVE.
- **How it does it:** run deterministic tests, inspect diffs/artifacts, dispatch retrieval-led VERIFY council, validate handled_findings_chain, run focused rerun for remediations, prepare VERIFY→RESOLVE transition.
- **Constraints:** do not accept summary-only reviews for governance/runtime claims; do not close with open blockers; do not conflate phase-local council with Heartgate.
- **Reason / rational intent / decisions:** intent is evidence closure: decisions are pass/warn/block, residual risk, deferred obligations, and whether RESOLVE may proceed.
- **Tools to use / not use:** use: validators, terminal tests, read/diff inspection, delegate_task council, uacp_heartgate_check; avoid: new feature implementation except minimal verification fixes routed back through EXECUTE/patch checkpoint.

This phase-specific contract complements `../references/agent-council-followthrough.md`; the shared reference supplies the common follow-through gate, while this section defines this phase's own job, intent, constraints, decisions, and tool boundary.

## Agent Council follow-through wiring

When this phase invokes or consumes Agent Council output, execute `../references/agent-council-followthrough.md` rather than treating council review as prose advice. In brief:

1. Select mode/tier/dispatch surface from UACP routing config and phase-local risk.
2. Dispatch retrieval-led roles when governance, runtime, artifact schema, Guardian/Heartgate, lifecycle, protected state, or skill behavior is involved.
3. Save `kind: uacp.council_synthesis` under `verification/` with `inspected_paths`, verdict, roles, findings, and evidence.
4. Extract all blockers, concerns, invariant failures, negative findings, and material warnings.
5. Do not advance the phase until every material finding is classified into the handled-findings matrix.
6. For `remediated`, `expanded`, or `justified` material findings, run one focused follow-up council unless a Heartgate-visible exception artifact is recorded.
7. Encode `handled_findings_chain`, `source_negative_findings_present`, and `followup_depth` in the transition artifact.
8. Run Heartgate after follow-through evidence exists; Agent Council synthesis is evidence, not transition approval.
9. Refuse next-phase adoption if the follow-through reference lists a refusal condition.


## VERIFY self-approval guard

VERIFY must not remediate its own material findings and then self-certify final closure. Any remediation discovered during VERIFY must be routed back through EXECUTE/patch checkpoint or a separate authorized repair step, then re-verified with independent council/audit evidence before RESOLVE.

## Autonomous self-closing loop

When this skill invokes or consumes Agent Council during skill-library repair, governance/runtime work, lifecycle state movement, or any other phase-local closure task, it must close the loop without external prompting:

1. Save the pre-change checkpoint and backup before implementation or state movement.
2. Run deterministic validation before council review so council participants inspect concrete evidence rather than intentions.
3. Run a full-perspective Agent Council and, when runtime/model diversity is requested or materially useful, an independent Kimi Code / Kimi K2.6 audit.
4. Classify every blocker, concern, invariant failure, negative finding, and material warning into the handled-findings matrix.
5. Remediate concrete findings with the smallest sufficient patch, then rerun focused verification until the result is `PASS` / no material concerns or a refusal condition is reached.
6. Preserve the recursion cap from `../references/agent-council-followthrough.md`: at most one focused follow-up council for the same finding chain unless the operator explicitly authorizes deeper recursion; unresolved material findings after the cap block closure or require recorded accepted risk/deferment with owner and condition.
7. Record `handled_findings_chain`, `source_negative_findings_present`, `followup_depth`, inspected paths, commands, and residual risks in the relevant checkpoint or transition artifact.

During this skill-library refactor specifically, do **not** use UACP protected writers, Heartgate, MEMEX/BES, or `uacp-verify` as self-approval authority. Use normal file/git workflow, deterministic audits, Agent Council, and Kimi verification. A skill is considered repaired only after its implementation audit and end-of-implementation council/audit return `PASS` with no material concerns.

## mode_behavior (Phase 4.3 stub)

This skill consults `config/autonomy-policy.yaml` to decide which actions
require operator confirmation per the active `state.current.uacp_mode`.

| mode | Behavior in VERIFY | Operator confirmation |
|---|---|---|
| manual | every action requires operator confirmation | yes (all transitions) |
| semi_auto | autonomous within-phase actions; operator confirms transitions | yes (transitions only) |
| supervised_auto | Per-cluster verified-facts and assumptions pair files; council-driven cluster reviews, autonomous | only on escalation triggers (see below) |
| full_auto | as supervised_auto, plus auto-confirming non-irreversible decisions | only on `trigger_irreversible_write` or `escalation_triggered` |

**Escalates when**: any unowned pending assumption, or council verdict=block, or PIV first failure.

**Mechanism**: when an escalation trigger fires, this skill emits a
`uacp_escalation_event` record into `state/escalations/{run_id}.jsonl`
(severity ∈ {info, warn, block}). Operators poll the file (push-notify
is Phase 5). See `config/autonomy-policy.yaml#escalation_triggers` for
the registered triggers.

## Phase Intent Verification assessment

When EXECUTE references a PIV contract, VERIFY must assess Phase Intent Verification satisfaction before accepting EXECUTE→VERIFY or VERIFY→RESOLVE claims.

VERIFY must inspect:

- `plans/{run_id}-piv.yaml`
- `executions/{run_id}-checkpoint-*.yaml`
- `executions/{run_id}/00-index.md` and semantic evidence modules
- evidence obligation results, deferred items, intent drift dispositions, and next-phase readiness

VERIFY should decide one of:

- `pass`: PIV obligations satisfied and semantic evidence is recoverable.
- `pass_with_deferred_items`: missing/non-live items are explicitly owned and accepted.
- `block_return_to_execute`: EXECUTE must produce missing evidence or fix drift handling.
- `block_return_to_plan`: PLAN intent or PIV contract is invalidated and needs re-plan.

Do not treat test success, raw diffs, or worker self-report as sufficient when the PIV contract requires broader evidence.


## Adaptive VERIFY evidence package

Reference: `../references/lifecycle-semantic-gates-20260519.md` summarizes the lifecycle semantic-gate pattern and the user correction that VERIFY is not optional follow-through: it is the truth boundary before RESOLVE.

For governed/non-trivial VERIFY work, VERIFY must produce validator-backed truth evidence rather than only a loose verification summary.

Reference: `references/adaptive-verify-evidence-gate.md` captures the session-derived gate shape, negative fixtures, and pre/post council sequence.

For governed/non-trivial VERIFY work, especially when EXECUTE used a PIV contract, VERIFY must produce a validator-backed evidence package rather than a summary-only YAML artifact.

Required machine artifacts when selected:

- `verification/{run_id}-verify-selection.yaml` with `kind: uacp.verification_package`
- `verification/{run_id}-piv-assessment.yaml` with `kind: uacp.piv_assessment` when EXECUTE used PIV
- `verification/{run_id}-resolve-readiness.yaml` with `kind: uacp.verify_resolve_readiness`

Required semantic package:

- `verification/{run_id}/00-index.md`
- `piv-assessment.md`
- `verified-facts.md`
- `assumptions-and-deferred-items.md`
- `findings-and-dispositions.md`
- `council-review.md`
- `resolve-readiness.md`

VERIFY must keep verified facts separate from assumptions/deferred items. Facts require source evidence; assumptions and deferred items require owner, accepted_by, residual risk, and next-phase obligation. `ready_for_resolve: true` is invalid with open blockers, missing required PIV assessment, missing Heartgate coherence when required, or failed self-approval guard.

If VERIFY discovers a material issue, route back to EXECUTE for missing/fixable evidence or to PLAN for invalidated intent/contract. Do not remediate material findings inside VERIFY and self-certify closure.

## Operator phase-return presentation

Default Telegram/Discord phase returns MUST follow the operator summary layer from `UACP_ROOT/docs/reference/operator-phase-return-schema.md`. Return information, not raw data.

Required shape:

1. **Conclusion** — phase + status + one-sentence result.
2. **What changed** — 1-3 meaning-level bullets, not file inventories.
3. **Why it matters** — rational intent / consequence.
4. **Decision** — pass/warn/block/in-progress and rationale.
5. **Invariants** — preserved constraints that matter for this phase.
6. **Risks** — only material residual risks and handling.
7. **Next** — recommended next action and whether operator input is required.
8. **Evidence pointer** — commit, artifact index, or verification summary; say raw details are available on request.

Suppress by default: full edited-file lists, newly-created-file lists, raw `git diff --stat`, raw validation logs, raw council transcripts, and complete artifact inventories. Include specific paths only when a path is the decision subject, a blocker/error depends on it, rollback needs it, or the operator explicitly asks for audit detail.

This is a presentation rule only. Preserve complete raw evidence in UACP artifacts, gate ledgers, commits, and verification records.

