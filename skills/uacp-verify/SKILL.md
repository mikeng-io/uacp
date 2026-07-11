---
name: uacp-verify
description: Use when validating completed UACP work with adaptive evidence clusters
  and review routing.
phase: verify
kind: lifecycle
authority_source: "engines/domain/{phase_graph,phase_transitions,gate_rules}.py (phase graph + stages + gate grammar, code-authoritative); config/uacp.toml [heartgate.*] (operator knobs); config/phase-transitions.yaml (LLM-read adaptive-gate doctrine + artifact schemas only)"
---
# UACP Verify

VERIFY is the lifecycle truth boundary before RESOLVE — the measure verb the doer cannot self-grant, so its verdict must be grounded in real evidence and fail-closed (see AGENTS.md Core Principle). It proves implemented work satisfies the proposal/plan and that every carried finding is handled — separating actual correctness from implementation claims. It is not a generic test summary and not a self-repair phase.

## Read first
- `UACP_ROOT/config/evidence-clusters.yaml`
- `UACP_ROOT/config/review-routing.yaml` (council grammar/surfaces; operator knobs in `config/uacp.toml [review]`)
- `UACP_ROOT/config/phase-transitions.yaml` (adaptive-gate doctrine + artifact schemas; phase graph/stages/gate grammar now in `engines/domain/{phase_graph,phase_transitions,gate_rules}.py`)
- `UACP_ROOT/skills/uacp-core/references/agent-council-followthrough.md` (council dispatch protocol, modes, tiers, retrieval-led rule, finding schema, mid-phase escalation)
- `UACP_ROOT/skills/uacp-core/references/generative-gate-authoring.md` (the producer contract — how to author the frozen `uacp.check.*` checks this phase must emit)

---

## Verification procedure

Follow these steps in order. Each step does one thing. Read the linked reference when the step's trigger applies; otherwise proceed.

### Step 1 — Scope the verification
Establish what is being verified before gathering anything.

- Identify what was claimed/done: the actual artifact set, diffs, and execution evidence.
- Pull the plan's success criteria and the proposal's declared evidence obligations.
- Read those criteria, obligations, and any PIV contract as authored — do not re-scope or soften an obligation to make it passable. If one is ambiguous, return to PLAN/PROPOSE rather than reinterpreting it here.
- Note the risk tier (see Step 4) and whether EXECUTE used a PIV contract.
- Do not use a fixed software-only checklist. Select evidence based on task context.
- Stop here and return to PLAN/PROPOSE if the artifacts do not match the proposal or plan.

> **Goal-driven track:** if the run is `track: goal-driven`, VERIFY judges the **checkpoint manifest** and the converged probe, not a fixed `executions/{run_id}` package. Read `uacp-core/references/goal-driven-track.md`. The manifest (`gate: CHECKPOINT` ledger entries) substitutes for verify-selection/resolve-readiness artifacts at closure, but every closure invariant below still fires unchanged.

### Step 2 — Gather evidence per claim from real artifacts
For each claim, collect traceable evidence — never self-attestation.

- Inspect the actual docs/config/scripts/state/runtime artifacts; require file/path/line or command evidence.
- For governance/runtime/artifact-management changes, make verification **retrieval-led**: inspect ground truth first, then reason — never claim coherence from the main session's inferred understanding alone.
- Confirm behavior is wired into the relevant lifecycle skills/SOPs, not only described in canonical docs or config.
- Run deterministic validation (validators, terminal tests) before any council, so reviewers inspect concrete evidence rather than intentions.

> **Read `references/retrieval-led-phase-verify.md`** for governance/runtime VERIFY: deterministic-first ordering, validating current council synthesis, and grounding out-of-repo skill alignment.
> **Read `references/read-only-containment-validation.md`** when running Python validation under read-only containment — use `PYTHONDONTWRITEBYTECODE=1` + AST parsing; do not treat bytecode-write failures as source failures.

### Step 2b — Author the frozen verification checks (generative gate)
For **each obligation / done-claim** this phase owns, author a specific runnable check so the
kernel can re-run it and block "done" if it is missing, weak, or failing — never a self-attested
verdict. Read `UACP_ROOT/skills/uacp-core/references/generative-gate-authoring.md` for the full
contract; in brief:

- **comprehend** the claim and classify it (`from.class`, recording `from.basis`); the class→required
  kind floor is authoritative in `UACP_ROOT/config/verification-floor.yaml`.
- **author** one `uacp.check.<kind>` per target via `uacp_entity_write` — typically
  `obligation_satisfied` (the obligation has a passing assessment, no uncleared block) or
  `artifact_integrity` (the evidence artifact is unchanged since its watermark) — with
  `from.target` = the obligation/work_unit node id, `from.class`, `bind`, and `severity: block`.
- **serialize** — the entity-writer validates + watermarks + registers it, so the coverage gate
  (`GP_UNCHECKED_TARGET`), the floor (`CHK_FLOOR_UNMET`), entailment (`CHK_CLASS_UNDERCLAIM`), and
  replay see it. A target you leave unchecked blocks the VERIFY exit.

### Step 2c — Run the harness loop to convergence (RUN → RECONCILE → LOOP → ESCALATE)
The fixed, deterministic machinery (design node 11) drives the frozen checks to a verdict — no
comprehension lives here. After authoring (Step 2b), loop:

- **RUN / RECONCILE** are the kernel's job: the engine sweep replays every check
  (`validate_check_replay`) and reconciles it with the structural findings (`GP_*`, contradiction).
  You do not re-run these by hand — they fire at the forced `verify_exit` gate and at closure.
- **LOOP** — each round you author a check (or a fix surfaces a new target → author another) and
  **record the move** as a `uacp.investigation_entry` (`move`, fail-closed `verdict`, `check_ref`,
  `target`; `supersedes` the prior attempt when re-trying). Read `investigation_status` (or
  `convergence_status`) from `engines.graph_projection`: keep going while it is **not `dry`**; stop
  when dry (no open `fail`/`error` move, no open contradiction). An open move blocks closure
  (`GP_OPEN_INVESTIGATION`), so you cannot exit a non-dry loop.
- **ESCALATE** — when `convergence_status(...)["escalate"]` lists a target (≥N failing moves, still
  open), stop patching the symptom and emit the **architecture verdict**: fire a `uacp_escalation_event`
  ("the design, not the code, is wrong" for that target). The escalation is recorded in the
  investigation trail and surfaced to the transition gate; it is not a magic phase number.

### Step 3 — Classify every item
Sort each gathered item into exactly one bucket, kept separate in both machine artifacts and semantic packages (see `references/verify-truth-gate-checklist.md` for the canonical distinctions and must-block cases):

- **verified fact** — supported by a source path/locator/command. Facts without source evidence block.
- **assumption** — accepted but not directly verified; requires owner, accepted_by, residual risk, next-phase obligation.
- **deferred item** — unresolved work carried forward; requires owner, revisit trigger, accepted_by, risk-if-delayed, next-phase obligation.
- **warning** — non-blocking risk, valid only when explicitly dispositioned and not hiding a blocker.
- **blocker** — a hard stop.

Also classify council findings using only the canonical states `open`, `resolved`, `accepted_risk`, `not_applicable`, `deferred`. Introduce no unsupported dispositions.

### Step 4 — Run the gate checklist
Run each sub-step as its own check. Tier the depth to risk:

- Low-risk docs/status-only: deterministic verification sufficient; council optional.
- Medium-risk implementation/governance: deterministic verification + Agent Council before RESOLVE.
- High-risk enforcement/authority/lifecycle/profile-boundary/containment: deterministic verification + Agent Council + formal audit/deep review when independent/runtime diversity materially improves confidence.

**4a — Evidence-cluster checks.** Record pass, warn, block, and deferred outcomes per selected cluster. For governed/non-trivial work produce a validator-backed evidence package, not a summary-only YAML (see Step 5 for artifact shape).

**4b — Invariant checks.** Confirm:
- phase-local granularity exit actual and composite granularity update,
- human involvement is required for unresolved CRITICAL findings or protected-action uncertainty,
- Evidence-Domain Registry is not claimed runtime-active while `implementation_status: not_runtime_active`,
- when verification is scoped to a local branch / dry-run proof, label it honestly as `pass_with_deferred_items` (or equivalent) — never full production readiness. Record non-actions explicitly (no push/PR, no DB mutation, no schedule mutation, no public delivery) and list the deferred proof boundary.

> **Read `references/fail-closed-containment-proof.md`** when the remaining blocker is UACP-bound shell/code containment — verify fail-closed behavior explicitly instead of waiting for a sandbox to exist.
> **Read `references/adversarial-runtime-review.md`** before claiming Guardian/Heartgate is production-complete, or after any host-runtime change affecting tool dispatch.

**4c — PIV assessment.** When EXECUTE references a PIV contract, judge Phase Intent Verification obligation-by-obligation. Inspect:
- `plans/{run_id}-piv.yaml`
- `executions/{run_id}-checkpoint-*.yaml`
- `executions/{run_id}/00-index.md` and semantic evidence modules
- evidence-obligation results, deferred items, intent-drift dispositions, next-phase readiness

Decide one of: `pass` / `pass_with_deferred_items` / `block_return_to_execute` / `block_return_to_plan`. Do not treat test success, raw diffs, or worker self-report as sufficient when the contract requires broader evidence.

> **Read `references/piv-execution-evidence-contract.md`** to judge the PLAN-authored PIV/evidence contract against EXECUTE checkpoints. If the PIV contract is missing for non-trivial/governed work, or evidence is YAML-only/raw-file-list without rationale/decision/invariant/drift/evidence mapping, return to EXECUTE or PLAN rather than improvising a pass.
> **Read `../uacp-execute/references/phase-intent-verification-execute-evidence-20260519.md`** for EXECUTE phases referencing `kind: uacp.phase_intent_verification_contract`.

**4d — Council (when tier requires it).** Run a role-diverse Agent Council (Primary Reviewer, Devil's Advocate, Integration Checker, Synthesis Lead) in verify/audit/review mode. Wire it via Step 6. In verify mode, run it with the **verification-gate posture** — default-to-refute + majority-clear (`uacp-council/references/finding-driven-mode.md`): a claim clears only when a majority of verifiers affirm it on grounded evidence, so the gate fails closed when the panel is uncertain.

### Step 5 — Synthesize blockers and concerns with file/path evidence
Assemble the verification package; keep verified facts separate from assumptions/deferred items.

Required machine artifacts when selected:
- `verification/{run_id}-verify-selection.yaml` with `kind: uacp.verification_package`
- `verification/{run_id}-piv-assessment.yaml` with `kind: uacp.piv_assessment` when EXECUTE used PIV.
  Each assessment's `evidence_refs` MUST be **graph node-ids** (e.g. `cp-1-wu-1` — work_unit /
  checkpoint ids), NOT artifact paths: a path is rejected as `GP_PHANTOM_EDGE` (forged/dangling
  reference). The gate is correct; the ref must name a node the graph already knows (#115). For the
  governed-writer context envelope + param conventions, see
  `docs/runtime/runtime-enforcement.md` → *Governed-writer call conventions* (#126).
- `verification/{run_id}-resolve-readiness.yaml` with `kind: uacp.verify_resolve_readiness`

Required semantic package under `verification/{run_id}/`:
- `00-index.md`, `piv-assessment.md`, `verified-facts.md`, `assumptions-and-deferred-items.md`, `findings-and-dispositions.md`, `council-review.md`, `resolve-readiness.md`

The council synthesis artifact uses `kind: uacp.council_synthesis` and records `inspected_paths` for ground-truth files/dirs/commands/evidence. Do not let a deterministic evidence package substitute for council synthesis when the plan or operator requires a VERIFY council — create both and link the synthesis from the transition.

> **Read `references/adaptive-verify-evidence-gate.md`** for the session-derived gate shape, must-block negative fixtures, and pre/post council sequence.
> **Read `../uacp-core/references/lifecycle-semantic-gates.md`** for the lifecycle semantic-gate pattern — VERIFY is the truth boundary before RESOLVE, not optional follow-through.

### Step 6 — Handle findings (no normalize-to-pass)
If council returns blockers, concerns, invariant failures, negative findings, or material warnings, **do not** normalize them into pass after explanation. Execute `../uacp-core/references/agent-council-followthrough.md` rather than treating council output as prose advice:

1. Select mode/tier/dispatch surface from routing config and phase-local risk.
2. Dispatch retrieval-led roles when governance, runtime, artifact schema, Guardian/Heartgate, lifecycle, protected state, or skill behavior is involved.
3. Save `kind: uacp.council_synthesis` under `verification/` with `inspected_paths`, verdict, roles, findings, evidence.
4. Extract all blockers, concerns, invariant failures, negative findings, material warnings.
5. Classify every material finding into the handled-findings matrix before advancing.
6. For `remediated`/`expanded`/`justified` findings, run one focused follow-up council unless a Heartgate-visible exception artifact is recorded.
7. Encode `handled_findings_chain`, `source_negative_findings_present`, and `followup_depth` in the transition artifact.
8. Run Heartgate only after follow-through evidence exists; council synthesis is evidence, not transition approval.
9. Refuse next-phase adoption if the follow-through reference lists a refusal condition.

Cap follow-up council at one rerun for the same finding chain, then block or escalate through Heartgate. Unresolved material findings after the cap block closure unless recorded as accepted risk/deferment with owner and condition.

> **Read `references/phase-end-council-hardening.md`** when council concerns touch a boundary the next phase builds on (writer-path containment, policy classification, Heartgate transition authority, runtime tool exposure) — prefer a small hardening patch before RESOLVE over carrying vague warnings forward; covers the concern-to-fix pattern and manual-drill fallback.

### Step 7 — Determine resolve-readiness and the Heartgate transition
Decide whether RESOLVE may proceed, then validate the boundary.

- `ready_for_resolve: true` is **invalid** with open blockers, missing required PIV assessment, missing Heartgate coherence when required, or a failed self-approval guard.
- If the council returned CONCERNS, do not claim final RESOLVE unless each is explicitly resolved, accepted as non-blocking risk, or deferred with owner/phase and acceptance criteria.
- If the run crosses a lifecycle boundary, verify the transition artifact through `uacp_heartgate_check` before claiming it valid. When `heartgate_coherence` is present, confirm the referenced coherence artifact exists and covers doctrine coherence, cross-artifact consistency, runtime-state alignment, warning/deferred honesty, authority-plane integrity, and next-phase readiness.
- If Heartgate blocks on evidence disposition, add the required `Fact:`/`Disposition:` evidence files rather than weakening the transition artifact.

> **Read `references/heartgate-evidence-disposition-and-reload.md`** for Heartgate-bound VERIFY→RESOLVE: per-cluster `verified-facts`/`assumptions` files with required `Fact:`/`Disposition:` markers, positive-and-negative enforcement fixtures, and recording a runtime-reload warning when file edits are verified on disk but not hot-reloaded in the live tool process.

**Heartgate vs. Council distinction.** VERIFY may run phase-local Agent Council to check the work product, but Heartgate owns transition-boundary coherence before VERIFY→RESOLVE. Phase-local review asks whether the verification package is good; Heartgate coherence asks whether the phase truthfully satisfied its lifecycle contract and whether docs/config/state/runtime/artifacts agree. Keep Heartgate Council/coherence outputs under `verification/`, referenced from transition artifacts via `heartgate_coherence.artifact_path`, separate from `council_synthesis_artifact`.

---

## Self-approval guard

VERIFY must not remediate its own material findings and then self-certify final closure. Any remediation discovered during VERIFY must be routed back through EXECUTE/patch checkpoint or a separate authorized repair step, then re-verified with independent council/audit evidence before RESOLVE.

When self-approval would be a conflict of interest — VERIFY remediating findings it discovered, or a single runtime both producing and certifying work — use an independent runtime/audit (e.g. a separate Agent Council and an independent code-runtime review with model/runtime diversity) rather than UACP protected writers or `uacp-verify` itself as self-approval authority. Work is repaired only after its implementation audit and end-of-implementation council/audit return PASS with no material concerns.

---

## mode_behavior

This skill consults `config/uacp.toml [autonomy]` to decide which actions require operator confirmation per the active `state.current.uacp_mode`.

| mode | Behavior in VERIFY | Operator confirmation |
|---|---|---|
| manual | every action requires operator confirmation | yes (all transitions) |
| semi_auto | autonomous within-phase actions; operator confirms transitions | yes (transitions only) |
| supervised_auto | per-cluster verified-facts and assumptions pair files; council-driven cluster reviews, autonomous | only on escalation triggers |
| full_auto | as supervised_auto, plus auto-confirming non-irreversible decisions | only on `trigger_irreversible_write` or `escalation_triggered` |

**Escalates when:** any unowned pending assumption, or council verdict=block, or PIV first failure.

**Mechanism:** when an escalation trigger fires, this skill emits a `uacp_escalation_event` record into `state/escalations/{run_id}.jsonl` (severity ∈ {info, warn, block}). See `config/uacp.toml [autonomy.escalation_triggers]` for the registered triggers.

---

## Phase-specific operating contract — VERIFY

- **What this skill does:** prove implemented work satisfies proposal/plan and all carried findings are handled.
- **Why it does it:** separate actual correctness from implementation claims before RESOLVE.
- **How it does it:** run deterministic tests, inspect diffs/artifacts, dispatch retrieval-led VERIFY council, validate handled_findings_chain, run focused rerun for remediations, prepare VERIFY→RESOLVE transition.
- **Constraints:** do not accept summary-only reviews for governance/runtime claims; do not close with open blockers; do not conflate phase-local council with Heartgate.
- **Reason / rational intent / decisions:** intent is evidence closure; decisions are pass/warn/block, residual risk, deferred obligations, and whether RESOLVE may proceed.
- **Tools to use / not use:** use validators, terminal tests, read/diff inspection, delegate_task council, uacp_heartgate_check; avoid new feature implementation except minimal verification fixes routed back through EXECUTE/patch checkpoint.

This phase-specific contract complements `../uacp-core/references/agent-council-followthrough.md`; the shared reference supplies the common follow-through gate, while this section defines this phase's own job, intent, constraints, decisions, and tool boundary.

---

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

---

## Retrieval-led prior-art (Oracle)

**Always** call `uacp_oracle_query` at the start of verification (Step 1) to surface the active run's execution history and any relevant prior verification outcomes — retrieval has a **deterministic floor** (#100): even with the semantic Oracle disabled (the default), it returns deterministic corpus matches over `.uacp/lessons` + `.uacp/knowledge`.

```
uacp_oracle_query(phase=verify, project=<project-id>)
```

Results at `phase=verify` are **FULL** mode — run-state packets are `trust_class=authoritative` and can be used as ground-truth evidence for checklist synthesis. Corpus and Honcho packets are `trust_class=normative` or `advisory` and require corroboration before being cited as verification proof. If `uacp_oracle_query` returns no packets (an empty corpus), proceed without retrieval.
