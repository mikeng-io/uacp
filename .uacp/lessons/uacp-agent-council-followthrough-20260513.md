---
type: lesson
id: uacp-agent-council-followthrough-20260513
title: UACP Agent Council Follow-through — Run Lessons
project: uacp
domains: [uacp, orchestration, kanban, delegate_task, agent_council, verification, guardian, heartgate, validation, state_mutation, runtime_enforcement, audit, evidence_registry]
invariants: []
affected_paths: []
severity: MEDIUM
source_run: uacp-agent-council-followthrough-20260513
extracted_at: "2026-05-12T20:52:40.809671+00:00"
eligible: 0
recurrences: 0
bes: 0.5
promoted_to: null
tags: [agent-council, delegate-task, guardian, heartgate, kanban]
---

# UACP Agent Council Follow-through — Run Lessons

Converted verbatim from `uacp-agent-council-followthrough-20260513.yaml` (kind `uacp.lesson`, schema_version 0.1) in the #110 corpus-parseability
migration — the OKF frontmatter above is derived metadata; the original document is preserved
in full below.

```yaml
schema_version: "0.1"
kind: uacp.lesson
lesson_id: "uacp-agent-council-followthrough-20260513"
source_run: "uacp-agent-council-followthrough-20260513"
created_at: "2026-05-12T20:52:40.809671+00:00"
lessons:
  - id: L1
    summary: "For UACP design follow-through, main-session execution can be safer than Kanban worker dogfood while worker crash/protocol behavior is unresolved."
    applies_to: [uacp, orchestration, kanban]
  - id: L2
    summary: "delegate_task with GPT-5.4-mini is useful for bounded role-framed critique, but final authority still requires orchestrator synthesis and council artifacting."
    applies_to: [delegate_task, agent_council, verification]
  - id: L3
    summary: "Manual-drill validator improvements are useful, but production Guardian/Heartgate claims need runtime proof and stronger schemas."
    applies_to: [guardian, heartgate, validation]
  - id: L4
    summary: "Any local write bypass caused by missing UACP context fields must be recorded as accepted risk or blocker, never normalized as the runtime path."
    applies_to: [state_mutation, runtime_enforcement, audit]
  - id: L5
    summary: "Evidence-Domain Registry selector design must remain visibly not runtime-active until selector fixtures and Heartgate consumption are verified."
    applies_to: [evidence_registry, verification]
recommended_future_runs:
  - "Runtime Guardian/Heartgate live proof and uacp_state_write lifecycle wiring."
  - "Validator fixture/schema hardening run."
  - "Evidence-Domain Registry selector implementation run."
  - "Downstream agent-skills extraction run."
```
