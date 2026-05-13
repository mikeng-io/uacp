# Agent-Skills Branch → UACP Integration Package

Status: draft split planning package  
Mode: manual UACP drill, not fully automated lifecycle enforcement  
Source branch: `mikeng-io/agent-skills` → `origin/codex/guardian-agent-council-uacp`  
UACP root: `UACP_ROOT`  
Prepared for: Mike / Norty

---

## 4. Proposed Canonical Document Changes

### 4.1 New document: `docs/orchestration-model.md`

Recommended new canonical doc.

Role:

- define Agent Council
- define council modes
- define council tiers
- define granularity vs tier
- define runtime, runtime adapter, runtime contract
- define diversity dimensions
- define DA / IC roles
- define relationship to UACP phases
- state deprecation of deep-* wrapper doctrine

Why new doc instead of stuffing into lifecycle-reference:

- The concepts are bigger than lifecycle phase text.
- It avoids bloating `docs/lifecycle-reference.md`.
- It gives agent-skills a clear downstream source to implement.

### 4.2 Update: `docs/index.md`

Changes:

- add `docs/orchestration-model.md` to inventory
- add decision log entry for branch-to-UACP doctrine integration
- note that agent-skills branch is source material, not canonical authority

### 4.3 Update: `docs/lifecycle-reference.md`

Changes:

- clarify how each phase can invoke Agent Council
- add granularity vs council-tier distinction
- add manual lifecycle drill note if appropriate
- add finding-driven VERIFY pattern summary

### 4.4 Update: `docs/runtime-enforcement.md`

Changes:

- clarify Guardian Core + Policy Packs + Runtime Adapters
- mention Trustless ACP policy compatibility
- define runtime adapters as UACP-facing/downstream boundary components
- clarify Hermes-first but not Hermes-only

### 4.5 Update: `config/review-routing.yaml`

Changes:

- add default mapping from UACP granularity/risk to council tier
- add override triggers for tier escalation
- add diversity dimensions as routing factors

### 4.6 Update: `config/evidence-clusters.yaml`

Changes:

- add migration note toward Evidence-Domain Registry
- possibly add domain bindings as seed structure
- avoid full merge until current domain-registry shape is reviewed in detail

---
