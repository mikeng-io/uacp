# UACP Alignment Spec

This spec defines the canonical artifact root layout and generic alignment conventions for UACP. It covers artifact directory layout, gate selection model, review routing alignment, and knowledge alignment — these are generic UACP conventions that apply regardless of host runtime.

## Hermes/Norty Deployment Preferences

The following constraints are specific to the current Hermes/Norty deployment. They are not generic UACP policy and should not be treated as universal governance invariants. A different deployment may legitimately override these.

- Use Hermes-only framing unless another project boundary is explicitly requested.
- Keep the main orchestration context lean.
- Delegate heavy coding or analysis to bounded workers when appropriate.
- Use Hermes Kanban for durable execution graphs.
- Avoid hardcoded model names in governance docs.
- Keep gate-learning artifacts out of Honcho memory.
- Do not touch `PRIVATE_ROOT`.

## Artifact Root

All Stage 1 and Stage 2 writes live under:

`UACP_ROOT`.

Initial top-level directories:

```text
proposals/
plans/
executions/
verification/
outputs/
knowledge/
config/
docs/
state/
```

Initial local knowledge directories:

```text
knowledge/scenarios/
knowledge/gate-templates/
knowledge/lessons/
knowledge/indexes/
```

## Gate Selection Alignment

UACP starts with `TRIAGE`, which decides whether a request should be handled directly, lightly governed, routed through standard UACP, or escalated to full strategic governance.

After triage, the meta-gate must:

- classify the task and artifact context,
- retrieve or inspect available universal and domain templates,
- preserve non-waivable invariants,
- rank candidate clusters by relevance and risk,
- mark irrelevant clusters not applicable with reasons,
- generate scenario-specific clusters when templates are insufficient,
- write a traceable gate-selection artifact.

## Review Alignment

Review routing is adaptive. UACP may use lightweight local review, Hermes Kanban tasks, delegated analysis, Agent Council tiers from `docs/lifecycle/orchestration-model.md`, or human operator review depending on risk, phase-local/composite granularity, and available tools. Legacy terms map as follows: local council roughly maps to `tier_1_bounded` or `tier_2_role_diverse`; deep council maps to `tier_3_cross_runtime` or `tier_4_deep_council`.

Unavailable review surfaces should be recorded. High-risk missing review support should block or escalate; low-risk missing review support can be noted as a warning.

## Knowledge Alignment

Local learning artifacts are seed material for a future Knowledge Bank. The future service should expose retrieval and ranking APIs for scenarios, gate templates, lessons, and artifacts. This stage only defines file locations and artifact shapes.
