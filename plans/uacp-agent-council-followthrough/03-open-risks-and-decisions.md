# 03 — Open Risks And Decisions

Status: active follow-through package  
Created: 2026-05-12T18:04:59.583598+00:00  
Authority root: `UACP_ROOT`  
Scope: preserve and execute the UACP Agent-Council integration context without relying on chat memory.  

---

## Open risks

### R1 — Runtime enforcement gap

The manual validator exists, but Guardian/Heartgate production wiring is still deferred. `execute_code`/shell-like bypasses must remain HIGH accepted risk or blocker depending on context.

### R2 — Evidence-Domain Registry is not runtime-active

`config/evidence-clusters.yaml` contains a seed merge target, not an implemented selector.

### R3 — Adapter taxonomy is doctrinal but not implemented

Runtimes, tool adapters, evidence services, and control substrates are conceptually separated, but there is no complete manifest/registry implementation yet.

### R4 — Kanban graph not created yet

This package defines the graph. It still needs to be created in the active Kanban board/tooling or imported later.

### R5 — Downstream agent-skills extraction may drift

Downstream extraction must follow stabilized UACP and must not redefine doctrine.

## Open decisions

1. Should `scripts/validate_uacp_artifacts.py` remain a manual drill helper or become a Guardian/Heartgate dependency?
2. Should UACP use JSON Schema for artifacts, or keep YAML seed schemas plus lightweight Python validation?
3. What is the minimum adapter manifest for a tool/evidence service to be allowed in UACP EXECUTE/VERIFY?
4. Which Kanban board slug should own this follow-through? Default proposed: `uacp`.
5. Should the downstream agent-skills extraction happen in this repo first or in `mikeng-io/agent-skills` branch/worktree after UACP stabilizes?

## Non-goals for immediate work

- Do not port branch implementation code yet.
- Do not claim Evidence-Domain Registry selector exists.
- Do not claim production Guardian enforcement.
- Do not hardcode provider/model names into UACP doctrine.
