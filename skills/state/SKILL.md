---
name: uacp-state-compat
description: Compatibility conductor for UACP state work; delegates to uacp-state.
kind: orchestration
version: 1.0.0
metadata:
  hermes:
    tags: [uacp, state, lifecycle]
    related_skills:
      - uacp-state
      - uacp
---

# UACP State Compatibility

This compatibility conductor exists for agents that look for
`skills/devops/uacp/state/SKILL.md`.

The canonical state skill is:

- `../uacp-state/SKILL.md`

Use the canonical state skill for current pointers, run manifests, governed
state mutation, gate ledgers, and state transition artifacts.
