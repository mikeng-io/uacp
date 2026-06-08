---
name: uacp-lifecycle
description: Compatibility conductor for UACP lifecycle work; routes to the phase-specific UACP skills.
version: 1.0.0
metadata:
  hermes:
    tags: [uacp, lifecycle, governance, routing]
    related_skills:
      - uacp
      - uacp-triage
      - uacp-propose
      - uacp-plan
      - uacp-execute
      - uacp-verify
      - uacp-resolve
      - uacp-state
---

# UACP Lifecycle

This compatibility conductor exists for agents that look for
`skills/devops/uacp/lifecycle/SKILL.md`.

The canonical lifecycle phase skills are siblings of this directory:

- `../uacp-triage/SKILL.md`
- `../uacp-propose/SKILL.md`
- `../uacp-plan/SKILL.md`
- `../uacp-execute/SKILL.md`
- `../uacp-verify/SKILL.md`
- `../uacp-resolve/SKILL.md`
- `../uacp-state/SKILL.md`

Read the parent router first:

- `../SKILL.md`

Use lowercase phase names for runtime artifacts: `triage`, `propose`, `plan`,
`execute`, `verify`, and `resolve`.
