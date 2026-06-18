---
type: index
tags: [index, lifecycle, orchestration]
status: living-document
---

# Lifecycle — Index

The six-phase UACP lifecycle (**TRIAGE → PROPOSE → PLAN → EXECUTE → VERIFY → RESOLVE**) and the orchestration model that animates it.

## Documents

| Doc | Type | Purpose |
|---|---|---|
| [lifecycle-reference.md](lifecycle-reference.md) | spec | Canonical phase semantics, transition rules, coordination-adapter binding contract. |
| [orchestration-model.md](orchestration-model.md) | spec | Cognitive planes (governance / deliberation / coordination / execution), Agent Council protocol, profile/runtime separation, escalation semantics. |
| [worktree-protocol.md](worktree-protocol.md) | spec | Workspace isolation rules preventing active runs from writing to main/master; workspace kinds and lifetimes. |

## Related

- Cross-phase artifact dependencies: [`../reference/lifecycle-trace-table.md`](../reference/lifecycle-trace-table.md).
- Per-phase enforcement: [`../runtime/runtime-enforcement.md`](../runtime/runtime-enforcement.md).
- Phase 5 (full autonomous mode) planning: [`../plans/phase5-reserved-slot.md`](../plans/phase5-reserved-slot.md).
