---
name: uacp-heartgate
description: Compatibility conductor for UACP Heartgate transition checks.
kind: orchestration
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

- `../uacp-core/scripts/engines/domain/phase_graph.py` — codified valid transitions (`LIFECYCLE_GRAPH`)
- `../uacp-core/scripts/engines/domain/gate_rules.py` — codified gate/rule grammar (heartgate_coherence required fields/lenses, run_registry, piv_rule)
- `config/uacp.toml` (`[heartgate.*]` — operator-tunable coherence thresholds and enforcement mode)
- `config/phase-transitions.yaml` (LLM-read adaptive-gate doctrine + artifact schemas; transition graph and gate grammar above are now code-authoritative)
- `docs/lifecycle/lifecycle-reference.md`
- `../uacp-state/references/heartgate-transition-schema-template.md`

Use `uacp_heartgate_check` where the runtime exposes it. When a transition is
blocked, preserve the blocker as phase evidence and route through the relevant
phase skill instead of bypassing Heartgate.
