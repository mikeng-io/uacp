---
name: uacp-resolve
description: Use when closing a UACP run, extracting lessons, and deciding memory
  or skill updates.
phase: resolve
kind: lifecycle
authority_source: "engines/domain/{phase_graph,phase_transitions,gate_rules}.py (phase graph + stages + gate grammar, code-authoritative); config/uacp.toml [heartgate.*] (operator knobs); config/phase-transitions.yaml (LLM-read adaptive-gate doctrine + artifact schemas only)"
---
# UACP Resolve

## Purpose
This skill closes the run, captures lessons, decides what belongs in memory, and determines whether a new skill or doc update is warranted.

## Read first
- `UACP_ROOT/config/uacp.toml [memory]` (operational boundaries; schema: `docs/reference/learning-artifact-schema.md`)

## Rules
- Keep the learning artifact compact.
- Separate useful lessons from one-off noise.
- Do not put high-volume gate-learning into personal memory.
- Persist lessons to `.uacp/lessons/<id>.md` and distilled knowledge to `.uacp/knowledge/<id>.md` **through the Oracle corpus-write surface** (`engines.oracle.corpus_writer.persist_lesson` / `persist_knowledge`), which serializes the OKF doc and routes it through the governed artifact writer. The Oracle is the single owner of corpus read and write — do not call `uacp_artifact_write` or touch `.uacp/lessons/` / `.uacp/knowledge/` directly.

## Typical outputs
- resolutions/
- `.uacp/lessons/` (OKF lesson corpus)
- `.uacp/knowledge/` (distilled knowledge items)
- lesson artifact or run summary

## Updated doctrine alignment

Read additionally:

- `UACP_ROOT/skills/uacp-core/references/agent-council-followthrough.md` (council dispatch protocol, modes, tiers, retrieval-led rule, finding schema, mid-phase escalation)
- `UACP_ROOT/config/phase-transitions.yaml` (adaptive-gate doctrine + artifact schemas; phase graph/stages/gate grammar now in `engines/domain/{phase_graph,phase_transitions,gate_rules}.py`)
- `UACP_ROOT/skills/uacp-core/scripts/engines/domain/phase_graph.py` — codified valid transitions (`LIFECYCLE_GRAPH`)

RESOLVE closes the run only after verification evidence, council findings, accepted risks, and human involvement requirements are settled.

Before marking a run resolved, ensure any phase transition that led here was validated by `uacp_heartgate_check`, and ensure canonical docs/config deltas used `uacp_doc_write` / `uacp_config_write` where applicable.

For UACP governance, lifecycle, Heartgate/Guardian, artifact-schema, runtime-enforcement, or Agent Council changes, RESOLVE must also check skill-level orchestration wiring. Do not close as clean pass if the change only updated docs/config/validator while the relevant lifecycle skills do not explain who dispatches councils, what synthesis artifact is produced, how handled negative findings are encoded, and how Heartgate gates progression. If any council finding remains material, require a handled-findings chain or record residual risk/owner/next-phase obligation before closure.

Resolution should record:

- final phase-local and composite granularity,
- remaining accepted risks and owners,
- lessons written to `.uacp/lessons/` (OKF, BES-scored),
- whether UACP skills or validators need updates,
- whether any skill updates happened outside the UACP repo boundary (for example Hermes skill storage),
- whether downstream agent-skills extraction should happen now or remain deferred.
- whether any operationally relevant skill changes live outside the UACP repo commit boundary. If skill alignment was inspected via `skill_view`, state that clearly as an external skill-store dependency rather than implying the change is backed by the UACP git commit.

## Goal-driven track

When the run is `track: goal-driven` (the goal-driven track — see `uacp-core/references/goal-driven-track.md`), RESOLVE closes the **goal**, not just the run. A goal-driven run is realized as a *chain of forward runs* held together by a shared `goal_id` (each rollback/restart was a new run with `inherits_from` the prior); closure happens once a checkpoint is **promoted to result** by satisfying the goal.

RESOLVE must:

- record the **converged checkpoint** (the final `keep`, goal-bound) as the result, and the **run-chain** that reached it (the `inherits_from` links and the `goal_id`), so a future agent can reconstruct how the goal was satisfied across restarts;
- **release the goal anchor** — deregister the goal's runs from the run registry (`uacp_run_registry_update`) so the held `goal_id` no longer pins live runs;
- carry the disposable-probe history honestly: the discarded `roll_back`/`restart` checkpoints are part of the record, not failures to hide.

The VERIFY→RESOLVE closure gate already enforced manifest coherence + goal-binding of the promoted checkpoint; RESOLVE consumes that judgment and does not re-open it. The standard closure invariants (computed engines, Heartgate coherence, no-fabrication) fire unchanged. Standard-track RESOLVE is unchanged.

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

Do not store high-volume gate outcomes in personal memory. Use durable UACP artifacts/knowledge.



## Phase-specific operating contract — RESOLVE

- **What this skill does:** close the run, archive outputs, record lessons, and decide memory/skill/doc follow-up.
- **Why it does it:** prevent unresolved risk or skill drift from being mislabeled complete.
- **How it does it:** load final transitions, verify Heartgate pass/warn, ensure all council findings have handled chain or accepted residual risk, write resolution artifact, update skills/memory only for durable lessons.
- **Constraints:** do not close if Heartgate blocks, follow-through is incomplete, or artifacts disagree; do not save stale task progress to memory.
- **Reason / rational intent / decisions:** intent is durable closure: decisions are resolved scope, residual risks, future work, skill/memory updates, and non-actions.
- **Tools to use / not use:** use: read/validator/session artifacts, skill_manage for durable skill fixes, memory only for stable facts, uacp_heartgate_check when boundary state is touched; avoid: implementation changes, broad memory dumps, public/external actions.

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

| mode | Behavior in RESOLVE | Operator confirmation |
|---|---|---|
| manual | every action requires operator confirmation | yes (all transitions) |
| semi_auto | autonomous within-phase actions; operator confirms transitions | yes (transitions only) |
| supervised_auto | Outputs, structured lessons artifact with ledger_citations, run-registry deregistration, autonomous | only on escalation triggers (see below) |
| full_auto | as supervised_auto, plus auto-confirming non-irreversible decisions | only on `trigger_irreversible_write` or `escalation_triggered` |

**Escalates when**: lessons artifact incomplete or unexpected residual blockers.

**Mechanism**: when an escalation trigger fires, this skill emits a
`uacp_escalation_event` record into `state/escalations/{run_id}.jsonl`
(severity ∈ {info, warn, block}). Operators poll the file (push-notify
is Phase 5). See `config/uacp.toml [autonomy.escalation_triggers]` for
the registered triggers.



## Adaptive RESOLVE closure package

Reference: `../uacp-core/references/lifecycle-semantic-gates.md` summarizes the lifecycle semantic-gate pattern and the user correction that RESOLVE must be hardened before claiming lifecycle completion.

For governed/non-trivial RESOLVE work, RESOLVE must produce validator-backed closure evidence instead of only a terminal summary or loose output file.

Required machine artifacts when selected:

- `resolutions/{run_id}-resolve-selection.yaml` with `kind: uacp.resolve_package`
- `resolutions/{run_id}-closure.yaml` with `kind: uacp.resolve_closure`

Required semantic package:

- `resolutions/{run_id}/00-index.md`
- `closure-summary.md`
- `final-decision.md`
- `residual-risks.md`
- `lessons-and-dispositions.md`
- `state-and-memory-disposition.md`
- `operator-handoff.md`

RESOLVE consumes `verification/{run_id}-resolve-readiness.yaml`. It must block if readiness is missing, stale, unbound, not ready, or contains open blockers. RESOLVE does not redo VERIFY; it preserves VERIFY's unresolved residual risks/deferred items and records final closure decisions.

Lesson dispositions must be explicit: `memory`, `skill`, `docs`, `knowledge`, or `no_action`, with rationale, owner, durability, risk_if_persisted, and accepted_by. Do not save memory/skill/doc changes implicitly just because a run closed.

## VERIFY evidence intake before RESOLVE

Before RESOLVE accepts a governed/non-trivial run, read `verification/{run_id}-resolve-readiness.yaml` when present. RESOLVE must not close a run if VERIFY reports open blockers, unowned assumptions/deferred items, failed Heartgate coherence, missing required PIV assessment, or self-approval guard failure. RESOLVE consumes VERIFY's evidence judgment; it does not convert unresolved VERIFY risks into closure prose.

## Lesson corpus + distillation

Read `references/lesson-corpus-extraction.md` when extracting lessons at RESOLVE. This reference contains the full operational procedure; this section is a pointer and summary.

After the gate artifact `resolutions/{run_id}-lessons.yaml` exists, RESOLVE performs three corpus steps:

**Step 1 — Extract to OKF.** Each durable lesson in the gate artifact is persisted to `.uacp/lessons/<id>.md` (OKF frontmatter + body) through the Oracle corpus-write surface (`engines.oracle.corpus_writer.persist_lesson`), which serializes the `Lesson` and routes it through the governed artifact writer. The `id` is kebab-case by lesson *topic* (not run/date), so re-extraction overwrites stably.

**Step 2 — Recompute BES.** After extraction, `engines.domain.corpus.recompute_bes` is called for every project lesson, using the resolved-run manifests under `.uacp/state/runs/` as eligibility evidence (manifests are read by the state engine and handed to RESOLVE — they are not Oracle inputs). Updated lessons are re-persisted via `engines.oracle.corpus_writer.persist_lesson`.

**Step 3 — Promote candidates.** `engines.domain.corpus.promotion_candidate` (thresholds from `config/uacp.toml [memory.distillation]`) identifies `"effective"` or `"chronic"` lessons. For each candidate:
- Gather the related lesson cluster + existing `.uacp/knowledge/` docs on the topic.
- Dispatch an **Agent Council synthesis** (per `../uacp-core/references/agent-council-followthrough.md`) to abstract a generalized pattern.
- **Extend-over-create**: update an existing knowledge doc if it owns the topic; otherwise create one. Persist via `engines.oracle.corpus_writer.persist_knowledge` to `.uacp/knowledge/`.
- Set backlinks: `derived_from` on the knowledge doc (lesson ids used as input) and `promoted_to` on each source lesson (knowledge id) — re-persist each modified lesson via `engines.oracle.corpus_writer.persist_lesson`.

**Top-down intake**: design docs, ADR digests, and research/analysis may author `.uacp/knowledge/` directly with no lesson behind them — build a `KnowledgeItem` and persist it via `engines.oracle.corpus_writer.persist_knowledge`.

Path resolution is owned by the Oracle corpus-write surface (`engines.oracle.corpus_writer` resolves `lessons` / `knowledge` via the config resolver internally) — RESOLVE routes all corpus read/write through it and never hard-codes `.uacp/` paths or loads the corpus directories directly.

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

