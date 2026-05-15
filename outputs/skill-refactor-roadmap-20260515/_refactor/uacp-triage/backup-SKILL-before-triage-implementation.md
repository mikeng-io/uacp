---
name: uacp-triage
description: Use when calibrating scope, scoring granularity, or deciding whether a request deserves full UACP governance.
---

# UACP Triage

## Purpose
This skill handles UACP admission. It scores impact, reversibility, domain count, runtime count, and verification difficulty, then routes the request to the right governance level.

## Read first
- `UACP_ROOT/docs/index.md`
- `UACP_ROOT/docs/constitution.md`
- `UACP_ROOT/config/gate-selection.yaml`
- `UACP_ROOT/config/review-routing.yaml`

## Rules
## Rules
- Do not treat TRIAGE as a proposal.
- Do not compress TRIAGE into PROPOSE when routing selects TRIAGE-local council or when high-granularity governance-core work touches Agent Council, Heartgate, Guardian, lifecycle semantics, artifact schema, runtime enforcement, or protected state.
- Do not assume every request needs the full lifecycle.
- Record the routing decision and the score factors.
- Escalate to PROPOSE only when the request is worth governed handling.
- Keep the output compact and machine-readable.
- **Persist the triage artifact** to `UACP_ROOT/state/runs/` with naming convention `{project}-{YYYYMMDD-HHMMSS}-triage.yaml`.

## Sequential phase discipline

Do **not** compress TRIAGE into PROPOSE just because routing feels obvious or the operator says “continue / let go.” For governance-core work, TRIAGE is a real phase with its own possible council and transition evidence.

When the request touches lifecycle semantics, Agent Council behavior, Heartgate/Guardian, protected state, artifact schemas, runtime enforcement, or other authority-plane behavior:

1. Create/patch the TRIAGE artifact first.
2. Decide whether TRIAGE-local Agent Council is selected based on phase-local risk/granularity/domains.
3. If selected, run a TRIAGE council focused only on admission/routing/scope/granularity — not proposal design.
4. Record a TRIAGE council synthesis artifact.
5. Create a TRIAGE→PROPOSE transition/coherence artifact when the run is crossing into PROPOSE.
6. Only then treat PROPOSE artifacts as adopted. If PROPOSE artifacts were drafted early, label them provisional and adopt/patch them after TRIAGE transition.

Scope separation:
- TRIAGE council: admission, routing, scope, granularity, whether UACP Lite/standard/full governance applies.
- PROPOSE council: authority, side effects, proposal quality, artifact contract.

Pitfall: user correction that “TRIAGE and PROPOSE should go one by one” is a workflow correction, not a style preference. Patch the UACP lifecycle skill path immediately if this rule is missing or stale.

## Typical outputs
- proposal-side triage artifact saved to `state/runs/`
- routing decision with granularity level

## Execution Steps

1. **Read gate-selection config** — `UACP_ROOT/config/gate-selection.yaml` for scoring factors and route mapping
2. **Score the request** — Evaluate impact, reversibility, domain_count, runtime_count, verification_difficulty on 1-10 scale
3. **Calculate granularity** — Use weighted formula from config (default: impact 0.30, reversibility 0.20, domain_count 0.15, runtime_count 0.15, verification_difficulty 0.20)
4. **Determine routing** — Map granularity to: `direct` | `lightweight` | `standard_uacp` | `full_governance` | `block_or_clarify`
5. **Write artifact** — Save YAML to `UACP_ROOT/state/runs/{project}-{YYYYMMDD-HHMMSS}-triage.yaml`
6. **Report to user** — Summarize: granularity level, routing outcome, rationale, next step

## Triage Artifact Schema

```yaml
kind: uacp.triage
triage_id: "{project}-{YYYYMMDD-HHMMSS}-001"
request_summary: ">"
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
granularity_level: 1-10
routing_outcome: direct | lightweight | standard_uacp | full_governance | block_or_clarify
rationale: []
artifact_policy: none | lightweight | standard | full
next_step: "..."
```

## Updated doctrine alignment

Read additionally:

- `UACP_ROOT/docs/orchestration-model.md`
- `UACP_ROOT/config/phase-transitions.yaml`

TRIAGE now produces an initial estimate, not final truth. It must record:

- initial composite granularity estimate,
- visible phase-local hotspots or projections,
- whether human involvement is immediately required,
- whether Agent Council should be considered for later phases.

If the request clearly implies a governed lifecycle boundary, note that the eventual transition artifact will need `uacp_heartgate_check`, and that any later canonical docs/config sync must use `uacp_doc_write` / `uacp_config_write` rather than generic file writes.

Triage artifact additions:

```yaml
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
human_involvement:
  required: true | false
  reason: ""
  authority_needed: ""
  decision_owner: ""
```

Human involvement may be selected at TRIAGE for unclear authority, irreversible/external side effects, high granularity with material side effects, unresolved critical risk, or Guardian/Heartgate uncertainty.

## TRIAGE council trigger and sequencing pitfall

For high-granularity governance-core work, TRIAGE may need its own phase-local Agent Council before PROPOSE. Select or strongly consider a TRIAGE council when phase-local/composite granularity is around 7+ or when the request touches Agent Council, Heartgate, Guardian, lifecycle semantics, artifact schema, runtime enforcement, protected state, or phase-transition rules.

Keep council scopes separate:

- **TRIAGE council:** admission, routing, scope, granularity, and whether to enter UACP at all.
- **PROPOSE council:** authority, side effects, proposal quality, artifact contract, and viability.

If PROPOSE artifacts were created early, treat them as provisional drafts. Correct the sequence by writing a TRIAGE council synthesis and TRIAGE→PROPOSE transition/coherence artifact before adopting the PROPOSE artifacts; do not discard useful draft artifacts unless their content is wrong.



## Phase-specific operating contract — TRIAGE

- **What this skill does:** classify request authority, scope, granularity, domains, routing, and whether council/Heartgate are required before PROPOSE.
- **Why it does it:** prevent premature phase compression and make admission/routing decisions explicit.
- **How it does it:** read canonical docs/config, score granularity/risk, record council trigger decision, dispatch TRIAGE-local council for governance-core/high-granularity work, write triage artifact and transition evidence.
- **Constraints:** do not design proposal content; do not approve implementation; do not collapse TRIAGE into PROPOSE; no protected writes except state/triage artifacts through allowed path.
- **Reason / rational intent / decisions:** intent is admission control: decide whether work may enter UACP and under what depth, not to solve the work; decisions are routing outcome, council tier, human involvement, and next phase obligations.
- **Tools to use / not use:** use: read/search/terminal diagnostics, delegate_task for TRIAGE council, uacp_heartgate_check for TRIAGE→PROPOSE; avoid: generic writes to canonical docs/config, production actions, external posts.

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
