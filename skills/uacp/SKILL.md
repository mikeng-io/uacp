---
name: uacp
description: Router for Universal Agent Control Plane governance, lifecycle, and state work.
kind: orchestration
version: 2.1.0
metadata:
  hermes:
    tags:
      - governance
      - lifecycle
      - multi-agent
      - router
    related_skills:
      - uacp-triage
      - uacp-propose
      - uacp-plan
      - uacp-execute
      - uacp-verify
      - uacp-resolve
      - uacp-state
      - uacp-context
      - uacp-brainstorm
      - uacp-council
      - uacp-debate
      - uacp-parallel
---

# Universal Agent Control Plane — Router

UACP is the generic, unified, adaptive control-plane doctrine for governed agentic work. It decides whether work needs lightweight handling or a full lifecycle run, and then routes to the appropriate phase skills.

## Lifecycle semantic gate reference

For UACP lifecycle hardening, validator gates, or phase-skill repair, read `../uacp-core/references/lifecycle-semantic-gates.md` before claiming a phase chain is complete. It captures the PROPOSE/PLAN/EXECUTE/VERIFY/RESOLVE semantic-gate pattern, the PIV naming correction, and the VERIFY/RESOLVE pitfalls Mike corrected in-session.

## When to use

Use when the request explicitly names UACP, a UACP lifecycle phase/skill, UACP state, or asks to change UACP governance/routing behavior. The router does not define Guardian, Heartgate, or review policy semantics; it only routes to the appropriate owner skill or canonical UACP docs.

## Lifecycle

```text
TRIAGE -> PROPOSE -> PLAN -> EXECUTE -> VERIFY -> RESOLVE
```

Use `uacp-state` only for governed state mutation and state-authority questions.

## Route

Reference: `../uacp-core/references/lifecycle-semantic-gates.md` captures the preferred lifecycle hardening pattern from the PROPOSE/PLAN/EXECUTE/VERIFY/RESOLVE gate work: PIV means Phase Intent Verification, VERIFY and RESOLVE are first-class gates, and governance-core phase hardening should use retrieval-led gap audit, pre-design council when semantics are subtle, implementation, validation, post-council, remediation, and follow-up PASS before commit/push.

- unclear scope, granularity, or admission -> `uacp-triage`
- proposal, authority, side effects, or viability -> `uacp-propose`
- execution graph, artifacts, or verification plan -> `uacp-plan`
- dispatch, Kanban, or worker execution -> `uacp-execute`
- adaptive verification, council, or evidence -> `uacp-verify`
- closure, lessons, memory, or skill updates -> `uacp-resolve`
- governed state mutation, state authority, or state consistency -> `uacp-state`
- admission reframing, surface classification (doc hygiene vs full lifecycle), or granularity/UACP-vs-non-UACP naming -> `uacp-triage`
- restructuring, refactoring, or repairing UACP skills (and its review/self-approval rules) -> `uacp-skills`

## Composition rule

The router does not contain phase execution procedures. Load the phase skill and let that skill own its checklist, adaptive gates, support files, handoff rules, and operator-facing presentation.

Operator channel output should be summary-first: conclusion, rational intent, decision/status, invariants, material risks, next action, and evidence pointer. Do not dump raw file lists or artifact inventories by default; raw details belong in evidence artifacts and are provided on request.

When using UACP phase labels such as `PASS`, `VERIFY PASS`, or `RESOLVE`, qualify exactly what passed. For documentation/design runs, say `documentation hygiene passed`, `first review slice passed`, or `draft reset resolved`; do not imply the underlying system/product has been implemented, accepted, or completed. If a run only reviews docs, explicitly state what is still not true: no runtime, no API, no integration, no canonical acceptance unless the lifecycle artifact actually grants that status.

For short context-dependent commands inside UACP work, bind the task to the strongest explicit conversational anchor before acting: platform reply/quote/thread context, then latest user message, then active UACP run/topic. Do not let cwd, dirty repositories, loaded skills, memory, or tool state redefine the run scope. If the anchored context does not clearly authorize a side-effectful action such as file edits, commits, state writes, gateway restarts, or protected artifact mutation, stop and ask.

Trustless ACP is pattern evidence only. UACP remains universal/adaptive and must not inherit Trustless-specific fixed gates, domains, worktree paths, proposal topology, reviewer lists, or verification sequences.

## Operator phase-return presentation

When reporting UACP phase progress or completion back to Telegram/Discord, return information rather than raw audit data. Use a conclusion-first operator summary: conclusion/status, what changed at meaning level, why it matters, decision rationale, invariants preserved, material risks, next action, and compact evidence pointer. Do not dump full file lists, raw diff stats, validation logs, council transcripts, or artifact inventories by default.

Raw evidence still belongs in UACP artifacts, commits, gate ledgers, and verification records. Mention that details are available on request. Include specific paths only when a path is itself the decision subject, a blocker/error depends on it, rollback requires it, or Mike explicitly asks for audit detail.

See `../uacp-core/references/operator-phase-return-presentation.md` for the reusable summary schema and suppression rules.

## Commit documentation discipline

When settling a large UACP working tree, especially after governance/runtime/doc-package work, do not simply commit the dirty set. First ensure there is a durable explanation surface in the repo and in the commit message:

- a decision/architecture or equivalent artifact that states what changed, why it changed, invariants, enforcement details, and verification commands;
- index/command-doc updates when gates, validators, fixtures, or operational workflows changed;
- inline test comments when an old verification lane needs new fixture setup because an invariant changed;
- a self-contained commit message with `What changed`, `Why`, `Invariants and details`, and `Verification` sections.

## Adaptive package backfill pattern

When auditing an in-flight UACP run, distinguish machine lifecycle envelopes from human-readable adaptive packages. If a medium/high consequence run has `proposals/{run_id}-proposal.yaml`, `plans/{run_id}-plan.yaml`, or scope/gate-selection YAML but lacks `proposals/{run_id}/` or `plans/{run_id}/` Markdown packages, call that out directly and backfill the package directories plus package-selection/plan-selection bridge artifacts before claiming strict lifecycle completeness.

## Lifecycle hardening pattern

For UACP self-patches, especially phase gates or truth/authority boundaries, use retrieval-led gap audit, pre-design council when appropriate, docs/config/validator/fixtures/skills patching, post-implementation adversarial audit, then commit/push. See `../uacp-core/references/lifecycle-semantic-gates.md` for the preferred hardening pattern.

For external audit remediation of lifecycle gates, do not stop at docs/config/offline validators. Check Heartgate runtime enforcement, root-confined artifact loading, runtime transition fixtures, PIV terminology/evidence semantics, and active skill-store sync.

When Mike asks for both Kimi Code and Codex to review UACP changes, launch them as bounded read-only external audits with explicit in-runtime Agent Council roles and command-level timeouts.

If Mike asks for a full review/audit, do **not** narrow the audit to the latest commit or immediate remediation unless explicitly instructed. Scope it to the full related change lineage and end-to-end lifecycle coherence across PROPOSE → PLAN → EXECUTE → VERIFY → RESOLVE, with devil's advocate, consistency historian, and dependency-readiness roles. After findings, patch all authoritative surfaces together — runtime, offline validator, config/schema, fixtures, active skill exports, state, and docs — and rerun adversarial follow-up until PASS.

When LEXA documentation authority is being reset or promoted, treat it as UACP lifecycle work if it affects source registry contracts, private/public retrieval boundaries, Nora/Cortex integration, or future runtime readiness. Do not frame it as informal Vault cleanup. After the reset, review draft docs in bounded slices, write per-slice checkpoints, preserve draft posture, then VERIFY/RESOLVE the review scope without implying LEXA itself is canonical or implementation-ready.

## Presentation and semantic package rule

Durable rule: YAML lifecycle files are machine envelopes; Markdown package files are semantic substrate for future human/agent understanding; Telegram/Discord receives a short operator summary. Do not fix missing semantic context only at the proposal level — update skills and validators/schema behavior so the failure cannot recur.

When council review finds gaps in semantic package enforcement, patch the systemic validator/skill contract, rerun focused council to PASS, and report conclusion -> patch -> rerun outcome without dumping raw inventories.

## Emergency stop

If UACP docs, config, or state disagree, stop. Route to `uacp-state` only for state mutation/authority/consistency; otherwise escalate to the operator or canonical UACP docs. If authority is unavailable, stop rather than inventing authority.
