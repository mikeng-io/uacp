# Adaptive Proposal Documentation Pattern

Use this pattern when PROPOSE handles work whose consequence, ambiguity, side effects, or future execution path requires more than lifecycle YAML metadata.

## Why this exists

A single proposal YAML is not enough for serious work. It records governance metadata, but humans and agents also need a reviewable artifact package that explains intent, authority, scope, risk, and the selected documentation surfaces needed for this specific work.

OpenSpec and Trustless ACP are pattern evidence only:

- OpenSpec shows that serious changes need separated review surfaces, not one blob.
- Trustless ACP shows that proposal/state/plan/evidence authority must be separated and guarded.

UACP must stay more universal than both. Do not import their fixed document set, coding bias, gates, domains, or classifications as UACP law.

## Core doctrine

Documentation selection is adaptive and context-driven.

Granularity informs how much rigor, evidence, and review pressure is needed, but granularity does **not** determine a fixed list of documents.

Two proposals with the same granularity may need different artifact modules because their heart is different:

- a security/privacy change may need threat model, containment, audit evidence, and rollback;
- a schema/runtime change may need interface contract, migration, compatibility, validation, and fixtures;
- a policy/governance change may need authority, decision log, precedent, exception rules, and enforcement hooks;
- a research/design track may need question map, evidence review, alternatives, and decision criteria;
- an operational incident may need timeline, blast radius, runbook, mitigation, and verification;
- a documentation/routing correction may need source inventory, routing rules, promotion rules, and traceability.

The package should fit the work's actual decision pressure.

## Universal core concerns

For serious PROPOSE work, cover these concerns somewhere in the package:

```text
intent
= why this work exists and what outcome it seeks

authority
= who/what authorizes it and what authority is missing or provisional

scope
= what is in scope, out of scope, and forbidden

containment
= side effects, protected surfaces, allowed paths, rollback/hold posture

risk
= privacy, security, governance, operational, data, or coherence risks

verification
= how success/failure will be judged before phase transition

transition
= what phase change is requested and what blocks it

artifact_map
= where human-readable docs, machine records, evidence, and canonical outputs live
```

These are concerns, not required filenames. They may be represented as separate files, sections, or structured records depending on context and reviewability.

## Domain-selected modules

Select modules dynamically from the work's nature, not from granularity alone.

Common modules:

```text
requirements_or_spec_delta
= behavior, policy, interface, or acceptance requirements; use scenarios when testable

design_or_architecture
= approach, structure, alternatives, tradeoffs, boundary decisions

tasks_or_work_packages
= draft execution tranches when PLAN-readiness needs decomposition

operations_or_runbook
= operator steps, rollout/rollback, observability, incident response

policy_or_governance
= authority rules, exceptions, enforcement hooks, escalation rules

data_or_state_stewardship
= ownership, migration, retention, provenance, consistency, privacy

security_or_compliance
= threat model, controls, audit expectations, evidence requirements

research_or_evidence
= source review, prior-art comparison, uncertainty, open questions

communication_or_change_management
= stakeholder impact, public/private messaging, adoption notes

user_or_decision_journal
= operator corrections, rationale trace, important context shifts
```

Add other modules when the work demands them. Omit modules only with explicit not-applicable rationale when their absence could affect review.

## Package topology

Use a conductor file plus concern modules.

Recommended shape:

```text
proposals/<run_id>/
  00-index.md              # conductor: selected concerns, reading order, status, blockers
  <core/module docs>        # names chosen by context
  artifacts.md             # artifact map when separate from 00-index
  machine/
    triage.yaml
    proposal.yaml
    gate-selection.yaml
    council-synthesis.yaml # if council is selected
```

For software-like work, this may look like:

```text
proposal.md
requirements.md
design.md
tasks.md
risks.md
```

For governance work, it may look like:

```text
proposal.md
authority.md
policy-delta.md
enforcement.md
risks.md
decision-journal.md
```

For operations work, it may look like:

```text
proposal.md
runbook.md
blast-radius.md
rollback.md
verification.md
```

For research/design work, it may look like:

```text
question-map.md
evidence-review.md
alternatives.md
decision-criteria.md
open-questions.md
```

Do not force every domain into OpenSpec-shaped names.

## Machine artifacts remain required

Still create validator/lifecycle artifacts in the locations expected by UACP validators and Heartgate, for example:

```text
proposals/<run_id>-triage.yaml
proposals/<run_id>-proposal.yaml
proposals/<run_id>-gate-selection.yaml
verification/<run_id>-council-synthesis.yaml
state/gate-ledger/<run_id>.jsonl
```

Machine artifacts do not replace the human-reviewable package. The package's `00-index.md` or `artifacts.md` must map human-readable docs to machine lifecycle records.

Compatibility note: if both package-local machine files and top-level validator-required YAML files exist, list their relationship explicitly. Do not let two layouts drift silently.

## Proposal readiness rule

For selected medium/high-consequence work, PROPOSE is blocked from PLAN unless:

- `00-index.md` exists or equivalent conductor exists;
- universal core concerns are covered or explicitly marked not-applicable with rationale;
- selected domain modules exist with enough detail for review;
- omitted expected modules have not-applicable rationale, owner, and residual risk where relevant;
- artifact map links package docs, machine records, evidence, and canonical/staging paths;
- gate-selection artifact exists in the validator-required location;
- council findings are classified and dispositioned when council was used.

If the package is absent, if selected concerns are missing, or if not-applicable rationale is weak, record PROPOSE as incomplete and do not create/adopt PROPOSE→PLAN transition.

## Not-applicable standard

`not_applicable` is allowed only when it states:

- what concern/module is omitted;
- why it does not apply to this work;
- who accepts the omission;
- what residual risk remains, if any;
- whether the concern must be revisited in PLAN/EXECUTE/VERIFY.

## Anti-patterns

Do not treat these as sufficient by themselves:

- one proposal YAML;
- one gate-selection YAML;
- one council synthesis;
- a fixed OpenSpec-style document quota;
- granularity-only document selection;
- a large mega-doc;
- Vault-only architecture notes;
- weak blanket `not_applicable` entries.

## LEXA correction

The LEXA run `lexa-20260518` exposed the gap. It first produced governance YAMLs and implementation-adjacent documents without a UACP-native adaptive package. The correction is not to force a fixed OpenSpec-style file list, but to select the package modules that match LEXA's actual heart: retrieval/context substrate, public/private boundary, source ownership, schema contracts, Cortex/Nora consumers, and governance enforcement.
