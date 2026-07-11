---
name: uacp-plan
description: Use when converting an approved UACP proposal into a bounded plan with
  execution and verification structure.
phase: plan
kind: lifecycle
authority_source: "engines/domain/{phase_graph,phase_transitions,gate_rules}.py (phase graph + stages + gate grammar, code-authoritative); config/uacp.toml [heartgate.*] (operator knobs); config/phase-transitions.yaml (LLM-read adaptive-gate doctrine + artifact schemas only)"
---
# UACP Plan

## Purpose
This skill turns an approved proposal into an executable graph with explicit dependencies, review checkpoints, and verification targets.

## PLAN_VALIDATION ledger contract

Before requesting PLAN→EXECUTE, this skill MUST append a `gate: PLAN_VALIDATION` record to the run's gate ledger via `uacp_gate_ledger_append`. Heartgate blocks the transition otherwise (see `engines/domain/gate_rules.py` — `plan_validation_gate_default()`).

The record must satisfy ALL of:
- `gate: PLAN_VALIDATION`
- `result: pass`
- `phase: plan` (matches `ledger_required_phase`)
- `checks:` a list containing every declared pv_id (`pv_1`..`pv_6`); extra unknown pv_ids are rejected
- explicit per-check pass evidence — EITHER each `checks[]` entry is a mapping `{id, result: pass[, evidence_path]}` OR the record carries a sibling `check_results: {pv_id: pass, ...}` mapping covering every pv_id

The six pv checks (codified in `engines/domain/gate_rules.py` — `PLAN_VALIDATION` pv-check list):
- `pv_1` scope_artifact_present_and_parses — `plans/{run_id}-scope.yaml` exists and parses with all required fields
- `pv_2` allowed_tools_registered — every tool named in scope.allowed_tools is registered in the Guardian tool registry
- `pv_3` write_paths_within_proposal_side_effects — `scope.write_paths` is a subset of the proposal's declared `side_effects.paths`
- `pv_4` blast_radius_human_approval_when_high — if blast_radius ∈ {high, critical} a human-involvement record exists in the triage artifact
- `pv_5` rollback_path_declared — a rollback_path is declared (even if `"none--write-only-artifact"`)
- `pv_6` cluster_artifacts_referenced — all required cluster artifacts from PROPOSE→PLAN are referenced in plan

Per-record DoS resistance: Heartgate scans ALL `PLAN_VALIDATION` pass records and accepts if any one satisfies the full contract; earlier-rejected records surface as warnings, not blockers.

## Read first
- `UACP_ROOT/config/phase-transitions.yaml` (adaptive-gate doctrine + artifact schemas; phase graph/stages/gate grammar now in `engines/domain/{phase_graph,phase_transitions,gate_rules}.py`; `plan_validation_gate` grammar in `engines/domain/gate_rules.py`)
- `UACP_ROOT/skills/uacp-core/scripts/engines/domain/gate_rules.py` — codified `plan_validation_gate_default()` and PLAN_VALIDATION pv-check list
- `UACP_ROOT/config/uacp.toml` (`[heartgate.*]` — operator-tunable knobs)
- `UACP_ROOT/config/review-routing.yaml` (council grammar/surfaces; operator knobs in `config/uacp.toml [review]`)
- `UACP_ROOT/skills/uacp-core/references/generative-gate-authoring.md` (the producer contract — how to author the frozen `uacp.check.*` checks per work_unit)

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
- for selected medium/high consequence work: adaptive PLAN package under `plans/{run_id}/`, with `plans/{run_id}-plan-selection.yaml` as the machine bridge

## Author the frozen verification checks (generative gate)
PLAN owns the **work_units**: for each one, author the check that would PROVE it, so VERIFY re-runs
it and "done" cannot be self-attested. Read
`UACP_ROOT/skills/uacp-core/references/generative-gate-authoring.md`; in brief — **comprehend** the
work_unit's intent and classify it (`from.class`/`from.basis`; the class→required-kind floor is
authoritative in `UACP_ROOT/config/verification-floor.yaml`), then **author** one `uacp.check.<kind>`
per work_unit via `uacp_entity_write` with `from.target` = the work_unit id (the `measured_by` edge):
the class-required kind — `field_equals` (set a value), `obligation_satisfied` (ensure an obligation),
`edge_exists` (required coverage), or `symbol_resolves` (wire a symbol — code plane, blocks until
wired). A work_unit you leave unchecked is blocked by the coverage gate; a too-weak kind for its
class is blocked by the floor.

## Adaptive PLAN package requirement

Read session lessons when package shape, operator presentation, or enforcement is in question:

- `references/adaptive-plan-package-enforcement-20260518.md` — adaptive PLAN package shape, validator/Heartgate enforcement pattern, and the narrow `self_patch_write_authority` bootstrap exception for UACP self-repair paths.
- `references/operator-summary-and-package-sufficiency-20260519.md` — operator-summary presentation and the correction that “light/standard” does not automatically mean YAML-only when why/how/invariants matter.
- `../uacp-execute/references/phase-intent-verification-execute-evidence-20260519.md` — PLAN-authored Phase Intent Verification contract pattern for EXECUTE evidence packages, neutral work-unit vocabulary, and validator fixture expectations.
- `references/piv-execution-evidence-contract.md` — PLAN-authored PIV/evidence contract pattern for EXECUTE observability and VERIFY handoff.

For medium/high consequence implementation tracks, governance changes, runtime boundaries, validator/Heartgate/Guardian work, multi-agent execution policy, public/private boundary work, identity-data handling, runtime prompt-context injection, or any PLAN that would otherwise compress execution topology into a single YAML artifact, PLAN must create a human-reviewable PLAN package in addition to machine lifecycle records.

This is UACP-native. OpenSpec and Trustless ACP are pattern evidence only. PLAN documentation selection is adaptive and context-driven: granularity informs rigor, but the execution topology determines which modules are needed.

Universal PLAN core concerns:

```text
work_breakdown
dependencies
authority_and_side_effects
tool_runtime_selection
artifact_write_surfaces
verification_strategy
rollback_recovery
council_review_topology
transition_readiness
```

Domain-selected modules may include runtime adapter plan, Guardian/Heartgate plan, schema/validator plan, documentation patch plan, migration plan, public/private boundary plan, multi-agent dispatch plan, Kanban coordination plan, containment plan, state-transition plan, or deployment/runbook plan.

A single PLAN YAML or scope YAML is not sufficient when the reviewer needs the why/how/invariants to safely execute or verify the task. Those YAML files are governance records, not the complete PLAN package. Treat `plans/{run_id}-plan.yaml` as a **machine lifecycle envelope** and `plans/{run_id}-plan-selection.yaml` as a **bridge/check artifact**. The PLAN substance lives in `plans/{run_id}/` whenever boundary, risk, rollback, verification, or runtime-context reasoning would otherwise be lost. “Light” or “standard” controls package size, not whether meaningful documentation may be skipped.

**Artifact audit pitfall:** when checking whether PLAN is complete, do not stop at `plans/{run_id}-plan.yaml`, `plans/{run_id}-scope.yaml`, or `PLAN_VALIDATION`. Explicitly check for the Markdown package directory `plans/{run_id}/`, its `00-index.md`, substantive Markdown modules covering the universal PLAN core concerns, and `plans/{run_id}-plan-selection.yaml`. If a run already advanced with only YAML envelopes, report that the Markdown PLAN package is missing and backfill it from authoritative proposal/plan/scope artifacts before claiming strict UACP completeness.

PLAN must not execute the work. PLAN may name target files, acceptance checks, and candidate function names as execution constraints, but actual code/config mutation belongs to EXECUTE.

N/A entries must be falsifiable. Each N/A must include reason, accepted_by, owner, residual_risk, revisit_phase, and an observable revisit_trigger.

## Goal-driven track

When the run is `track: goal-driven` (the goal-driven track — see `uacp-core/references/goal-driven-track.md`), the PLAN is **provisional and disposable**: the success criterion is the **goal** (held constant across a chain of forward runs), not a deliverable specifiable before EXECUTE. Plan accordingly:

- Do not over-specify a fixed acceptance artifact. Instead define the **checkpoint cadence**: what each EXECUTE probe attempts toward the goal, and what real evidence artifact each checkpoint must reference (Heartgate enforces that `evidence` is a governed-root-contained artifact — no prose self-attestation).
- The in-EXECUTE **checkpoint manifest** (`gate: CHECKPOINT` ledger entries) substitutes for the PIV/execution-evidence *artifact* at EXECUTE→VERIFY. The PIV *ledger* gate, authority/containment, and no-fabrication engines still fire. So a light PIV contract is still useful, but the checkpoint manifest — not a `executions/{run_id}` package — is the goal-driven EXECUTE evidence substrate.
- Carry the convergence budget (`proposals/{run_id}-convergence-budget.yaml`, `max_checkpoints`) into the plan's stop conditions: the plan must name what happens when the budget is near exhaustion (converge to a `keep`, or escalate) rather than looping.
- Plan rollback as **relaunch under the held goal**, not in-run rewind: a `roll_back`/`restart` verdict closes the run and starts a new forward run (`inherits_from` the prior, reusing triage/proposal/plan output). The phase graph is untouched.

Standard-track PLAN is unchanged.

## Updated doctrine alignment

Read additionally:

- `UACP_ROOT/skills/uacp-core/references/agent-council-followthrough.md` (council dispatch protocol, modes, tiers, retrieval-led rule, finding schema, mid-phase escalation)
- `UACP_ROOT/config/evidence-clusters.yaml`

PLAN is where execution topology is selected.

A complete plan should identify:

- UACP authority and side-effect boundaries,
- phase-local granularity entry estimate and downstream projections,
- the PLAN-authored PIV/evidence contract for EXECUTE: objectives, implementation units, checkpoint cadence, evidence obligations, semantic recovery obligations, drift/re-plan triggers, escalation conditions, and VERIFY handoff criteria,
- whether Agent Council is selected and at what mode/tier,
- Kanban graph shape when durable coordination is needed,
- selected profiles, agent runtimes, tool adapters, evidence services, and control substrates,
- profile/runtime separation: `role` = cognitive responsibility, `profile_id` = Hermes execution identity/configuration, `runtime_surface` = where work runs,
- runtime adapter ownership when plugins/hooks/config are involved: UACP-owned source under `UACP_ROOT/runtime-adapters/<runtime>/...` vs runtime-local binding path,
- version-control/branch/worktree SOP when the plan changes UACP artifacts or runtime adapter source (see `config/uacp.toml [version_control]`),
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

For plans that cross lifecycle boundaries, include the target transition artifact and call out that `uacp_heartgate_check` is required before the next phase is accepted. Separate phase-local council review from Heartgate transition coherence: phase-local council checks the plan/work product; Heartgate checks lifecycle contract satisfaction, docs/config/state/runtime consistency, warning/deferred-item honesty, authority-plane integrity, and next-phase readiness. If Agent Council is selected for governance/runtime/artifact-management work, require retrieval-led review and a `uacp.council_synthesis` artifact with `inspected_paths`. If the plan includes canonical docs/config mutations, make `uacp_doc_write` / `uacp_config_write` the required write surfaces (EXECUTE will use these — PLAN names them but does not call them) and explicitly check whether protected filesystem containment is available. If governed writers fail closed on containment, plan to record an EXECUTE checkpoint and route containment repair or explicit manual recovery; do not fall back to generic patch/terminal writes by default.

For UACP self-repair plans that must touch skill exports, validator scripts, or runtime-adapter source paths not reachable by existing governed writers, do **not** broaden `terminal`, `patch`, or generic shell into universal governed writers. Instead, require a narrow `self_patch_write_authority` block in the scope artifact with explicit reason, authority artifact, owner, rollback path, safe allowed prefixes, and verification obligations. See `references/adaptive-plan-package-enforcement-20260518.md`. Treat source-level Heartgate success, live `uacp_heartgate_check` success, and Guardian hard-interception proof as separate claims; after kernel/plugin patches, a runtime reload may be required before live tools reflect source behavior.

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
- **Why it does it:** make EXECUTE well-specified and bounded enough that workers never improvise governance.
- **How it does it:** read proposal/gates, decompose into bounded work units, declare tools/forbidden tools, define negative-result tests, run PLAN council, patch plan, write PLAN→EXECUTE transition.
- **Constraints:** do not implement beyond plan artifacts; do not hide unresolved council findings in plan text; do not select tools outside authority.
- **Reason / rational intent / decisions:** intent is execution design: decide who/what will act, with which tools, side effects, verification, rollback, and stop conditions.
- **Tools to use / not use:** use: read/search, delegate_task council, validators, optionally Kanban planning; avoid: live side effects, code/doc mutations outside planning artifacts.

This phase-specific contract complements `../uacp-core/references/agent-council-followthrough.md`; the shared reference supplies the common follow-through gate, while this section defines this phase's own job, intent, constraints, decisions, and tool boundary.

## Agent Council follow-through wiring

When this phase invokes or consumes Agent Council output, execute `../uacp-core/references/agent-council-followthrough.md` rather than treating council review as prose advice. In brief:

1. Select mode/tier/dispatch surface from UACP routing config and phase-local risk.
2. Dispatch retrieval-led roles when governance, runtime, artifact schema, Guardian/Heartgate, lifecycle, protected state, or skill behavior is involved.
3. Save `kind: uacp.council_synthesis` under `verification/` with `inspected_paths`, verdict, roles, findings, and evidence.
4. Extract all blockers, concerns, invariant failures, negative findings, and material warnings.
5. Do not advance the phase until every material finding is classified into the handled-findings matrix.
6. For `remediated`, `expanded`, or `justified` material findings, run one focused follow-up council unless a Heartgate-visible exception artifact is recorded.
7. Encode `handled_findings_chain`, `source_negative_findings_present`, and `followup_depth` in the transition artifact.
8. Run Heartgate after follow-through evidence exists; Agent Council synthesis is evidence, not transition approval.
9. Refuse next-phase adoption if the follow-through reference lists a refusal condition.


## Autonomous self-closing loop

When this skill invokes or consumes Agent Council during skill-library repair, governance/runtime work, lifecycle state movement, or any other phase-local closure task, it must close the loop without external prompting:

1. Save the pre-change checkpoint and backup before implementation or state movement.
2. Run deterministic validation before council review so council participants inspect concrete evidence rather than intentions.
3. Run a full-perspective Agent Council and, when runtime/model diversity is requested or materially useful, an independent Kimi Code / Kimi K2.6 audit.
4. Classify every blocker, concern, invariant failure, negative finding, and material warning into the handled-findings matrix.
5. Remediate concrete findings with the smallest sufficient patch, then rerun focused verification until the result is `PASS` / no material concerns or a refusal condition is reached.
6. Preserve the recursion cap from `../uacp-core/references/agent-council-followthrough.md`: at most one focused follow-up council for the same finding chain unless the operator explicitly authorizes deeper recursion; unresolved material findings after the cap block closure or require recorded accepted risk/deferment with owner and condition.
7. Record `handled_findings_chain`, `source_negative_findings_present`, `followup_depth`, inspected paths, commands, and residual risks in the relevant checkpoint or transition artifact.

During this skill-library refactor specifically, do **not** use UACP protected writers, Heartgate, MEMEX/BES, or `uacp-verify` as self-approval authority. Use normal file/git workflow, deterministic audits, Agent Council, and Kimi verification. A skill is considered repaired only after its implementation audit and end-of-implementation council/audit return `PASS` with no material concerns.

## mode_behavior

This skill consults `config/uacp.toml [autonomy]` to decide which actions
require operator confirmation per the active `state.current.uacp_mode`.

| mode | Behavior in PLAN | Operator confirmation |
|---|---|---|
| manual | every action requires operator confirmation | yes (all transitions) |
| semi_auto | autonomous within-phase actions; operator confirms transitions | yes (transitions only) |
| supervised_auto | Plan artifact, scope artifact, PLAN_VALIDATION ledger record, run-registry registration (under supervised_auto/full_auto), autonomous | only on escalation triggers (see below) |
| full_auto | as supervised_auto, plus auto-confirming non-irreversible decisions | only on `trigger_irreversible_write` or `escalation_triggered` |

**Escalates when**: scope.write_paths overlaps with another active run, or pv_4 (blast_radius high/critical) fires.

**Mechanism**: when an escalation trigger fires, this skill emits a
`uacp_escalation_event` record into `state/escalations/{run_id}.jsonl`
(severity ∈ {info, warn, block}). Operators poll the file. See `config/uacp.toml [autonomy.escalation_triggers]` for
the registered triggers.

## Phase Intent Verification contract

For selected non-trivial EXECUTE work, PLAN must author a Phase Intent Verification (PIV) contract before PLAN→EXECUTE. PIV means **Phase Intent Verification**, not implementation verification: the work units may be code, docs, config, generated artifacts, council dispatch, runtime probes, dry-runs, state updates, or handoffs.

Required machine artifact when selected:

- `plans/{run_id}-piv.yaml` with `kind: uacp.phase_intent_verification_contract`

Recommended semantic companion inside the PLAN package:

- `plans/{run_id}/piv-contract.md`

The PIV contract must define phase intent, neutral `work_units`, evidence obligations, checkpoint policy, intent-drift conditions, and next-phase handoff criteria. PLAN owns this contract so EXECUTE does not improvise what to record and VERIFY does not improvise what evidence is sufficient.

Write it with **`uacp_entity_write`** (`kind: uacp.phase_intent_verification_contract`) — the governed, registering manifest writer. **Each `work_unit` MUST carry `derives_from: [scope_item_id, …]`** referencing the keyed `scope.in_scope` ids from the PROPOSE proposal — this is the PROPOSE→PLAN coverage edge the graph gate enforces (a work_unit with no `derives_from` is an orphan; a scope_item nothing derives from is a dropped intent). This coverage edge is PLAN's fail-closed measure — the gate blocks on a dropped intent or an orphan work_unit rather than passing on the planner's assertion that coverage is complete.

A `work_unit` may also carry an optional **`required: false`** flag to mark it as non-blocking for the EXECUTE→VERIFY coverage gate (`forced_execute_evidence_blockers`). Omit it (or set `required: true`) for units that must be completed — these block the transition until EXECUTE writes an `after_work_unit` checkpoint for each. Mark stretch goals, conditional paths, or best-effort units as `required: false` so they neither block the transition nor imply dropped work.

## Operator phase-return presentation

Default Telegram/Discord phase returns MUST follow the operator summary layer from `UACP_ROOT/skills/uacp-core/references/operator-phase-return-presentation.md`. Return information, not raw data.

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

## Semantic package requirement

For any selected adaptive PLAN package, Markdown artifacts are mandatory semantic context, not optional human-facing decoration. The package must let a future agent reconstruct, one month later, without relying on chat history:

1. Why this execution topology was selected.
2. How the work will execute.
3. The intention, rationale, and decision behind tools, boundaries, verification, rollback, and review.

`plans/{run_id}-plan.yaml` and `plans/{run_id}-scope.yaml` remain machine lifecycle envelopes. They are not sufficient as the semantic substrate for STANDARD/FULL governance work. If a PLAN package is selected, `plans/{run_id}/` must contain Markdown documents with concrete headings and explanatory prose for work breakdown, dependencies, authority/side effects, tool/runtime selection, artifact write surfaces, verification strategy, rollback/recovery, council/review topology, and transition readiness. Placeholder Markdown or one-line stubs are blockers.

---

## Retrieval-led prior-art (Oracle)

**Always** call `uacp_oracle_query` before completing the plan to surface prior execution
patterns, scope decisions, and relevant council findings — retrieval has a **deterministic
floor** (#100): even with the semantic Oracle disabled (the default), it returns deterministic
corpus matches over `.uacp/lessons` + `.uacp/knowledge`.

```
uacp_oracle_query(phase=plan, project=<project-id>)
```

Results at `phase=plan` are **FULL** mode — run-state packets are `trust_class=authoritative`;
corpus and Honcho packets are `trust_class=normative` or `advisory`. Use retrieved packets to
inform work breakdown, risk assessment, and tool selection. Cite relevant `source` values in
the plan's rationale. If `uacp_oracle_query` returns no packets (an empty corpus), proceed without retrieval.

