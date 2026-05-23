# UACP Lifecycle Skill Contract

This reference is non-authoritative. Canonical authority remains in `UACP_ROOT/docs/index.md`, `UACP_ROOT/docs/constitution.md`, and `UACP_ROOT/docs/lifecycle-reference.md`.

## Shared rules

- Read `UACP_ROOT/docs/index.md` first.
- Use symbolic roots, not cwd-relative paths.
- Do not hardcode model names.
- Do not treat Hermes Kanban as UACP phase state.
- Do not mutate UACP state outside `uacp-state`.
- Keep phase skills thin and single-purpose.

## Current active skill

- `uacp-state`
- `uacp-triage`
- `uacp-propose`
- `uacp-plan`
- `uacp-execute`
- `uacp-verify`
- `uacp-resolve`

## Boundary rule

Phase skills may write only their declared artifact class. Any state or pointer change must route through `uacp-state`.

## Updated doctrine contract

Lifecycle skills implement the canonical UACP docs/config; they do not define doctrine themselves.

Required shared concepts:

- UACP is governance cognition: authority, phase state, risk, human involvement, evidence obligations.
- Agent Council is deliberative cognition: role topology, challenge, synthesis, execution strategy when selected.
- Hermes Kanban is coordination memory: durable task graph, dependencies, ownership, status, and handoffs.
- Runtimes, tool adapters, and evidence services perform bounded work or observation under declared authority.
- Guardian/Heartgate enforce boundaries between these planes.

Every phase skill must preserve phase-local granularity fields when relevant:

```yaml
phase_local_granularity:
  phase: triage | propose | plan | execute | verify | resolve
  entry_estimate: 1-10
  exit_actual: 1-10
  delta_reason: ""
  downstream_projection: {}
composite_granularity: 1-10
human_involvement:
  required: true | false
  reason: ""
  authority_needed: ""
  decision_owner: ""
  accepted_risk_artifact: ""
```

Council synthesis artifacts must follow `UACP_ROOT/config/phase-transitions.yaml#council_synthesis_schema` when a council is selected or required.
