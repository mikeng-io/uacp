---
name: uacp-heartgate
description: Compatibility conductor for UACP Heartgate transition checks.
version: 1.0.0
metadata:
  hermes:
    tags: [uacp, heartgate, transitions, verification]
    related_skills:
      - uacp
      - uacp-verify
      - uacp-state
---

# UACP Heartgate

This compatibility conductor exists for agents that look for
`skills/devops/uacp/heartgate/SKILL.md`.

Canonical transition authority lives in:

- `config/phase-transitions.yaml`
- `docs/lifecycle/lifecycle-reference.md`
- `../uacp-state/references/heartgate-transition-schema-template.md`

Use `uacp_heartgate_check` where the runtime exposes it. When a transition is
blocked, preserve the blocker as phase evidence and route through the relevant
phase skill instead of bypassing Heartgate.
