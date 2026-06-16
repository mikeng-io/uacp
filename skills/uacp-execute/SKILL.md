---
name: uacp-execute
description: Use when dispatching bounded UACP work through Hermes Kanban or delegated
  workers.
phase: execute
allowed_tools:
- uacp_doc_write
- uacp_config_write
- uacp_state_write
- uacp_artifact_write
- uacp_gate_ledger_append
- uacp_contained_shell
- uacp_sandbox_check
- uacp_heartgate_check
- terminal
- execute_code
- uacp_run_registry_update
- uacp_escalation_event
forbidden_tools: []
phase_exit_invariants:
- artifact_glob: executions/{run_id}*
  required: true
- gate_ledger_entry: PLAN->EXECUTE
  required: true
authority_source: "engines/domain/{phase_graph,phase_transitions,gate_rules}.py (phase graph + stages + gate grammar, code-authoritative); config/uacp.toml [heartgate.*] (operator knobs); config/phase-transitions.yaml (LLM-read adaptive-gate doctrine + artifact schemas only)"
---
# UACP Execute

## Purpose
This skill executes the approved plan by routing bounded work through Kanban or other delegated workers while keeping the active run traceable.

## Read first
- `UACP_ROOT/docs/INDEX.md`
- `UACP_ROOT/docs/lifecycle/lifecycle-reference.md`
- `UACP_ROOT/config/state.yaml`

## Execution Posture (Critical)

**Full autonomy is the default for bounded, documented work.** When a plan or run manifest already defines the next gate — a PR to open, tests to run, a doc sync, a state update — execute it immediately without prompting. The only reasons to stop and ask:
- Genuinely ambiguous scope or a decision with no basis in the approved artifact
- Destructive or irreversible action not explicitly green-lit
- A bug or blocker that requires a judgment call

**Anti-pattern (avoid):** Pausing mid-execution to confirm routine steps ("should I run the tests now?", "do you want me to push?"). If the answer is obviously yes given the bounded plan, just do it.

**Manual-drill verification:** When UACP automation is partially broken and a manual drill uses a bypass path (for example a code-execution write path because Guardian blocks ordinary file tools without context fields), record that as a verification finding and keep the write boundary narrow. Do not present the bypass as normal enforcement; present it as manual-drill risk accepted for the bounded artifact.

**Governed writer containment blockers:** For UACP canonical docs/config mutation, generic `patch`, terminal writes, and ordinary file tools are not acceptable fallbacks after Guardian blocks them. First use the governed writers (`uacp_doc_write`, `uacp_config_write`, `uacp_state_write` as appropriate). If the governed writer itself fails closed because protected filesystem containment is unavailable, treat that as a runtime posture blocker: write an execution checkpoint, keep any prepared full-file payload as a temporary artifact, and either fix/verify containment first, defer the canonical mutation, or ask the operator for an explicit manual recovery drill. Do not loosen Guardian and do not silently bypass with direct terminal writes.

**Guardian-blocked shell/tool fallback:** If `exec.shell` is blocked by missing UACP context fields, or a newly registered UACP writer tool is misclassified in the current long-running session as `external.unknown_mutator`, prefer a narrow `execute_code` automation that invokes the UACP-owned guarded handler directly with full UACP context and writes only declared evidence/artifact paths. Record authority, side effects, and the fact that this was a manual-drill fallback in the artifact; verify YAML/git state afterward. Do not generalize this into a permanent bypass or present it as normal enforcement — schedule fresh-session/runtime reload verification for the exposed tool path.

**The "no permission" trap:** If a concern about gh/GitHub access was raised previously, always resolve it by checking `gh auth status` and `git remote -v` before declaring the action impossible. The gh CLI uses HTTPS tokens for PR creation — Phase 1 PRs (#4–#6) were created this way even when SSH deploy keys were not configured. Verify before you stop.

## Finding the Correct Python Runtime

Many of Mike's repos place a `.venv` at the repo root. This is the canonical runtime — not the hermes-agent venv and not the system python.

```
# Always check for a local .venv before using the default python
cd /path/to/repo && .venv/bin/python -m pytest ...

# Wrong: python3 or hermes-agent venv may lack project dependencies
# (e.g. temporalio, psycopg2, etc. are in .venv, not the system path)
```

This applies to any repo with: `pyproject.toml` + `.venv/` + a dependency on Temporal, PostgreSQL libs, or other project-specific packages.

## Rules
- Current-stage UACP is manual/semi-auto first: use Kanban/coordination primarily for non-trivial EXECUTE, not by default for TRIAGE/PROPOSE/PLAN/VERIFY/RESOLVE.
- Treat Kanban as the coordination adapter/work substrate, not the phase engine, doctrine, or Agent Council substrate.
- A Kanban task is a bounded work unit inside a phase, usually EXECUTE; it is not automatically equal to a UACP lifecycle phase.
- Keep writes inside the declared execution boundary.
- Record task IDs and completion summaries back into run state.
- Do not broaden scope during execution.
- When an approved plan or source-of-truth doc already names routine execution gates (review, fix, PR, CI response, smoke, doc sync), dispatch them into Kanban proactively instead of keeping them as synchronous chat prompts. Telegram/chat should be control + escalation, while Kanban carries durable task state, dependencies, backup plans, verification specs, and fan-out/fan-in topology.
- If execution produces or updates canonical docs/config, route those mutations through `uacp_doc_write` or `uacp_config_write` rather than generic file writes.
- If execution reaches a phase boundary, prepare a transition artifact and run `uacp_heartgate_check` before the next phase is accepted. For non-trivial governance/runtime execution, also prepare or reference Heartgate coherence evidence (`heartgate_coherence`) separately from any phase-local implementation review council.
- Ask the operator only for genuinely ambiguous scope, destructive/irreversible actions, or decisions not covered by the approved plan.

## Typical outputs
- execution artifacts in `executions/`
- Kanban task references in state

## Code-execution checkpoint pattern

When EXECUTE produces a local code patch in a project worktree, do not stop at "tests passed" or an external worker's self-report. Before reporting progress:

1. Verify the worktree state directly with `git status --short --branch`, `git log --oneline -1`, and a focused diff/stat.
2. Run targeted tests from the project runtime (`uv run`, local `.venv`, etc.) and record exact commands/results.
3. Commit only if the bounded patch and tests are coherent; do not push/PR unless the approved plan or operator explicitly authorizes it.
4. Write an execution checkpoint artifact under `executions/` that records: worktree path, branch, commit, files/areas touched, tests, non-actions, residual risks, and any deferred out-of-band artifact disposition.
5. Preserve live-side-effect boundaries explicitly: no production DB mutation, no schedule mutation, no public post, no push, unless separately authorized.

If an external coding runtime returns success but produces no output or no diff, treat that as no verified work. Inspect git state and either rerun with a narrower prompt or continue manually; never report success from the worker's exit code alone.

## Goal-driven track — the checkpoint loop

When the run is `track: goal-driven` (the goal-driven track — see `uacp-core/references/goal-driven-track.md`), EXECUTE is not a single bounded implementation pass — it is an iterative loop of **disposable probes** toward the persistent goal (`goal_id`). Each iteration is recorded as a governed checkpoint; nothing is committed as "the result" until a probe *satisfies* the goal. This loop is what `uacp-plan`'s standard PIV/execution package is replaced by here.

**1. Write each checkpoint to the gate ledger.** After each probe, append a `gate: CHECKPOINT` record via `uacp_gate_ledger_append`. The payload is a `CheckpointEntry` (`engines/domain/checkpoint.py`, `extra="forbid"` — extra fields BLOCK):

```yaml
checkpoint_id: "<unique within run>"
run_id: "<this run>"
goal_id: "<the held goal>"
phase: execute
what_changed: "what this probe produced/changed"
why: "why this probe, toward the goal"
evidence: "executions/{run_id}/cp-3-hero.png"   # a REAL governed-root artifact — existence is enforced; prose is rejected
verdict: keep | roll_back | restart
invariant: "the goal invariant this probe is judged against"
rolled_back_to: "<checkpoint_id>"               # only when verdict=roll_back
```

The `evidence` must reference a real, governed-root-contained artifact. Heartgate runs the same no-self-attestation / no-fabrication check it uses for all gate-ledger evidence — a missing path, an escaping path, or a prose sentence is a BLOCK.

**2. Decide the verdict honestly.**
- `keep` — the probe advances the goal; carry it forward. (The *final* manifest entry must be `keep` or EXECUTE→VERIFY blocks — a dangling `roll_back`/`restart` means nothing converged.)
- `roll_back` — discard this probe; relaunch from a prior checkpoint (`rolled_back_to`).
- `restart` — discard and relaunch the run under the held goal.

**3. Roll-back / restart is a NEW forward run, not an in-run rewind (P2=b).** There are no phase-graph back-edges. To roll back: close this run, then `uacp_state_write` init a new run with the **same `goal_id`** and `inherits_from: <this run_id>`. The new run inherits the prior triage/proposal/plan output references automatically; its EXECUTE continues the same checkpoint chain.

**4. Respect the convergence budget.** The cap (`proposals/{run_id}-convergence-budget.yaml` → `max_checkpoints`) counts `CHECKPOINT` entries across the goal's **whole run-chain** (every run sharing the `goal_id`), not just this run. Exactly `max_checkpoints` passes; `max_checkpoints + 1` BLOCKS at EXECUTE→VERIFY. As the count approaches the cap, converge to a `keep` or escalate via `uacp_escalation_event` — do not keep probing.

**5. EXECUTE→VERIFY requires a coherent manifest.** Before requesting the transition, the checkpoint manifest must be: non-empty, every entry valid (`CheckpointEntry`), every `evidence` ref real, total count ≤ cap, and the final verdict `keep`. This coherent manifest is what substitutes for the PIV/execution-evidence *artifact* — but the PIV *ledger* gate, authority/containment, and no-fabrication engines still fire normally.

Standard-track EXECUTE (PIV contract + `executions/{run_id}` package) is unchanged — the above applies only when `track: goal-driven`.

## Updated doctrine alignment

Read additionally:

- `UACP_ROOT/docs/lifecycle/orchestration-model.md`
- `UACP_ROOT/config/phase-transitions.yaml` (adaptive-gate doctrine + artifact schemas; phase graph/stages/gate grammar now in `engines/domain/{phase_graph,phase_transitions,gate_rules}.py`)
- `UACP_ROOT/skills/uacp-core/scripts/engines/domain/checkpoint.py` — codified `CheckpointEntry` schema (goal-driven checkpoint manifest)
- `UACP_ROOT/skills/uacp-core/scripts/engines/domain/budget.py` — codified `ConvergenceBudget` schema (goal-driven cap)
- `UACP_ROOT/skills/uacp-core/scripts/engines/domain/phase_graph.py` — codified valid transitions (`LIFECYCLE_GRAPH`)
- `UACP_ROOT/skills/uacp-core/scripts/engines/domain/gate_rules.py` — codified gate/rule grammar (piv_rule, heartgate_coherence, run_registry)
- `UACP_ROOT/config/uacp.toml` (`[heartgate.*]` — operator-tunable coherence thresholds and enforcement mode)
- `UACP_ROOT/config/review-routing.yaml` (council grammar/surfaces; operator knobs in `config/uacp.toml [review]`)
- `references/current-semi-auto-orchestration.md` when deciding whether EXECUTE really needs Kanban/coordination or can stay synchronous
- `references/self-patch-write-authority-gap-20260518.md` when EXECUTE touches UACP skills, validators, Heartgate/Guardian runtime adapters, or other self-patch governance surfaces
- `references/phase-intent-verification-execute-evidence.md` when EXECUTE needs PIV-backed semantic evidence and VERIFY handoff
- `references/phase-intent-verification-execute-evidence-20260519.md` when EXECUTE needs PIV-backed evidence, semantic execution packages, checkpoint validators, or expected-fail fixtures
- `references/piv-execution-evidence-contract.md` when EXECUTE needs to record semantic evidence/checkpoints against a PLAN-authored PIV contract rather than ad hoc YAML-only summaries

EXECUTE follows the topology selected in PLAN:

- UACP gates authority, side effects, phase state, and human involvement.
- Agent Council supplies deliberative orchestration for non-trivial implementation when selected.
- Do not treat docs/config/validator updates as fully wired execution. For UACP governance, lifecycle, Heartgate/Guardian, artifact-schema, or runtime-enforcement changes, EXECUTE must either implement the skill/SOP wiring itself or explicitly record that orchestration wiring remains incomplete.
- When Agent Council is selected for EXECUTE, the skill must state the operational chain: select council mode/tier, dispatch retrieval-led roles, write `kind: uacp.council_synthesis` under `verification/`, classify material findings, require handled-findings evidence, run at most one follow-up council when required, then feed `handled_findings_chain` into Heartgate before phase progression.
- Kanban is coordination memory, not governance or deliberation.
- Runtimes/tool adapters/evidence services perform bounded work only within declared scope.

During execution, re-evaluate phase-local granularity at entry and exit.

Mid-phase escalation rule: if granularity escalates mid-phase:

- apply higher council tier to pending work when no protected action is in flight,
- pause before next irreversible/external side effect when stronger review is required,
- block phase exit on unresolved HIGH/CRITICAL findings unless resolved, accepted, or re-planned.

Completion should produce execution evidence and, when council was used, a council synthesis artifact.

## PLAN-authored PIV / execution evidence contract

For non-trivial/governed EXECUTE work, do not treat `executions/{run_id}*.yaml` as sufficient just because a checkpoint exists. First locate the PLAN-authored PIV/evidence contract (for example `plans/{run_id}-piv.yaml` and/or `plans/{run_id}/piv-contract.md`). EXECUTE records against that contract: implementation units completed, decisions made, assumptions changed, drift/deviations, tests/probes run, invariants preserved, handled findings, and VERIFY handoff evidence.

If PLAN did not define a PIV/evidence contract but the work is medium/high consequence, governance/runtime/protected-state, public/private boundary, multi-agent, validator/Guardian/Heartgate, or profile/plugin work, record the gap and either backfill the contract before continuing or explicitly block/re-plan. Do not silently invent a one-off checkpoint schema and call it complete.

A semantic execution package under `executions/{run_id}/` should explain why choices were made and how evidence maps to the plan/PIV; YAML remains the machine envelope. Avoid raw file lists as the primary record unless paired with rationale, decision, invariant, and evidence mapping.



## Phase-specific operating contract — EXECUTE

- **What this skill does:** perform bounded implementation according to PLAN using selected workers/tools and record execution evidence.
- **Why it does it:** convert plan into controlled changes while preserving authority, provenance, rollback, and council follow-through.
- **How it does it:** load plan, create/dispatch bounded units, apply patches, run local tests, record checkpoints, run implementation council for non-trivial work, encode handled findings before EXECUTE→VERIFY.
- **Constraints:** do not expand scope without re-plan; do not use forbidden tools; do not bypass Guardian/Heartgate; do not treat worker self-report as verified.
- **Reason / rational intent / decisions:** intent is controlled mutation: decisions are patch boundaries, worker dispatch, evidence sufficiency, whether execution is complete enough for VERIFY.
- **Tools to use / not use:** use: patch/write_file/terminal tests/delegate_task/Kanban/external agents only if planned; avoid: production changes, secrets, unmanaged background writes, broad external runtimes without approval.

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

## mode_behavior (Phase 4.3 stub)

This skill consults `config/uacp.toml [autonomy]` to decide which actions
require operator confirmation per the active `state.current.uacp_mode`.

| mode | Behavior in EXECUTE | Operator confirmation |
|---|---|---|
| manual | every action requires operator confirmation | yes (all transitions) |
| semi_auto | autonomous within-phase actions; operator confirms transitions | yes (transitions only) |
| supervised_auto | Bounded implementation work within scope.write_paths; per-cluster sub-step heartgate checks, autonomous | only on escalation triggers (see below) |
| full_auto | as supervised_auto, plus auto-confirming non-irreversible decisions | only on `trigger_irreversible_write` or `escalation_triggered` |

**Escalates when**: scope.write_paths needs widening, or irreversible_write triggers, or council material finding.

**Mechanism**: when an escalation trigger fires, this skill emits a
`uacp_escalation_event` record into `state/escalations/{run_id}.jsonl`
(severity ∈ {info, warn, block}). Operators poll the file (push-notify
is Phase 5). See `config/uacp.toml [autonomy.escalation_triggers]` for
the registered triggers.

## Phase Intent Verification (PIV) execution evidence

Reference: `references/phase-intent-verification.md` captures the session-derived neutral PIV vocabulary and PLAN→EXECUTE→VERIFY ownership model.

EXECUTE must execute against the PLAN-authored PIV contract when one exists.

EXECUTE must:

1. Load the PIV contract and identify the active `work_unit_id`.
2. Write `kind: uacp.execution_checkpoint` artifacts that reference `piv_contract`, record work performed, decisions, evidence obligation results, intent drift, invariants, and next-phase readiness.
3. Maintain a semantic execution package under `executions/{run_id}/` with `00-index.md`, work narrative, decision log, evidence map, intent drift/deviation record, and VERIFY handoff when the adaptive execute evidence gate applies.
4. Treat `next_phase_readiness: ready` as invalid when required PIV evidence obligations are missing.
5. If intent drift is discovered, record disposition (`accepted`, `replanned`, `blocked`, or `deferred`) and escalate/re-plan when the PIV contract requires it.

YAML-only execution checkpoints are insufficient for selected medium/high consequence work because they do not preserve why/how/decision/evidence meaning for future agents.

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

