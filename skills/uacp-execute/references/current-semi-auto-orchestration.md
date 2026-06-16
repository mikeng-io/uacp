# UACP Current Semi-Auto Orchestration Model

Use this reference when UACP work touches orchestration topology, Agent Council, profiles, delegate_task, or Hermes Kanban.

## Locked current-stage model

Current UACP execution is manual/semi-auto first.

```text
TRIAGE / PROPOSE / PLAN / VERIFY / RESOLVE:
  default: main orchestrator
  optional helpers: delegate_task same-profile branch, external runtime when justified
  no Kanban by default

EXECUTE:
  default for non-trivial work: coordination adapter, currently Hermes Kanban
  worker surfaces: Hermes profile/default worker, delegate_task inside worker, external runtime, tool/evidence adapter, human checkpoint
```

## Key boundaries

- `delegate_task` is a synchronous same-profile branch. It does not load a separate Hermes profile home, profile-local SOUL.md, memory, or skills.
- Named UACP profiles such as `uacp-planner` and `uacp-verifier` are current-stage role templates / future execution identities unless async profile-specific work is explicitly justified.
- Hermes Kanban is a replaceable coordination adapter, not UACP doctrine and not the Agent Council substrate.
- Agent Council is an adaptive deliberation protocol. It may use delegate branches, profile workers, external runtimes, humans, and coordination adapters as selected by phase-local topology.
- A Kanban task is a bounded work unit inside a phase, most often EXECUTE; it is not automatically equal to a UACP lifecycle phase.

## When to use Kanban / coordination

Use coordination when a phase or unit needs at least one of:

- durable multi-worker ownership,
- profile-specific workers,
- long timeout/background execution,
- dependencies between units,
- retry/rerun/regrouping,
- notification/resume across sessions,
- audit trail for worker outputs,
- external runtime coordination,
- full-autonomy command-bot execution.

## Future reserved slots

Reserve but do not prematurely implement:

- full autonomous phase controllers / command bot topology,
- Profile Council as actual named-profile workers,
- coordination adapter interface beyond Hermes Kanban,
- adaptive Agent Council coordinator with rerun/regroup/escalation logic,
- dispersed multi-agent review/audit for high-risk work.
