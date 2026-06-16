---
name: uacp-triage
description: Calibrate UACP admission, scope, granularity, routing depth, council,
  and human authority before proposal.
phase: triage
authority_source: "engines/domain/{phase_graph,phase_transitions,gate_rules}.py (phase graph + stages + gate grammar, code-authoritative); config/uacp.toml [heartgate.*] (operator knobs); config/phase-transitions.yaml (LLM-read adaptive-gate doctrine + artifact schemas only)"
---
# UACP Triage

Triage is UACP admission control. It decides whether a request should enter UACP and at what governance depth.
It also records what obligations the next phase inherits.

It does not design the proposal.
## When to use
Use for unclear scope, governance-depth decisions, granularity scoring, phase admission, or deciding routing depth.
Routing depth may be direct, lightweight, standard, full-governance, or block/clarify.

## Read when needed
- `UACP_ROOT/config/gate-selection.yaml` — scoring factors (descriptive) and artifact schemas; scoring weights/method/route-bands in `config/uacp.toml [gates.scoring]`
- `UACP_ROOT/config/review-routing.yaml` — council/review doctrine, grammar, and surfaces; operator knobs (operating_mode, escalation_rules, followthrough depth) in `config/uacp.toml [review]`
- `UACP_ROOT/docs/lifecycle/orchestration-model.md` — phase and council boundaries
- `UACP_ROOT/config/phase-transitions.yaml` — adaptive-gate doctrine (LLM-read; `selected_when_any`/`block_when`/`required_artifacts` blocks) + artifact schemas
- `UACP_ROOT/skills/uacp-core/scripts/engines/domain/phase_graph.py` — codified valid transitions (`LIFECYCLE_GRAPH`)
- `UACP_ROOT/skills/uacp-core/scripts/engines/domain/gate_rules.py` — codified gate/rule grammar (heartgate_coherence, run_registry, piv_rule)
- `UACP_ROOT/config/uacp.toml` (`[heartgate.*]` — operator-tunable coherence thresholds and enforcement mode)

## Rules
- TRIAGE is not PROPOSE.
- Do not compress TRIAGE into PROPOSE for governance-core or high-granularity work.
- If TRIAGE estimates granularity around 7+, strongly consider TRIAGE-local council before PROPOSE.
- Do not assume every request needs full lifecycle governance.
- Keep scoring adaptive and config-driven, not Trustless-specific.
- Treat the output contract below as the default minimum; extend it from canonical config/schema if present.
- Record routing decision, score factors, council trigger, and human-involvement decision.
- Keep output compact and machine-readable.

## UACP vs non-UACP naming rule

If the operator asks “UACP or no UACP” or rejects “UACP Lite”, TRIAGE must not use informal labels as authority. Record the work as admitted to UACP or not admitted. If admitted, use the canonical `routing_outcome` enum (`direct`, `lightweight`, `standard_uacp`, `full_governance`, `block_or_clarify`) and state that UACP owns granularity. Do not call a selected `lightweight`/`standard_uacp` path “UACP Lite” in user-facing summaries or artifacts.

## Execution checklist
1. Summarize the request and authority source.
2. Score visible factors from config: impact, reversibility, domain count, runtime count, verification difficulty.
3. Estimate phase-local and composite granularity.
4. Select routing outcome: `direct`, `lightweight`, `standard_uacp`, `full_governance`, or `block_or_clarify`.
5. Decide whether TRIAGE-local Agent Council is required.
6. Decide whether immediate human authority is required.
7. Record a compact triage artifact or update the active refactor artifact.
8. If routing to PROPOSE, record TRIAGE→PROPOSE obligations; do not adopt proposal artifacts early.
9. Report routing outcome and next phase obligations.

## Track selection

TRIAGE selects the lifecycle **track** by applying one mechanical test:

> *Is the success criterion specifiable as a verifiable artifact before EXECUTE begins?*
> - **yes** → `track: standard` (the default)
> - **no** → `track: goal-driven`

Record the result as `track` on the triage artifact. When the key is absent it defaults to `standard`; existing runs without the field are unaffected.

Valid values: `standard | goal-driven`. Any other value is a Heartgate BLOCK.

**The TRIAGE `track` is authoritative.** Heartgate binds the run manifest's `track` to this value at PROPOSE→PLAN (a worker may not self-select `goal-driven` to relax the PIV-artifact gate). So a mistaken TRIAGE choice propagates — apply the mechanical test honestly.

**Goal-driven obligations to record forward.** When `track: goal-driven`, TRIAGE must hand two obligations to PROPOSE:
- a **persistent goal** — the invariant the whole run-chain serves (becomes the manifest `goal_id`); name it in `next_step`/obligations even though PROPOSE establishes it formally.
- a **convergence budget** — PROPOSE must author `proposals/{run_id}-convergence-budget.yaml` (a positive `max_checkpoints`), or Heartgate blocks PROPOSE→PLAN. Flag this as a PROPOSE obligation so an autonomous run cannot loop unbounded.

## Council and human-involvement trigger
Strongly consider TRIAGE-local council when granularity is high, authority is unclear, or phase compression risk exists.
Also consider it when the request touches lifecycle semantics, Agent Council behavior, Guardian/Heartgate boundaries,
protected state, artifact schemas, runtime enforcement, or phase-transition rules.

TRIAGE council reviews admission, routing, scope, granularity, and whether UACP applies.
PROPOSE council reviews authority, side effects, proposal quality, artifact contract, and viability.

Human involvement is required for unclear authority, irreversible/external side effects, unresolved critical risk,
or Guardian/Heartgate uncertainty.

## Output contract
The YAML below is the default minimum artifact contract, not a closed universal schema.
Additional fields may be added when canonical UACP config/schema requires them.

```yaml
kind: uacp.triage
triage_id: "{project}-{YYYYMMDD-HHMMSS}-001"
request_summary: "..."
authority:
  status: pass | warn | block
  source: "..."
factor_scores:
  impact: 1-10
  reversibility: 1-10
  domain_count: 1-10
  runtime_count: 1-10
  verification_difficulty: 1-10
  notes: []
phase_local_granularity:
  phase: triage
  entry_estimate: 1-10
  exit_actual: 1-10
  delta_reason: ""
  downstream_projection:
    propose: 1-10
    plan: 1-10
    execute: 1-10
    verify: 1-10
    resolve: 1-10
composite_granularity: 1-10
routing_outcome: direct | lightweight | standard_uacp | full_governance | block_or_clarify
rationale: []
artifact_policy: none | lightweight | standard | full
council:
  required: true | false
  reason: ""
human_involvement:
  required: true | false
  reason: ""
  authority_needed: ""
  decision_owner: ""
next_step: "..."
```

## Shared follow-through
When TRIAGE invokes or consumes Agent Council output, use `../uacp-core/references/agent-council-followthrough.md`.

This file exists in the current skill library and is intentionally not modified in this phase.

Agent Council synthesis is evidence, not transition approval.

Before advancing, classify material blockers/concerns and record handled findings in transition evidence.

## Self-repair caveat
During this skill-library refactor, do not use UACP protected writers, Heartgate, MEMEX/BES, or `uacp-verify`
as self-approval authority. Use normal file/git workflow plus Hermes/Kimi council verification.

For normal UACP operation, TRIAGE-local council is for admission, routing, and granularity.
Full Agent Council is reserved for lifecycle semantics, Guardian/Heartgate uncertainty,
or high-impact governance ambiguity.
A skill is considered repaired only after its own implementation audit and end-of-implementation council
return PASS/no concerns.

## mode_behavior (Phase 4.3 stub)

This skill consults `config/uacp.toml [autonomy]` to decide which actions
require operator confirmation per the active `state.current.uacp_mode`.

| mode | Behavior in TRIAGE | Operator confirmation |
|---|---|---|
| manual | every action requires operator confirmation | yes (all transitions) |
| semi_auto | autonomous within-phase actions; operator confirms transitions | yes (transitions only) |
| supervised_auto | Routing decisions (direct / lightweight / standard / full_governance) and write the triage artifact, autonomous | only on escalation triggers (see below) |
| full_auto | as supervised_auto, plus auto-confirming non-irreversible decisions | only on `trigger_irreversible_write` or `escalation_triggered` |

**Escalates when**: blast_radius=high/critical at routing time, or operator-asked clarification needed.

**Mechanism**: when an escalation trigger fires, this skill emits a
`uacp_escalation_event` record into `state/escalations/{run_id}.jsonl`
(severity ∈ {info, warn, block}). Operators poll the file (push-notify
is Phase 5). See `config/uacp.toml [autonomy.escalation_triggers]` for
the registered triggers.

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

