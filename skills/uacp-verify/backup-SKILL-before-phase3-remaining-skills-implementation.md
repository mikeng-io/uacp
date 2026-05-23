---
name: uacp-verify
description: Use when validating completed UACP work with adaptive evidence clusters and review routing.
---

# UACP Verify

## Heartgate Council distinction

VERIFY may run phase-local Agent Council to check the work product, but Heartgate owns transition-boundary coherence before VERIFY -> RESOLVE. Do not collapse these jobs. Phase-local review asks whether the verification package is good; Heartgate coherence asks whether the phase truthfully satisfied its lifecycle contract and whether docs/config/state/runtime/artifacts agree. Heartgate Council/coherence outputs belong under `verification/` and should be referenced from transition artifacts via `heartgate_coherence.artifact_path`; keep them separate from `council_synthesis_artifact`.

## Purpose
This skill verifies completed work against the actual artifact set using context-selected evidence clusters and councils when risk justifies it.

## Read first
- `UACP_ROOT/docs/index.md`
- `UACP_ROOT/docs/lifecycle-reference.md`
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

- `UACP_ROOT/docs/orchestration-model.md`
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
- If the run crosses a lifecycle boundary, verify the transition artifact through `uacp_heartgate_check` before claiming the boundary is valid. When `heartgate_coherence` is present, verify the referenced coherence artifact exists and covers doctrine coherence, cross-artifact consistency, runtime-state alignment, warning/deferred-item honesty, authority-plane integrity, and next-phase readiness.

If the council returns CONCERNS, do not claim final RESOLVE unless concerns are explicitly resolved, accepted as non-blocking risk, or deferred with owner/phase and acceptance criteria.

When council concerns touch a boundary that the next phase will build on (for example Guardian writer path containment, policy classification, Heartgate transition authority, or runtime tool exposure), prefer a small hardening patch before RESOLVE instead of carrying vague warnings forward. See `references/phase-end-council-hardening.md` for the concern-to-fix pattern, verification artifact shape, and manual-drill fallback rules.

## Containment hardening verification
When the remaining blocker is UACP-bound shell/code containment, verify fail-closed behavior explicitly instead of waiting for a future sandbox to exist. See `references/fail-closed-containment-proof.md` for the probe shape and artifact expectations.

When VERIFY runs Python validation under read-only UACP containment, do not treat bytecode-write failures as source failures. `python -m py_compile` may try to create `__pycache__` under the read-only tree. Prefer `PYTHONDONTWRITEBYTECODE=1` plus AST parsing for syntax checks, then run the artifact validator with bytecode writes disabled. See `references/read-only-containment-validation.md` for the command pattern and evidence fields.

For governance/runtime VERIFY phases, use `references/retrieval-led-phase-verify.md`: run deterministic validation first, explicitly validate current council synthesis artifacts, check `council_synthesis_artifact` vs `heartgate_coherence` separation, ground-truth any out-of-repo skill alignment, and only carry honest residuals into RESOLVE.

## Pre-PLAN codebase verification review
When acting as a verification reviewer before PLAN (e.g. the operator asks "what tests/dry-run fixtures and acceptance evidence are required before implementing or enabling live changes?"), use `references/codebase-verification-review-pattern.md`. This pattern inspects the existing codebase, maps test coverage, identifies gaps between design intent and implementation, defines required tests/fixtures, compiles blockers/concerns/suggestions, and produces a structured review artifact that gates PROPOSE → PLAN.

## Adversarial runtime review
Before claiming Guardian/Heartgate is production-complete, or after any host-runtime change that affects tool dispatch, run an adversarial review of the actual runtime source to find bypasses, hook gaps, and fail-open paths. See `uacp/references/adversarial-runtime-review.md` for the methodology, known bypass classes, and the mandatory questions that must be answered before enforcement can be claimed complete.



## Phase-specific operating contract — VERIFY

- **What this skill does:** prove implemented work satisfies proposal/plan and all carried findings are handled.
- **Why it does it:** separate actual correctness from implementation claims before RESOLVE.
- **How it does it:** run deterministic tests, inspect diffs/artifacts, dispatch retrieval-led VERIFY council, validate handled_findings_chain, run focused rerun for remediations, prepare VERIFY→RESOLVE transition.
- **Constraints:** do not accept summary-only reviews for governance/runtime claims; do not close with open blockers; do not conflate phase-local council with Heartgate.
- **Reason / rational intent / decisions:** intent is evidence closure: decisions are pass/warn/block, residual risk, deferred obligations, and whether RESOLVE may proceed.
- **Tools to use / not use:** use: validators, terminal tests, read/diff inspection, delegate_task council, uacp_heartgate_check; avoid: new feature implementation except minimal verification fixes routed back through EXECUTE/patch checkpoint.

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
