# Agent-Skills Branch → UACP Integration Package

Status: draft split planning package  
Mode: manual UACP drill, not fully automated lifecycle enforcement  
Source branch: `mikeng-io/agent-skills` → `origin/codex/guardian-agent-council-uacp`  
UACP root: `UACP_ROOT`  
Prepared for: Mike / Norty

---

## 0. Purpose

This document captures the plan, requirements, and design for integrating the newly created concepts from the `agent-skills` branch into UACP.

The goal is not to copy the branch wholesale. The goal is to make UACP the canonical doctrine and later re-extract a cleaner agent-skills implementation from that stabilized doctrine.

UACP is currently treated as partially broken / not fully self-enforcing, so this work will be run as a **manual UACP drill**:

```text
TRIAGE -> PROPOSE -> PLAN -> EXECUTE -> VERIFY -> RESOLVE
```

The lifecycle will be followed manually and honestly. We will not claim Guardian/Heartgate automation is fully reliable until it is proven.

---

## 1. Ground Truth Inputs

### 1.1 Agent-skills branch

Branch inspected by native Hermes subagents only:

```text
/home/norty/workspace/agent-skills
origin/codex/guardian-agent-council-uacp
```

Observed scale:

- 48 files changed
- approximately +4265 / -4871 lines

Major branch changes:

- `bridge-*` renamed to `runtime-*`
- `bridge-commons` renamed to `runtime-contracts`
- standalone `deep-council` deleted
- `agent-council` becomes the unified council/orchestration surface
- council depth becomes tiered: Tier 0 / 1 / 2 / 3
- new `guardian` skill added
- `council-taxonomy` becomes the glossary anchor inside agent-skills
- `deep-review`, `deep-audit`, `deep-verify`, and `deep-research` become thin wrappers over `agent-council`
- new runtime adapter family appears: `runtime-claude`, `runtime-codex`, `runtime-gemini`, `runtime-opencode`, `runtime-kimi`

### 1.2 Current UACP

Current UACP source of truth inspected:

```text
UACP_ROOT/docs/index.md
UACP_ROOT/docs/constitution.md
UACP_ROOT/docs/lifecycle-reference.md
UACP_ROOT/docs/runtime-enforcement.md
UACP_ROOT/config/*.yaml
UACP_ROOT/state/current.yaml
UACP_ROOT/state/runs/
```

Current UACP already defines:

- lifecycle: `TRIAGE -> PROPOSE -> PLAN -> EXECUTE -> VERIFY -> RESOLVE`
- document authority chain
- file-based YAML state model
- `uacp-state` as governed state mutator
- Guardian + Heartgate as runtime enforcement concepts
- review routing
- evidence clusters
- Kanban binding as execution substrate, not phase state

Current UACP is missing or ambiguous on:

- formal council taxonomy
- exact meaning of `agent council`
- exact meaning of `deep council`
- runtime adapter vocabulary
- council tier model
- Devil's Advocate role
- Integration Checker role
- finding-driven review / verification mode
- packetized council exchange
- relationship between domain registry and evidence clusters

---
