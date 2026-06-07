# 07 — Session Resume Guide

Status: active follow-through package  
Created: 2026-05-12T18:04:59.583598+00:00  
Authority root: `UACP_ROOT`  
Scope: preserve and execute the UACP Agent-Council integration context without relying on chat memory.  

---

## How to resume after context loss

1. Load the `uacp` skill.
2. Read `UACP_ROOT/docs/index.md`.
3. Read this package index: `plans/uacp-agent-council-followthrough/00-index.md`.
4. Read current handoff: `.outputs/agent-skills-integration-current-handoff.md`.
5. Read verification baseline: `verification/uacp-skills-validator-alignment-verify.yaml`.
6. If Kanban tasks exist, use the board/task graph as coordination memory.
7. If Kanban tasks do not exist, create/import from `kanban-import.yaml`.

## Do not rely on

- chat memory,
- line counts as proof of content,
- a single mega-document,
- stale branch docs as authority,
- downstream skills over UACP canonical docs/config.

## First question to ask on resume

```text
Which task is active in the Kanban graph, and what artifact verifies its previous step?
```

## Safe next action if unsure

Run:

```bash
python3 scripts/validate_uacp_artifacts.py --root UACP_ROOT verification/*.yaml
```

Then inspect `plans/uacp-agent-council-followthrough/04-task-breakdown.md` and continue from the first incomplete task.
