# 05 — Kanban Delegation

Status: active follow-through package  
Created: 2026-05-12T18:04:59.583598+00:00  
Authority root: `UACP_ROOT`  
Scope: preserve and execute the UACP Agent-Council integration context without relying on chat memory.  

---

## Board

Proposed board slug: `uacp`

## Root task

Title: `UACP Agent-Council Integration — Runtime/Validator Follow-through`

Description should link:

- `plans/uacp-agent-council-followthrough/00-index.md`
- `plans/uacp-skills-and-validator-alignment-phased-plan.md`
- `outputs/agent-skills-integration-current-handoff.md`
- `verification/uacp-skills-validator-alignment-verify.yaml`

## Child task dependency graph

```text
ROOT
├── T1 validator-hardening
├── T2 guardian-heartgate-validator-wiring-design  (depends on/consumes T1)
├── T3 agent-council-kanban-task-templates
├── T4 runtime-tool-evidence-adapter-manifest
├── T5 evidence-domain-registry-selector           (depends on/consumes T4)
├── T6 downstream-agent-skills-extraction-plan     (consumes T1-T5)
└── T7 final-council-review-and-resolve            (depends on T1-T6)
```

## Kanban import manifest

Machine-readable manifest is stored at:

`plans/uacp-agent-council-followthrough/kanban-import.yaml`

## Dispatch rules

- Kanban is coordination memory only.
- UACP phase state remains in UACP artifacts/state.
- Each task must include authority artifact, allowed files, forbidden files, verification, rollback/stop condition, and expected deliverable.
- Human involvement is required before irreversible external side effects or production Guardian enforcement changes.

## Created Kanban tasks

Board: `uacp`

- `ROOT` → `t_c4d15164`
- `T1` → `t_cc7735d5`
- `T2` → `t_fa9357e5`
- `T3` → `t_48f4cad3`
- `T4` → `t_91edad52`
- `T5` → `t_7bb7c078`
- `T6` → `t_afb883aa`
- `T7` → `t_a3505386`

Created map: `plans/uacp-agent-council-followthrough/kanban-created.yaml`
