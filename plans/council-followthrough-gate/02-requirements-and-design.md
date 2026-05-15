# Requirements and Design — Council Follow-Through Gate

Run: `council-followthrough-gate-20260514-201718`
Phase: PLAN

## Requirement R1 — handled negative findings cannot silently pass

If a phase-local Agent Council, Heartgate Council, evidence cluster, invariant check, or transition review returns a blocker, concern, invariant failure, negative finding, or material warning, and that item is later marked handled, the transition must preserve a traceable handling chain.

Required chain:

- original finding id/artifact
- finding classification
- handling classification
- handling artifact/evidence
- owner and residual risk
- follow-up Agent Council synthesis when required by materiality/routing
- Heartgate/Guardian transition result

## Requirement R2 — hard vs conditional follow-up

Hard follow-up Agent Council is required when a material finding is marked:

- `remediated`
- `expanded`
- `justified`

Conditional follow-up Agent Council is selected by severity/routing when a finding is marked:

- `deferred`
- `accepted_warning`
- `rejected_with_reason`

Those conditional cases always require Heartgate visibility, owner, residual risk, and next-phase obligation.

## Requirement R3 — material warning threshold

A warning is material when it can affect:

- lifecycle progression
- authority
- non-waivable invariant status
- trust boundary
- side-effect containment
- runtime enforcement
- artifact schema
- next-phase obligations

Pure style/lint/wording issues must not trigger council unless they obscure one of the above.

## Requirement R4 — Heartgate remains independent

Follow-up Agent Council synthesis is evidence, not approval.

Heartgate must independently validate:

- artifact chain completeness
- non-waivable invariants are pass/block only
- warnings/deferred items are owned and accepted by the next phase
- no unresolved blockers remain
- side effects and authority are declared

## Requirement R5 — recursion cap

Default follow-up depth is one rerun. If the follow-up council creates a new blocker/material concern, the system must block or escalate to operator/Heartgate-selected routing instead of spawning unbounded councils.

## Requirement R6 — TRIAGE sequencing correction

For high-granularity governance-core changes, TRIAGE must not be silently compressed into PROPOSE. TRIAGE may require its own phase-local Agent Council focused on admission/routing/scope/granularity, separate from PROPOSE council focused on authority/side effects/proposal quality.

Recommended trigger:

- phase: `triage`
- composite or phase-local granularity >= 7, or
- domains include `agent_council`, `heartgate`, `guardian`, lifecycle semantics, artifact schema, runtime enforcement, or protected state.

## Design shape

### Transition schema / artifact contract

Add or document a transition field equivalent to:

```yaml
handled_findings_chain:
  - original_finding_id: string
    original_artifact_path: string
    finding_classification: blocker | concern | invariant_failure | negative_finding | material_warning
    handling_classification: remediated | expanded | justified | deferred | accepted_warning | rejected_with_reason
    handling_artifact_path: string
    followup_council_synthesis_artifact: string | null
    followup_required: true | false
    owner: string
    residual_risk: string
    next_phase_obligation: string | null
    heartgate_validation: pass | warn | block
```

Keep compatibility with existing Heartgate warning/deferred shape:

- `warnings[].owner`
- `warnings[].residual_risk`
- `warnings[].next_phase_acceptance`
- `deferred_items[].id`
- `deferred_items[].cluster_id`
- `deferred_items[].owner`
- `deferred_items[].condition`
- `deferred_items[].accepted_by`
- `accepted_exceptions[]` for intentionally accepted warning clusters.

### Routing design

- TRIAGE council: admission/routing/scope/granularity only.
- PROPOSE council: proposal authority, side effects, artifact contract, feasibility.
- PLAN council: actual target surface inventory and implementation plan.
- EXECUTE council: patch review / execution critique where selected.
- VERIFY council: evidence, synthetic negative, regression, coherence.

### Validator design

Validator should remain lightweight, but catch:

- council synthesis required fields
- invalid finding state/disposition vocabulary
- transition `heartgate_coherence` lenses
- non-waivable invariants with `warn` or `deferred`
- handled findings chain missing required handling/follow-up fields when present
- warnings/deferred items missing owner/residual-risk/acceptance fields
