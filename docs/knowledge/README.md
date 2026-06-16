# UACP Knowledge

Durable run-lessons, design rationale, and history — relocated from the former
`skills/references/` shared dump (abolished in the skill-convention application,
ADR-0017 / Step 2 Slice 3).

**Not skill-citable.** Skills must reference only files that ship with a skill
(their own `references/`, or `uacp-core/references/`). These knowledge docs are for
human and agent *reading* and *provenance*, not skill instruction prose. Operational
contracts that a skill needs live under `uacp-core/references/`, not here.

## Index

- [agent-council-integration-and-operationalization-lessons.md](agent-council-integration-and-operationalization-lessons.md) — Split-plan shape, cognitive-plane anti-patterns, phase-local granularity fields, surface taxonomy, skill/validator propagation, and PLAN→EXECUTE checklist for Agent Council work.
- [filesystem-containment-phase-lessons.md](filesystem-containment-phase-lessons.md) — Evidence-vs-execution distinction, boundary-correction principle, bwrap design, write-probe requirement, Heartgate YAML shape, and 10-step phase-start sequence for filesystem containment phases.
- [hermes-adapter-porting-and-cleanup-lessons.md](hermes-adapter-porting-and-cleanup-lessons.md) — UACP adapter ownership direction, hermes_symlink_plugin_probe.py invocation, dirty-state precheck, branch-verification checklist, deferred-action boundary, and stale-gate-task resolution for Hermes porting work.
- [kanban-guard-and-closure-lessons.md](kanban-guard-and-closure-lessons.md) — 7-step closure evidence pattern, workspace-separation boundary, completion metadata field list, completion_blocked_uacp_metadata event, 5-case verification shape, and non-goals for Kanban guard phases.
