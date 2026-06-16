---
name: uacp-guardian
description: Compatibility conductor for UACP Guardian policy and runtime enforcement work.
kind: orchestration
version: 1.0.0
metadata:
  hermes:
    tags: [uacp, guardian, enforcement, runtime]
    related_skills:
      - uacp
      - uacp-state
---

# UACP Guardian

This compatibility conductor exists for agents that look for
`skills/devops/uacp/guardian/SKILL.md`.

Canonical Guardian authority lives in the UACP repository:

- `config/uacp.toml` (`[guardian]` section — policy collapsed from legacy guardian-policy.yaml in Slice 3)
- `config/hooks/terminal/authority-resolution.yaml`
- `docs/runtime/runtime-integration-guide.md`
- `runtime-adapters/hermes/plugins/uacp_guardian/`

For governed state mutation, use:

- `../uacp-state/SKILL.md`

For lifecycle routing, use:

- `../SKILL.md`
