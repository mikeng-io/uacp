# Proposal package envelope vs substance — 2026-05-18 session lesson

## Why this reference exists

During UACP PROPOSE repair, the operator challenged whether the new proposal artifacts had collapsed back into a single YAML. That correction is durable: serious PROPOSE work must be package-first, not YAML-first.

## Correct artifact shape

For medium/high consequence work:

```text
proposals/{run_id}/                       # human-readable proposal package
proposals/{run_id}/00-index.md            # package map
proposals/{run_id}/proposal.md            # intent/objective
proposals/{run_id}/authority-*.md         # authority/scope/containment as selected
proposals/{run_id}/risks-*.md             # risk/verification as selected
proposals/{run_id}/artifacts.md           # artifact map
proposals/{run_id}/machine/package-selection.yaml
proposals/{run_id}-proposal.yaml          # machine lifecycle envelope
proposals/{run_id}-gate-selection.yaml    # gate selection envelope
proposals/{run_id}-package-selection.yaml # bridge/check artifact
```

The exact Markdown filenames are context-selected. The concerns are mandatory; the filenames are not.

## What each layer means

- Markdown files explain intent, authority, containment, risks, selected modules, and transition readiness.
- Top-level YAML files exist so validators, Heartgate, and ledger tooling can reason about lifecycle state.
- `package-selection.yaml` is not the proposal. It is the bridge that maps universal and selected concerns to artifacts and records N/A rationale.

## Response pattern when challenged

If the operator asks whether PROPOSE became "single YAML again":

1. Acknowledge the concern directly.
2. State whether a package directory exists and where the substance lives.
3. Clarify that YAML artifacts are envelopes/bridge only.
4. If the package is missing, treat it as a BLOCK and create/patch the package before PLAN.
5. If package-local and top-level YAML drift, sync them and keep an explicit artifact map.

## Enforcement pattern

Do not stop at doctrine text. For adaptive PROPOSE packages, wire the rule into:

- proposal/package-selection validation;
- N/A schema completeness (`reason`, `accepted_by`, `owner`, `residual_risk`, `revisit_phase`, and where relevant `revisit_trigger`);
- positive/negative fixtures;
- Heartgate/Guardian checks when transition behavior is claimed;
- Agent Council review of the Markdown package, not just YAML metadata.

## Boundary with PLAN

PROPOSE covers intent, authority, scope, containment, risk, verification posture, transition readiness, and artifact map.

PLAN covers execution topology, work breakdown, dependencies, runtime/tool selection, rollback, and detailed verification schedule.

If proposal docs begin naming detailed implementation tranches or function-level patches, mark those as PLAN obligations instead of letting PROPOSE become premature PLAN.
