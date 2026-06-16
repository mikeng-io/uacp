# Adaptive Gate Selection Rationale

UACP cannot inherit Trustless ACP's fixed software-engineering gate checklist. Trustless ACP worked in a constrained domain, so predefined gates were reasonable. UACP is universal and must adapt across software, infra, research, marketing, productivity, lifestyle, creative, operations, and mixed-domain work.

## Core Rule

Before each phase decision, run a **meta-gate / gate-selection preflight** that selects the evidence needed for the specific domain and context.

```text
phase context
  -> meta-gate / gate-selection preflight
  -> selected evidence clusters
  -> concurrent execution
  -> fan-in synthesis
  -> phase transition decision
```

The lifecycle phases stay stable:

```text
TRIAGE -> PROPOSE -> PLAN -> EXECUTE -> VERIFY -> RESOLVE
```

Gates and clusters inside a phase are adaptive; the phases themselves are not.

## What the Meta-Gate Decides

For the current task, the meta-gate classifies:

- domain(s): software, infra, marketing, research, lifestyle, productivity, compliance, creative, mixed
- artifact type: code, doc, plan, post, purchase decision, workflow, design, etc.
- risk level and blast radius
- side effects and reversibility
- need for current/external facts
- affected workspaces or systems
- applicable skills/docs/domain registry entries
- prior rejected designs or lessons

It outputs:

- `required_clusters`
- `optional_clusters`
- `not_applicable_clusters` with reasons
- `generated_clusters` for context-specific checks
- `non_waivable_invariants`
- reasoning for selection

## Non-Waivable Invariants

The meta-gate may adapt evidence requirements, but it cannot waive constitutional invariants:

- explicit authority
- declared side effects
- write containment
- traceable state changes
- privacy/safety constraints
- conservative failure on missing required config/evidence

## VERIFY Examples by Domain

**Software/code VERIFY** may select: tests, diff review, security review, runtime validation, rollback validation.

**Marketing/content VERIFY** may select: audience fit, brand consistency, claims grounding, legal/compliance risk, channel formatting.

**Research VERIFY** may select: source quality, claim-to-source mapping, recency/currency, contradiction scan, confidence rating.

**Productivity/lifestyle VERIFY** may select: constraints and preferences, availability, safety, cost, reversibility.

## Implementation Note

The live implementation lives in `config/gate-selection.yaml` alongside `config/evidence-clusters.yaml` and `config/phase-transitions.yaml`. Each phase skill (`uacp-propose`, `uacp-plan`, `uacp-verify`) should run gate-selection before fan-out. PLAN should rerun selection because new risk/domain facts often appear during planning. VERIFY should run against actual completed artifacts, not the initial proposal only.
