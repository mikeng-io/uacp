---
name: uacp-execute
description: Use when dispatching bounded UACP work through Hermes Kanban or delegated workers.
---

# UACP Execute

## Purpose
This skill executes the approved plan by routing bounded work through Kanban or other delegated workers while keeping the active run traceable.

## Read first
- `UACP_ROOT/docs/index.md`
- `UACP_ROOT/docs/lifecycle-reference.md`
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

## Updated doctrine alignment

Read additionally:

- `UACP_ROOT/docs/orchestration-model.md`
- `UACP_ROOT/config/phase-transitions.yaml`
- `UACP_ROOT/config/review-routing.yaml`
- `HERMES_ROOT/skills/devops/uacp/references/current-semi-auto-orchestration.md` when deciding whether EXECUTE really needs Kanban/coordination or can stay synchronous

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



## Phase-specific operating contract — EXECUTE

- **What this skill does:** perform bounded implementation according to PLAN using selected workers/tools and record execution evidence.
- **Why it does it:** convert plan into controlled changes while preserving authority, provenance, rollback, and council follow-through.
- **How it does it:** load plan, create/dispatch bounded units, apply patches, run local tests, record checkpoints, run implementation council for non-trivial work, encode handled findings before EXECUTE→VERIFY.
- **Constraints:** do not expand scope without re-plan; do not use forbidden tools; do not bypass Guardian/Heartgate; do not treat worker self-report as verified.
- **Reason / rational intent / decisions:** intent is controlled mutation: decisions are patch boundaries, worker dispatch, evidence sufficiency, whether execution is complete enough for VERIFY.
- **Tools to use / not use:** use: patch/write_file/terminal tests/delegate_task/Kanban/external agents only if planned; avoid: production changes, secrets, unmanaged background writes, broad external runtimes without approval.

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
