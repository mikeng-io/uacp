---
name: uacp-propose
description: Use when creating governed UACP proposals, bootstrap artifacts, or authority
  declarations.
phase: propose
allowed_tools:
- uacp_artifact_write
- uacp_state_write
- uacp_gate_ledger_append
- uacp_heartgate_check
- uacp_doc_write
- uacp_run_registry_update
- uacp_escalation_event
forbidden_tools:
- terminal
- execute_code
phase_exit_invariants:
- artifact_glob: proposals/{run_id}*.yaml
  required: true
- gate_ledger_entry: TRIAGE->PROPOSE
  required: true
authority_source: config/phase-transitions.yaml (mirror; config wins on conflict)
---
# UACP Propose

## Purpose
This skill creates the proposal artifact that states why the work exists,
who authorized it, what changes are in scope, and what side effects are declared.

## Read first
- `UACP_ROOT/docs/INDEX.md`
- `UACP_ROOT/docs/policy/constitution.md`
- `UACP_ROOT/docs/lifecycle/lifecycle-reference.md`
- `UACP_ROOT/config/evidence-clusters.yaml`

## Rules
- Capture authority, scope, side effects, and containment explicitly.
- Keep the proposal bounded and reviewable.
- Do not jump into planning before the proposal is viable.
- **Do not leave proposal inputs in Vault/Obsidian** — When the material contains accepted decisions, formal schemas, source registry contracts, runtime boundary sketches, council synthesis, manifests, or implementation-adjacent examples, treat it as UACP proposal/planning material. Promote or copy it into a UACP artifact path before PROPOSE, leaving Vault as pointer/summary only.
- **If canonical UACP_ROOT is unavailable, use explicit non-Vault staging** — Create a staging artifact directory with README/manifest, record that it is not canonical, and carry a next-phase obligation to import/select the canonical UACP root before PLAN finalization.
- **Do not skip TRIAGE adoption** — Before treating a proposal as adopted, verify
  that the originating TRIAGE phase is complete enough for the request class.
  For governance-core work touching lifecycle semantics, Agent Council,
  Heartgate/Guardian, protected state, artifact schemas, or runtime enforcement,
  check for TRIAGE council/transition evidence when selected.
  If proposal artifacts were drafted early, mark them provisional and adopt/patch
  them only after TRIAGE→PROPOSE transition.
- **Reference the triage artifact** — Every proposal must link to its originating
  triage artifact (`state/runs/*-triage.yaml`) to maintain traceability.
- **Scope must be implementable** — If the user says "this is a medium spec",
  treat it as a signal to keep the proposal bounded and avoid over-engineering.
- **MUST create gate-selection artifact** — Per `lifecycle-reference.md`,
  PROPOSE requires an `initial gate-selection artifact` with:
  - `selection_id`, `run_id`, `phase`
  - `domains`, `artifact_types`
  - `risk_level`, `granularity_level`
  - `invariant_checks` (all non-waivable invariants with pass/block status + reason)
  - `selected_clusters` (required / optional / generated)
  - `not_applicable` clusters with reason
  - `transition_requirements`
  - `reasoning`
  See `config/gate-selection.yaml` for full schema.
- **Agent council review is context-selected, not automatically external** —
  If user requests council review or the proposal risk/routing requires it,
  select the council surface from UACP routing doctrine.
  Delegate Task / Kimi-style local council is acceptable for bounded proposal
  critique when it provides sufficient perspective; external bridges are
  escalation paths only when scale, runtime diversity, independence, or
  verification confidence materially justify them.
- **Audit trail is required** — Record all significant events
  (issue report, diagnosis, council dispatch, operator decisions)
  with timestamps and actors.
- **Validator shape matters** — Proposal artifacts should include validator-required
  fields (`phase: propose`, `triage_artifact`, `objective`, `scope.in_scope`,
  `scope.out_of_scope`, `declared_side_effects`, `authority.status`, and
  `human_involvement`) even when richer aliases such as
  `originating_triage_artifact` are also present.

## Typical outputs
- proposal artifact in `proposals/`
- gate-selection artifact in `proposals/`
  (name: `<proposal-id>-gate-selection.yaml`)
- reference to originating triage artifact
- for medium/high consequence work: adaptive proposal package under `proposals/{run_id}/`

## Adaptive proposal package requirement

For medium/high consequence implementation tracks, new project substrates, schema/runtime boundaries, governance changes, operations, research/design tracks, or work that will later enter PLAN/EXECUTE, PROPOSE must create a human-reviewable proposal package in addition to YAML lifecycle records.

Read and apply:

- `references/modular-proposal-package.md`
- `references/adaptive-proposal-documentation-lifecycle.md`
- `references/adaptive-proposal-package-enforcement-20260518.md`
- `references/proposal-package-envelope-vs-substance-20260518.md`

This is UACP-native, not an OpenSpec import. OpenSpec and Trustless ACP are pattern evidence only. UACP documentation selection is adaptive and context-driven: granularity informs rigor, but the work's actual heart determines which documentation modules are needed.

Universal core concerns:

```text
intent
authority
scope
containment
risk
verification
transition
artifact_map
```

Domain-selected modules may include requirements/spec delta, design/architecture, tasks/work packages, operations/runbook, policy/governance, data/state stewardship, security/compliance, research/evidence, communication/change management, or user/decision journal.

A single proposal YAML, gate-selection YAML, or council synthesis is not sufficient for serious work. Those are governance records, not the complete proposal package. Treat top-level YAML artifacts as **machine lifecycle envelopes/exports** for validators and Heartgate; the proposal substance lives in the package directory. When compatibility requires duplicated top-level YAML and package-local YAML, keep the artifact map explicit so future agents do not mistake the envelope for the package.

**Artifact audit pitfall:** when checking whether PROPOSE is complete, do not stop at `proposals/{run_id}-proposal.yaml` and `*-gate-selection.yaml`. Explicitly check for the Markdown package directory `proposals/{run_id}/`, its `00-index.md`, substantive Markdown modules, and `proposals/{run_id}-package-selection.yaml`. If the run already advanced with only YAML envelopes, report that the Markdown proposal package is missing and backfill it from authoritative lifecycle artifacts before claiming strict UACP completeness.

For selected medium/high consequence work, missing selected concerns without explicit not-applicable rationale are a BLOCK for PROPOSE→PLAN, not a soft warning. Do not block solely because an OpenSpec-style filename is absent if the concern is covered appropriately elsewhere.

When the package itself is repairing UACP PROPOSE or lifecycle semantics, drive the sequence in the main orchestrator, use Agent Council/delegate_task for bounded critique, and use Kanban only if EXECUTE becomes multi-lane or durable async work. Keep downstream proving cases paused until VERIFY/RESOLVE. For self-repair, do not stop at skill/config prose: wire the rule into validator fixtures and, where transition behavior is claimed, Heartgate/kernel-level enforcement or an explicit accepted residual risk.

## Updated doctrine alignment
Read additionally:
`UACP_ROOT/docs/lifecycle/orchestration-model.md`,
`UACP_ROOT/config/review-routing.yaml` (council grammar/surfaces; operator knobs in `config/uacp.toml [review]`),
`UACP_ROOT/config/phase-transitions.yaml`.

Do not require external bridge dispatch merely because work is medium-sized.
Select council mode/tier from phase-local granularity, risk, domains, side effects,
and evidence need. Record phase-local granularity entry/exit estimate,
updated downstream projections, and human involvement requirement if authority
or side effects are unclear. If the proposal changes canonical docs/config or
will end in a phase transition, state that the eventual implementation must use
`uacp_doc_write` / `uacp_config_write` for docs/config and
`uacp_heartgate_check` for the transition artifact.

## Proposal-council remediation pattern
For UACP governance/runtime/council proposals, convert council findings into
concrete proposal/gate-selection/package patches before PROPOSE→PLAN.
If council is used, record a council synthesis artifact matching
`config/phase-transitions.yaml#council_synthesis_schema` instead of ad hoc
`agent_council:` prose. For handled negative findings, use the follow-through
gate: remediated/expanded/justified material findings require handling evidence
and follow-up Agent Council where selected; deferred/accepted_warning/rejected_with_reason
findings require Heartgate-visible owner, residual risk, and next-phase obligation.
See `../references/proposal-council-concerns-pattern-20260515.md` for the full pattern.

For medium/high-consequence runs, proposal council must review the adaptive proposal package, not only YAML metadata. If universal core concerns or gate-selected domain modules are missing without explicit not-applicable rationale, treat that as a material proposal-quality concern before PROPOSE→PLAN. Do not require fixed OpenSpec-style filenames when the concerns are covered by context-appropriate documents.

### Validator and Heartgate artifact-shape pitfalls
Preserve these concrete requirements when preparing PROPOSE→PLAN:
- Proposal artifacts must include validator-required top-level fields:
  `phase: propose`, `triage_artifact`, `objective`, `scope.in_scope`,
  `scope.out_of_scope`, `declared_side_effects`, `authority.status` as
  `pass|warn|block`, and `human_involvement`.
- Council synthesis artifacts must use canonical shape: `council_id`, `mode`,
  `tier`, `phase`, `phase_local_granularity`, `roles`, `dispatch_surfaces`,
  `findings`, `verdict`, `artifact_paths`, and `inspected_paths`.
- Transition artifacts consumed by Heartgate should use list-shaped
  `invariant_summary` and `cluster_summary` entries
  (`id/status/evidence`, `cluster_id/state/artifact_path`).
- Heartgate warning/deferred encoding must include `owner`, `residual_risk`,
  and `next_phase_acceptance`.
- Run both checks: first the lightweight artifact validator, then
  `uacp_heartgate_check`.

## Adaptive proposal package sufficiency

Do not treat Markdown proposal packages as optional merely because a task is light or standard. YAML proposal artifacts are machine lifecycle envelopes; they rarely preserve enough why/how/context by themselves when the task touches public/private boundaries, identity data, runtime prompt-context injection, governance policy, validators, Heartgate/Guardian behavior, irreversible side effects, or non-trivial rollback.

For those cases, create a concise human-readable proposal package under `proposals/{run_id}/` plus `proposals/{run_id}-package-selection.yaml`. The package may be small, but it must preserve:

- what is changing
- why it is changing / rational intent
- authority, scope, and containment
- invariants
- risks and required verification
- artifact map / transition meaning

See `../uacp-plan/references/operator-summary-and-package-sufficiency-20260519.md` for the session lesson that triggered this rule.

## Phase-specific operating contract — PROPOSE
- **What this skill does:** produce bounded proposal: objective, authority,
  in/out scope, side effects, non-goals, gate-selection, and proposal council response.
- **Why it does it:** ensure work is authorized and coherent before planning implementation.
- **How it does it:** load triage/gate policy, draft proposal artifacts,
  run proposal council when selected, classify council findings,
  require follow-through before proposal adoption, prepare PROPOSE→PLAN transition.
- **Constraints:** do not execute implementation; do not silently accept concerns;
  no destructive/external actions; no bypass of missing TRIAGE evidence.
- **Reason / rational intent / decisions:** intent is authority framing:
  decide what is being proposed and why it is allowed;
  decisions are scope, side effects, risks, accepted non-goals, required gates.
- **Tools to use / not use:** use: file reads, delegate_task council, validator,
  uacp_heartgate_check; avoid: implementation tools except artifact drafting,
  direct production/runtime mutation.

This phase-specific contract complements `../references/agent-council-followthrough.md`;
the shared reference supplies the common follow-through gate, while this section
defines this phase's own job, intent, constraints, decisions, and tool boundary.

## Agent Council follow-through wiring
When this phase invokes or consumes Agent Council output, execute
`../references/agent-council-followthrough.md` rather than treating council review
as prose advice. PROPOSE council reviews proposal authority, scope, and artifact
viability. PLAN/VERIFY councils review implementation and evidence.

## mode_behavior (Phase 4.3 stub)

This skill consults `config/uacp.toml [autonomy]` to decide which actions
require operator confirmation per the active `state.current.uacp_mode`.

| mode | Behavior in PROPOSE | Operator confirmation |
|---|---|---|
| manual | every action requires operator confirmation | yes (all transitions) |
| semi_auto | autonomous within-phase actions; operator confirms transitions | yes (transitions only) |
| supervised_auto | Draft proposal, declared side effects, viability assessment, intent doc, autonomous | only on escalation triggers (see below) |
| full_auto | as supervised_auto, plus auto-confirming non-irreversible decisions | only on `trigger_irreversible_write` or `escalation_triggered` |

**Escalates when**: viability=not_viable, or authority.authorization_source is 'implied'/'inferred' under supervised_auto/full_auto.

**Mechanism**: when an escalation trigger fires, this skill emits a
`uacp_escalation_event` record into `state/escalations/{run_id}.jsonl`
(severity ∈ {info, warn, block}). Operators poll the file (push-notify
is Phase 5). See `config/uacp.toml [autonomy.escalation_triggers]` for
the registered triggers.

## Semantic package requirement

For any selected adaptive proposal package, Markdown artifacts are mandatory semantic context, not optional human-facing decoration. The package must let a future agent reconstruct, one month later, without relying on chat history: why the work exists, how the proposed mechanism works, the intention/rationale/decision, and the authority/scope/containment/risks/verification/transition boundary.

`proposals/{run_id}-proposal.yaml` remains a machine lifecycle envelope. It is not sufficient as the semantic substrate for STANDARD/FULL governance work. If a proposal package is selected, `proposals/{run_id}/` must contain Markdown documents with concrete headings and explanatory prose, and `proposals/{run_id}-package-selection.yaml` must map every universal core concern to those documents. Placeholder Markdown or one-line stubs are blockers.

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

## Semantic package requirement

For any selected adaptive proposal package, Markdown artifacts are mandatory semantic context, not optional human-facing decoration. The package must let a future agent reconstruct, one month later, without relying on chat history:

1. Why the work exists.
2. How the proposed mechanism works at a conceptual level.
3. The intention, rationale, and decision.
4. Authority, scope, containment, risks, verification, transition readiness, and artifact map.

`proposals/{run_id}-proposal.yaml` remains a machine lifecycle envelope. It is not sufficient as the semantic substrate for STANDARD/FULL governance work. If a proposal package is selected, `proposals/{run_id}/` must contain Markdown documents with concrete headings and explanatory prose, and `proposals/{run_id}-package-selection.yaml` must map every universal core concern to those documents. Placeholder Markdown or one-line stubs are blockers.

