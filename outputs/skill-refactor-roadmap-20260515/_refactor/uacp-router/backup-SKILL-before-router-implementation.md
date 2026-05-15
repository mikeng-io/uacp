---
name: uacp
description: Use when working on UACP governance, lifecycle routing, state, review policy, or any UACP lifecycle skill.
version: 2.0.0
metadata:
  hermes:
    tags: [governance, lifecycle, multi-agent, review, kanban, control-plane]
    related_skills: [uacp-state]
---

# Universal Agent Control Plane

UACP is the single canonical doctrine for Hermes-native work: governance, implementation, execution, verification, and resolution are one system, not separate frameworks.

The canonical source of truth is the UACP artifact root and its docs/config/state files, not runtime memory or implied behavior.

## Drift guard

Do **not** let UACP collapse into governance-only language. If the skill layer starts treating UACP as merely a lifecycle gate, stop and restore the execution/implementation meaning before expanding the suite further.

UACP-derived skills should be extracted from the doctrine, not allowed to redefine it. If terminology becomes inconsistent, settle the glossary first and only then continue phase or skill expansion.

## Lifecycle

```text
TRIAGE -> PROPOSE -> PLAN -> EXECUTE -> VERIFY -> RESOLVE
```

Lifecycle phases are stable envelopes. Evidence clusters, councils, and verification depth are adaptive per context.

## Mike-specific UACP doctrine preferences

- For planning/design packages, split review artifacts by concern (ground truth, decisions, requirements, design, execution plan, verification/resolution) instead of compressing everything into one mega-document.
- Treat Agent Council as native orchestration, not review-only. For non-trivial implementation, EXECUTE should normally use Agent Council execution topology while Kanban remains the durable task substrate.
- Model granularity as phase-local and compositional: each phase records/re-evaluates entry estimate, exit actual, delta reason, and downstream projection; composite run granularity is recalculated from phase scores plus coupling/risk.
- Do not pre-decide or casually label a request as lightweight/standard/full outside the UACP lifecycle. Start the general lifecycle when Mike asks for UACP, let TRIAGE/PROPOSE/PLAN own granularity, and phrase any early score as an initial phase-local estimate only.

## Context rehydration before UACP execution

When resuming or executing the UACP rework / Agent-Council follow-through package, do not answer from the latest chat topic alone. First rehydrate the working context from UACP artifacts:

1. `docs/index.md`
2. `plans/uacp-agent-council-followthrough/00-index.md`
3. `plans/uacp-agent-council-followthrough/04-task-breakdown.md`
4. `outputs/uacp-current-status.yaml` when runtime/prototype status matters
5. current run artifacts under `state/runs/`, `verification/`, and `outputs/` when closing or resuming a run

Pitfall: if the conversation recently discussed delegate models, compression, gateway config, or model intelligence limits, do not mistake that meta-discussion for the active UACP workstream. Re-anchor on the planning package before deciding whether to use `delegate_task`, Kanban, external runtimes, or Agent Council. If Mike asks "what is actually missing?" or challenges why the agent is stuck, answer from the current artifacts first; do not open a new delegate just to rediscover root/status facts.

## Skill family

| Skill | Responsibility |
|---|---|
| `uacp-state` | Active governed state mutation, current pointers, run manifests |
| `uacp-triage` | Admission routing, scope calibration, granularity scoring |
| `uacp-propose` | Proposal artifacts, authority, side effects, viability |
| `uacp-plan` | Bounded execution graph and verification plan |
| `uacp-execute` | Dispatch through Hermes Kanban or delegated workers |
| `uacp-verify` | Adaptive verification and council review |
| `uacp-resolve` | Lessons, outputs, memory decisions, skill updates |
| `references/lifecycle-skill-contract.md` | Shared contract for the lifecycle skill family |
| `references/skills-validator-alignment.md` | Phased workflow for aligning lifecycle skills and artifact validators after canonical docs/config changes |
- `scripts/validate_uacp_artifacts.py` | Lightweight starter validator for UACP YAML/artifact sanity checks |
- `scripts/hermes_symlink_plugin_probe.py` | Non-destructive Hermes user-plugin symlink discovery probe for UACP-owned runtime adapters |
- `references/lcp-integration.md` | LCP design framework and UACP integration pattern |
- `references/guardian-neutral-kernel-adapter.md` | Guardian/Heartgate neutral-kernel + runtime-adapter implementation pattern |
- `references/round3-runtime-construction-lessons.md` | Session-proven implementation notes for neutral Guardian extraction, guarded artifact writes, and Kanban governance-context migration |
- `references/runtime-porting-version-control.md` | UACP-owned runtime adapter/plugin source, symlink/install bindings, Git/branch/worktree SOP, and Hermes local-patch reduction pattern |
- `references/runtime-porting-execution-runbook.md` | Execution runbook for dirty-root settlement, branch rebase/merge, Hermes symlink proof, and post-merge evidence |
- `references/runtime-porting-live-binding-cleanup.md` | Session-proven cleanup/doc-sync sequence after UACP-owned Hermes adapters are live-bound as user-plugin symlinks, including duplicate source removal, probe cleanup, and writer-surface gap handling |
- `references/operational-dashboard-and-live-proof.md` | Pattern for creating `outputs/uacp-operational-dashboard.yaml`, a safe live Guardian proof harness, and verification artifacts after runtime binding/cleanup checkpoints |
- `references/governed-canonical-writers.md` | Governed doc/config/state/artifact writer surface pattern, classification rules, containment checks, and verification harness cases
- `references/containment-design-direction-20260514.md` | Concrete containment design direction for enabling UACP-bound shell/code execution safely (read-only bind mount + sandbox working directory)
- `references/contained-shell-execution-seam-20260514.md` | Verified pattern for the actual contained-shell runtime seam, attestation lifecycle, and fail-closed boundaries
- `references/phase4b-resolve-lessons-20260514.md` | Resolve/closure lessons for contained-shell phases: Heartgate enum discipline, accepted council concerns as warnings/deferred items, and contained-shell workspace boundaries
- `references/phase5-kanban-completion-guard-20260514.md` | Phase 5 Kanban completion guard pattern: UACP-bound completion metadata/evidence contract, completion-time validation, tests, and Heartgate warning encoding
- `references/phase-transition-finalization-and-validation.md` | Final validation and phase-transition pattern after blocker patches: rerun retrieval-led council, validate/commit locally, Heartgate check, state/dashboard update, and non-action reporting
- `references/phase6-agent-council-operationalization-lessons-20260515.md` | Phase 6 Agent Council operationalization lessons: surface inventory, retrieval-led councils, transition repair, council/Heartgate artifact separation, and read-only validation pattern
- `references/heartgate-council-artifact-management.md` | Heartgate Council vs phase-local Agent Council distinction, transition-coherence artifact placement, required lenses, and writer safety pitfall
- `references/proposal-council-concerns-pattern-20260515.md` | Session-proven pattern for handling UACP proposal Agent Council CONCERNS before PROPOSE→PLAN: synthesize, patch proposal/gate artifacts, classify concerns, validate, then Heartgate
- `references/phase4-filesystem-containment-start-pattern-20260513.md` | Session-proven start pattern for Phase 4 containment: triage/propose/council/Heartgate/PLAN sequence, accepted-warning artifact shape, and EXECUTE-blocking constraints
- `references/phase4-filesystem-containment-start-pattern-20260513.md` | Session-proven start pattern for Phase 4 containment: triage/propose/council/Heartgate/PLAN sequence, accepted-warning artifact shape, and EXECUTE-blocking constraints

- `references/guardian-hook-audit-pattern.md` | Reusable methodology for auditing whether the Guardian `pre_tool_call` hook fires correctly across all execution paths (sequential, concurrent, subagent)
- `references/runtime-trust-boundary-correction-20260514.md` | Boundary correction: UACP governs declared runtime execution and revalidation, not arbitrary operator/host-side mutation outside the controlled runtime.

## Read first

Before using any UACP lifecycle skill, read:

- `UACP_ROOT/docs/index.md`
- `UACP_ROOT/docs/constitution.md`
- `UACP_ROOT/docs/lifecycle-reference.md`
- `UACP_ROOT/docs/runtime-enforcement.md`
- `UACP_ROOT/config/state.yaml`
- `UACP_ROOT/config/gate-selection.yaml`
- `UACP_ROOT/config/phase-transitions.yaml`
- `UACP_ROOT/config/review-routing.yaml`
- `UACP_ROOT/config/roots.yaml`
- `UACP_ROOT/references/branch-porting-ground-truthing.md`
- `references/agent-council-integration-lessons.md` when the work touches Agent Council, execution methodology, phase-local granularity, human involvement routing, or UACP/Agent Council/Kanban wiring
- `references/current-semi-auto-orchestration.md` when the work touches current-stage orchestration topology, delegate_task vs profile workers, Kanban/coordination boundaries, or future full-autonomy slots
- `references/delegate-task-model-selection.md` and `delegation-routing-policy/references/uacp-delegate-model-routing.md` when a UACP task will use `delegate_task` and the delegate model/provider choice matters
- `references/skills-validator-alignment.md` when canonical UACP docs/config changed and lifecycle skills or artifact validators may need alignment
- `references/governian-neutral-kernel-adapter.md` when work touches Guardian/Heartgate runtime activation, Hermes plugin integration, neutral kernel extraction, or Kanban governance-context propagation
- `references/containment-design-direction-20260514.md` when designing or implementing filesystem containment for UACP-bound shell/code execution
- `references/contained-shell-execution-seam-20260514.md` when implementing or verifying the governed contained-shell seam, attestation lifecycle, and standard shell/code fail-closed boundary
- `references/phase4b-resolve-lessons-20260514.md` when closing a contained-shell/runtime phase, especially if Agent Council returns accepted concerns or Heartgate rejects non-canonical status vocabulary
- `references/phase5-kanban-completion-guard-20260514.md` when work touches UACP-bound Kanban task completion, worker completion metadata/evidence, or the boundary between Kanban `done` and UACP lifecycle state
- `references/phase-transition-finalization-and-validation.md` when moving a UACP run toward VERIFY/RESOLVE after runtime/docs/config changes, especially after Agent Council blocker/concern patching, final validation, local commits, or `heartgate_coherence` transition evidence
- `references/phase6-agent-council-operationalization-lessons-20260515.md` when work touches Agent Council operationalization, retrieval-led council evidence, council synthesis schema, plan-council remediation, transition repair, or Phase 6-style surface inventory/gap mapping
- `references/heartgate-council-artifact-management.md` when work touches phase-local Agent Council vs Heartgate Council responsibilities, transition-coherence artifacts, `heartgate_coherence` fields, or Heartgate/artifact-validator alignment
- `references/runtime-trust-boundary-correction-20260514.md` before expanding containment or enforcement scope beyond the runtime/tool boundary, especially when discussing manual edits, user-side config changes, plugin enablement, or external runtimes without UACP integration-kanban-completion-guard-20260514.md` when work touches UACP-bound Kanban task completion, worker completion metadata/evidence, or the boundary between Kanban `done` and UACP lifecycle state
- `references/runtime-trust-boundary-correction-20260514.md` before expanding containment or enforcement scope beyond the runtime/tool boundary, especially when discussing manual edits, user-side config changes, plugin enablement, or external runtimes without UACP integration
- `references/round3-runtime-construction-lessons.md` when implementing the Guardian neutralization plan, adding guarded UACP writer tools, or migrating Kanban from UACP-specific context toward generic governance context
- `references/runtime-porting-version-control.md` when work touches runtime adapter/plugin ownership, UACP repository backup, branch/worktree SOP, symlink/install/export bindings, or the path to reduce Hermes Agent local patches
- `references/runtime-porting-execution-runbook.md` when executing the porting lane: settling dirty UACP roots, rebasing runtime-porting branches, proving Hermes symlink discovery, and recording post-merge evidence
- `references/runtime-porting-live-binding-cleanup.md` when live user-plugin symlink bindings are already active and the task is to reduce Hermes Agent duplicate source, remove temporary probes, or synchronize runtime binding/status docs
- `references/operational-dashboard-and-live-proof.md` when a runtime checkpoint needs a compact re-entry dashboard, safe live proof harness, or post-restart binding verification
- `references/governed-canonical-writers.md` when adding or using UACP Guardian writer tools for docs/config/state/artifacts, or when closing a manual doc/config mutation gap

## Core rules

- For major UACP doctrine/integration work, prefer a split planning package (index, ground truth, decisions, requirements, design, execution plan, verification/resolution) over one giant document.
- Treat Agent Council as a deliberative cognition layer, not review-only and not a Kanban substitute. Kanban is coordination memory; UACP is governance cognition; runtimes/tools are execution/evidence surfaces.
- Do not compress TRIAGE into PROPOSE for governance-core work. If a request touches lifecycle semantics, Agent Council, Heartgate/Guardian, protected state, artifact schemas, runtime enforcement, or authority-plane behavior, TRIAGE may need its own council and TRIAGE→PROPOSE transition before PROPOSE artifacts are adopted. Early proposal drafts are provisional until the TRIAGE gate accepts them.
- Model granularity as phase-local and compositional. Each phase should reassess entry estimate, exit actual, delta reason, and downstream projection; composite granularity is revised as evidence appears.
- Human involvement is selected by TRIAGE or later phase-local reassessment when authority, side effects, granularity, findings, or Guardian/Heartgate uncertainty require it.
- When Mike asks for a status summary or handoff, lead with *what has been achieved* and *what remains*; keep it short and concrete. Do not enumerate every file unless he asks for file-level detail.
- When Mike asks whether to continue, classify the next step by risk and reversibility before escalating:
  - reversible cleanup / verification / doc sync -> proceed without council
  - execution-enabling work, authority-boundary changes, or safety model changes -> pause and run a focused council first
- Do not hardcode model names.
- Do not use fixed numbered gates.
- Do not treat Hermes Kanban as UACP phase state.
- Do not mutate UACP state outside `uacp-state`.
- Do not keep deleted working notes in the active doc tree.
- Do not load suppressed docs by default; use tombstones and git history for legacy retrieval.
- Do not invent physical paths inside canonical UACP docs/config; use symbolic roots.
- Do not assume a skills branch has changed UACP until the live UACP canon is ground-truthed.
- If a skills refactor and UACP drift apart, treat UACP as the authority layer and port the skills to match it, not the other way around.
- For UACP self-modification or bootstrap/hardening work, distinguish lifecycle discipline from execution substrate. Follow the TRIAGE→PROPOSE→PLAN→EXECUTE→VERIFY→RESOLVE rhythm conceptually, but do not force the work through UACP's own protected runtime/write path when that creates recursion or a Guardian/containment bootstrap conflict. Use a general controlled implementation workflow (branch/worktree, normal repo patching, tests/validators, review/council as needed), then feed the result back into UACP as evidence once the enforcement substrate can consume it. Do not weaken Guardian to make self-modification convenient.
- After canonical UACP docs/config change, actively check and align lifecycle skills and lightweight artifact validators; do not stop at document updates if executable skills still encode stale workflow.
- For UACP-governed runtime plugins/adapters, prefer UACP-owned source under `UACP_ROOT/runtime-adapters/<runtime>/...` plus runtime-specific symlink/install/export binding. Do not let Hermes Agent's repository become the long-term source of UACP-owned plugin code; Hermes should consume the adapter through `HERMES_ROOT/plugins/` or another runtime binding when practical.

## Checkpoints

At the end of a phase or before a phase transition with material risk, distinguish two council jobs:

1. Run the appropriate adaptive evidence selection.
2. Dispatch phase-local Agent Council when the phase work itself needs review, execution critique, audit, or specialist validation.
3. Run or record Heartgate-level coherence when crossing the phase boundary: doctrine coherence, docs/config/state/runtime consistency, warning/deferred-item honesty, authority-plane integrity, and next-phase readiness.
4. For doctrine/runtime/artifact-management changes, do **retrieval-led council reasoning before claiming correctness**: dispatch role-diverse Agent Council to inspect ground-truth files/scripts/config, synthesize findings, then patch blockers/concerns. Do not rely only on main-session understanding.
5. Store Heartgate Council/coherence outputs as verification artifacts and reference them from transition artifacts via `heartgate_coherence.artifact_path`; do not treat them as lifecycle state or as a replacement for phase-local `council_synthesis_artifact`.
6. Escalate to a deeper council when runtime or domain diversity materially changes confidence.
7. Record both the phase-local council synthesis and the Heartgate/transition coherence outcome in run/state artifacts when used.

See `references/heartgate-council-artifact-management.md` for the exact artifact shape and required coherence lenses.

## Planning package shape

For substantial UACP design/integration work, do not compress every plan, requirement, decision, and design note into one giant document. Prefer a reviewable split package under `UACP_ROOT/plans/<topic>/` with an index and separate files for ground truth, decisions, requirements, design, execution plan, and verification/resolution. A single compiled reference packet is acceptable only as a secondary artifact, not the primary review surface.

Before claiming a planning package captures the discussion, actively verify it against the operator's explicit decisions and constraints. Use a checklist and patch any implicit or weakly stated items into explicit requirements before moving to execution.

## Planning artifact coverage check

When Mike asks to "write down all plans/requirements/design docs first" or otherwise pauses UACP execution for a planning artifact, do not just report line count or file creation. Before claiming the artifact captures the discussion, verify coverage against the explicit decisions and constraints from the conversation.

Minimum coverage checklist:

- UACP as the single canonical doctrine/source of truth, not a parallel agent-skills doctrine.
- Downstream skill/implementation extraction happens after UACP doctrine stabilizes.
- No canonical doc/config/code mutation before the planning artifact is reviewed or approved.
- Manual lifecycle drill is named when automation/enforcement is incomplete.
- Guardian neutrality is explicit: kernel + policy packs + runtime adapters.
- Agent Council is native multi-agent orchestration, not review-only.
- UACP granularity and council tier/orchestration depth are separate axes.
- Evidence cluster and domain registry merge direction is explicit.
- Deep-* wrappers are deprecated/compatibility-only if the UACP phases already cover their role.
- Symbolic path style is explicit: `UACP_ROOT/...` in docs/config, `$UACP_ROOT` only in shell, avoid `$$UACP_ROOT` unless an escaping layer is documented.
- Config-like paths should use global variable-like symbolic roots rather than repeated magic physical strings.
- Implementation code such as `guardian.py`, hooks, and runtime adapter scripts is not ported until doctrine stabilizes and an implementation phase is explicitly approved.
- UACP Guardian/Heartgate implementation is plugin-first: prefer `plugins/uacp_guardian/`, plugin tools/hooks, config, lifecycle skills, and UACP artifacts before proposing Hermes Agent core edits. Any core edit needs a documented missing extension seam and must follow `hermes-core-patching`.
- Guardian runtime activation must preserve a neutral-kernel + adapter boundary: policy evaluation in a Hermes-free kernel, Hermes-specific event/tool/session mapping in the plugin adapter, and generic core seams only when unavoidable. Agent-skills Guardian extraction work may be used as pattern evidence, but UACP docs/config/state remain authoritative.

If a point is only implied, patch the planning artifact to say it directly before reporting completion.





## Phase-specific coordination rule

Do not force every UACP phase through Kanban. EXECUTE is the phase most likely to require a coordination adapter. TRIAGE, PROPOSE, PLAN, VERIFY, and RESOLVE should use direct reasoning, scratch delegates, profile council, or external runtime adapters as needed. Use Kanban/coordination only when the phase needs durable multi-worker ownership, profile-specific workers, long-running/background execution, dependencies, reruns/regrouping, notifications/resume, audit trail, external runtime coordination, or full-autonomy command-bot execution. The phase controller/Insight layer chooses topology; Kanban only persists and dispatches selected units.

## Coordination adapter boundary

Do not let Hermes Kanban become hidden UACP doctrine. Kanban is the current durable coordination adapter for tasks/comments/artifacts, not the Agent Council protocol itself. Agent Council owns adaptive deliberation: roles, debate rounds, reruns, regrouping, escalation, synthesis, findings, and evidence obligations. Any Kanban-hosted debate requires an active coordinator/orchestrator loop; passive task completion is insufficient. Preserve a replaceable adapter contract so custom Kanban, issue trackers, or queues can replace Hermes Kanban later.

## Kanban binding

Use Hermes Kanban for durable task decomposition and traceability.
Do not use Kanban as the lifecycle state machine. UACP phase state lives in UACP artifacts/state; Kanban task IDs are references.

For UACP-bound Kanban tasks, task completion is itself a guarded evidence event. Require completion-time metadata/evidence before allowing a worker to mark a governed task done: `uacp_run_id`, `uacp_phase`, `authority_artifact`, `guardian_policy_version`, declared side effects, and non-empty evidence references. Validate this against the stored task governance context before the task state changes. Ordinary non-UACP Kanban completion must remain unaffected. Read `references/phase5-kanban-completion-guard-20260514.md` before editing completion semantics.

When PLAN/EXECUTE work becomes a durable graph, include the same execution spec shape used by the Kanban orchestrator: objective, allowed/forbidden files, verification, backup/rollback plan, execution topology/synchronization, and deliverable. Wire notifications to the relevant Telegram/Discord control surfaces after creating the graph so UACP does not depend on a synchronous chat session for progress tracking.

## Prototype/doc-drift sync

After UACP prototype state advances (for example: bootstrap closes, `uacp-state` starts governing mutation, lifecycle skills are created, or Kanban binding becomes active), actively check canonical docs/config for stale future-tense instructions. Common drift targets:

- `docs/index.md` open actions and decision log
- `docs/lifecycle-reference.md` deferred/creation-rule language
- `config/state.yaml` implementation status fields and examples
- `state/kanban.yaml` task status pointers

Do not patch these ad hoc from chat. Create or run a bounded UACP/Kanban doc-sync task through governed mutation, then verify YAML parses and commit UACP_ROOT if canonical docs/config changed.

## Use this registry when

- deciding which lifecycle skill to load
- checking the canonical read order
- updating UACP governance rules
- adding or changing lifecycle skills
- routing work into TRIAGE vs PROPOSE vs later phases

## LCP (Liaison Control Plane) — UACP-governed sibling

LCP is the public assistant governance layer. It is UACP-inspired but governs public-facing context and social memory, not agent execution.

- LCP implementation work enters UACP at TRIAGE
- LCP runtime is NOT UACP — it has its own simpler lifecycle (OBSERVE→EXTRACT→GUARD→MEMORIZE→RESPOND)
- Design doc: `~/.hermes/plans/lcp/LCP_REQUIREMENTS_AND_ARCHITECTURE.md`
- Artifacts: `~/.hermes/liaison/`
- Full skill: `devops/lcp`
- Enforcement tiers: `devops/lcp/references/enforcement-tiers.md`

Key relationship: UACP governs changes to agents/systems. LCP governs what a public assistant may observe, remember, share, and do on the operator's behalf.

## Containment and runtime trust boundary

Before designing or implementing UACP filesystem containment for shell/code execution, separate three layers:

1. **UACP layer:** declares lifecycle, authority, side effects, evidence obligations, and required runtime posture.
2. **Guardian/runtime-adapter layer:** enforces UACP rules inside the controlled runtime/tool path and verifies evidence supplied by the runtime.
3. **Host/runtime containment layer:** actually provides sandboxing, read-only mounts, isolated workdirs, separate users, containers, or equivalent controls.

Do **not** drift into making UACP police arbitrary operator or host-side behavior. UACP cannot and should not claim to prevent a human editing files in VS Code, changing local config, replacing a symlink, or running an external runtime without UACP integration enabled. Treat those as **out-of-band mutation**: untrusted until revalidated, not impossible.

When Mike challenges that a proposed hardline configuration is fuzzy, chaotic, or outside the UACP framework, pause and reframe the authority boundary before adding mechanisms. Prefer: "UACP declares required posture; Guardian verifies runtime evidence; host/runtime supplies containment; otherwise execution stays fail-closed."

If UACP-bound shell/code execution is being enabled, treat the new runtime seam as the real deliverable, not just the evidence checker. Keep `uacp_sandbox_check` evidence-only, add a separate contained execution surface, and preserve standard `terminal`/`execute_code` fail-closed until backend-specific containment is actually proven.

When using `uacp_contained_shell`, keep the execution workspace separate from `UACP_ROOT`. The contained shell is for commands that run in a sandbox workspace while UACP artifacts remain read-only; it is not the writer path for UACP-root mutation. If the workspace is `UACP_ROOT` or contains `UACP_ROOT`, containment should fail. For UACP artifact updates, use the governed writer tools instead.

When resolving a runtime phase after a council returns concerns, encode accepted concerns as `warnings` and `deferred_items`; keep invariant and cluster statuses within Heartgate's accepted vocabulary (typically `pass` for non-blocking accepted concerns). Do not invent status strings such as `pass_with_concerns` inside strict transition fields unless the transition config explicitly supports them.

When a phase-local Agent Council returns blockers, concerns, invariant failures, negative findings, or material warnings that are later marked handled, do not let the handling silently become a pass. Use a follow-through gate:

- `remediated`, `expanded`, or `justified` material findings require a handling artifact and context-selected follow-up Agent Council review before phase progression.
- `deferred`, `accepted_warning`, or `rejected_with_reason` findings require Heartgate visibility, owner, residual risk, and next-phase obligation; select follow-up council when severity/risk/routing warrants it.
- The follow-up council synthesis is evidence for Heartgate, not transition approval. Heartgate independently validates transition coherence and may still block.
- Cap default follow-up recursion at one rerun; if the follow-up council creates new blockers/material concerns, block or escalate instead of spawning endless councils.
- For Heartgate-compatible transition artifacts, carry warnings with `owner`, `residual_risk`, and `next_phase_acceptance`; carry deferred items with `id`, `cluster_id`, `owner`, `condition`, and `accepted_by`; add `accepted_exceptions` for intentionally accepted warning clusters.

TRIAGE sequencing rule for this class of work: do not stack TRIAGE and PROPOSE just because routing seems obvious. For high-granularity governance-core work, TRIAGE may need a TRIAGE-local Agent Council and TRIAGE→PROPOSE Heartgate/coherence artifact before PROPOSE artifacts are treated as adopted. If PROPOSE artifacts were drafted early, mark/adopt them only after the TRIAGE boundary is repaired; do not discard useful drafts unless their content is wrong.

EXECUTE containment rule for this class of work: canonical docs/config mutation must use governed writers. If generic patching is blocked, that is expected. If the governed writer itself fails closed because protected filesystem containment is unavailable, record an execution checkpoint and treat it as a runtime posture prerequisite; do not bypass with direct terminal writes unless Mike explicitly authorizes a manual recovery drill and the exception is recorded.

## Containment design direction

When reviewing or advancing UACP filesystem containment for shell/code execution:

1. Start from `references/containment-design-direction-20260514.md` for the current verified posture, open blockers, and the minimal-delta read-only bind mount + sandbox working directory approach.
2. When starting a new containment phase, read `references/phase4-filesystem-containment-start-pattern-20260513.md` before writing transition artifacts; it captures the triage → proposal → council → Heartgate → PLAN sequence and the structured warning/deferred-item shape Heartgate accepts.
3. The Guardian adapter already checks `event.filesystem_guard_verified`. The adapter must set it to `True` only after proving containment.
4. Do not weaken the default fail-closed block. Containment must be proven, not assumed.
5. Required evidence before claiming containment is live:
   - `verify_filesystem_containment()` implemented in adapter
   - `uacp_sandbox_check` tool registered (optional but recommended)
   - Live probe tests both allowed (contained workspace) and blocked (uncontained workspace) scenarios
   - Verification artifact recorded under `verification/`
   - `outputs/uacp-current-status.yaml` updated

## Kanban completion guard boundary

When UACP work modifies Hermes Kanban completion behavior, treat task completion as its own protected boundary. Creation-time and dispatch-time checks are not sufficient: a UACP-bound task must not transition to `done` unless completion carries required UACP evidence and Guardian metadata. Preserve ordinary non-UACP Kanban completion behavior, and keep Kanban as coordination memory rather than lifecycle state. Use `references/phase5-kanban-guard-start-pattern-20260514.md` for the proven triage/propose/plan sequence, council-validity weighting, exact surface inventory pattern, and required positive/negative/regression verification shape.

## Emergency stop

If docs, config, or state disagree, stop and resolve the canonical files first. Do not patch runtime behavior to paper over governance drift.


## Agent Council follow-through wiring

For any UACP work that invokes or consumes Agent Council findings, execute `references/agent-council-followthrough.md` before phase movement. Do not treat council output as prose advice: classify material findings, record handled-findings evidence, run any required focused follow-up council, and then run Heartgate on the transition artifact.

## Skill composition rule from Trustless ACP

When updating UACP lifecycle skills, do not put all SOPs into one shared file and do not inflate every phase `SKILL.md` into an unreadable mega-SOP. Use ACP-style class-level module composition: each lifecycle skill may be a directory with `SKILL.md` as the concise executable conductor plus local `references/`, scripts, schemas, prompts, and validators **only when the skill's explored intent justifies them**.

Trustless ACP is pattern evidence, not UACP authority. UACP is the superior universal abstraction: generic, unified, adaptive, and domain-neutral. Copy Trustless structural mechanics (owner skill, lifecycle trace, executable checklist, handoff invariant, local support files when needed), but do not copy Trustless-specific fixed gates, domains, proposal topology, worktree paths, or reviewer classifications into UACP canon.

If Mike asks how ACP composes skills, inspect or recall the actual skill directory structure before answering. Heavy Trustless ACP skills such as `implementation-plan`, `implementation-execute`, `verify`, `state`, and `review-principles` are multi-file skill packages; `agent-control-plane-propose` being single-file shows that single-file skills are valid when sufficient.

For UACP VERIFY specifically, preserve adaptive routing: determine the evidence clusters, risk surface, required expertise, council/review topology, and verification depth from current artifacts and authority boundaries. Do not hardcode Trustless's fixed verification gates as universal UACP doctrine.
