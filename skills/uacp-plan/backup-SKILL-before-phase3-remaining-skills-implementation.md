---
name: uacp-plan
description: Use when converting an approved UACP proposal into a bounded plan with execution and verification structure.
---

# UACP Plan

## Purpose
This skill turns an approved proposal into an executable graph with explicit dependencies, review checkpoints, and verification targets.

## Read first
- `UACP_ROOT/docs/index.md`
- `UACP_ROOT/docs/lifecycle-reference.md`
- `UACP_ROOT/config/phase-transitions.yaml`
- `UACP_ROOT/config/review-routing.yaml`

## Rules
- Keep the plan bounded.
- For broad UACP doctrine/runtime/skill work, start with a whole phased plan before executing local patches. The plan should name phases, target files, acceptance checks, and deferred runtime work.
- When a proposal council has mixed or low-confidence outputs, do not treat that as a clean blocker by default. Weight validity explicitly, record usable findings in a synthesis artifact, then use PLAN to do direct source-surface inventory before EXECUTE. If proposal concerns identify existing doctrine/plans that may overlap with new work, make the first plan work package a surface inventory/gap map that marks prior artifacts as `reuse`, `patch`, `defer`, or `out_of_scope` before editing canonical docs/config.
- Split work only when the decomposition is real, then execute phase-by-phase: plan → patch → verify → continue.
- Preserve read/write boundaries for downstream skills.
- Do not treat Kanban as lifecycle state; use it for task decomposition and traceability.
- For long-running UACP hardening, prefer piece-by-piece tracks with autonomous local execution, verification, local commits, and UACP-private pushes when approved by current operator instruction; do not block every small local step on a new approval.
- Keep Hermes Agent upstream separate: local Hermes runtime patch consolidation may be committed locally, but do not push to upstream or open PRs unless explicitly requested.

## Typical outputs
- phased plan artifact in `plans/` for broad UACP doctrine/runtime/skill work
- plan artifact in `plans/` for ordinary bounded runs

## Updated doctrine alignment

Read additionally:

- `UACP_ROOT/docs/orchestration-model.md`
- `UACP_ROOT/config/evidence-clusters.yaml`

PLAN is where execution topology is selected.

A complete plan should identify:

- UACP authority and side-effect boundaries,
- phase-local granularity entry estimate and downstream projections,
- whether Agent Council is selected and at what mode/tier,
- Kanban graph shape when durable coordination is needed,
- selected profiles, agent runtimes, tool adapters, evidence services, and control substrates,
- profile/runtime separation: `role` = cognitive responsibility, `profile_id` = Hermes execution identity/configuration, `runtime_surface` = where work runs,
- runtime adapter ownership when plugins/hooks/config are involved: UACP-owned source under `UACP_ROOT/runtime-adapters/<runtime>/...` vs runtime-local binding path,
- version-control/branch/worktree SOP when the plan changes UACP artifacts or runtime adapter source,
- symlink/install/export binding and rollback steps when UACP-owned adapters are consumed by Hermes/OpenCode/Claude Code/Codex/etc.,
- whether delegated work should use native `delegate_task`, a Hermes Kanban/profile worker, a spawned `hermes --profile <name>` process, or an external runtime adapter,
- human involvement checkpoints,
- verification evidence and council synthesis artifact requirements.

For runtime-permission or containment plans, separate **mechanism evidence** from **execution authority**:

- An evidence checker (for example, a sandbox probe) proves that a mechanism is available; it is not itself permission to use standard shell/code paths.
- Name the actual execution seam that will consume the evidence and run inside containment.
- Keep standard tool paths fail-closed until the exact wrapped runtime surface is implemented and tested.
- Plan terminal/shell containment separately from `execute_code`; keep `execute_code` out of scope unless its backend-specific containment can be proven.
- Require positive and negative live probes plus Agent Council review before claiming any allow path is enabled.

For plans that cross lifecycle boundaries, include the target transition artifact and call out that `uacp_heartgate_check` is required before the next phase is accepted. Separate phase-local council review from Heartgate transition coherence: phase-local council checks the plan/work product; Heartgate checks lifecycle contract satisfaction, docs/config/state/runtime consistency, warning/deferred-item honesty, authority-plane integrity, and next-phase readiness. If Agent Council is selected for governance/runtime/artifact-management work, require retrieval-led review and a `uacp.council_synthesis` artifact with `inspected_paths`. If the plan includes canonical docs/config mutations, make `uacp_doc_write` / `uacp_config_write` the required write surfaces and explicitly check whether protected filesystem containment is available. If governed writers fail closed on containment, plan to record an EXECUTE checkpoint and route containment repair or explicit manual recovery; do not fall back to generic patch/terminal writes by default.

## Plan-council hardening pattern

When PLAN itself changes UACP governance, Agent Council protocol, Heartgate behavior, artifact schemas, validators, or runtime boundaries, do not treat a plan council as a ceremonial review. Use it to validate the actual plan artifacts and the prior transition artifact before PLAN→EXECUTE:

1. Create a surface inventory/gap map before planning exact patches. Include canonical docs/config/scripts, prior planning packages, skill surfaces, and mark each item `reuse`, `patch`, `defer`, or `out_of_scope`.
2. Dispatch retrieval-led PLAN council against the plan, gate selection, surface inventory, current state, and transition artifact. Require ground-truth file/path evidence.
3. If the council finds that an earlier transition artifact fails validator or Heartgate policy (for example invalid enum values or missing `heartgate_coherence`), patch that transition before creating PLAN→EXECUTE. Do not carry a known-invalid transition forward as “historical”.
4. Patch the plan itself with council remediations: rollback checkpoint, exact target surfaces, writer/tool availability checks, follow-through negative/regression verification cases, and whether skill alignment is in-scope or deferred.
5. For follow-through-gate or handled-negative-finding work, make the PLAN exact enough for EXECUTE: target config fields, validator checks, council recursion cap, evidence-cluster promotion/deferral, and TRIAGE-council trigger policy must be named before PLAN→EXECUTE.
6. Run artifact validation after the patches. Only then write PLAN→EXECUTE and run `uacp_heartgate_check`.

Pitfall: `python -m py_compile` may try to write bytecode inside read-only UACP containment. For read-only syntax checks, prefer `PYTHONDONTWRITEBYTECODE=1` with AST parsing, then run the validator separately.

Cognitive split:

- Agent Council decides/debates topology and synthesis when selected.
- Kanban records durable task graph and handoffs.
- Runtimes/tools/evidence services execute or observe bounded units.



## Phase-specific operating contract — PLAN

- **What this skill does:** turn approved proposal into execution topology, tasks, evidence clusters, rollback, tool surfaces, and council/Heartgate checkpoints.
- **Why it does it:** make EXECUTE deterministic enough that workers do not improvise governance.
- **How it does it:** read proposal/gates, decompose into bounded work units, declare tools/forbidden tools, define negative-result tests, run PLAN council, patch plan, write PLAN→EXECUTE transition.
- **Constraints:** do not implement beyond plan artifacts; do not hide unresolved council findings in plan text; do not select tools outside authority.
- **Reason / rational intent / decisions:** intent is execution design: decide who/what will act, with which tools, side effects, verification, rollback, and stop conditions.
- **Tools to use / not use:** use: read/search, delegate_task council, validators, optionally Kanban planning; avoid: live side effects, code/doc mutations outside planning artifacts.

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
