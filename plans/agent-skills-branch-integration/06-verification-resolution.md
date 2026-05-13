# Agent-Skills Branch → UACP Integration Package

Status: draft split planning package  
Mode: manual UACP drill, not fully automated lifecycle enforcement  
Source branch: `mikeng-io/agent-skills` → `origin/codex/guardian-agent-council-uacp`  
UACP root: `UACP_ROOT`  
Prepared for: Mike / Norty

---

## 6. Open Questions

### Q1. Name of new doc

Recommended: `docs/orchestration-model.md`

Alternative: `docs/council-taxonomy.md`

Current recommendation is `orchestration-model` because the scope includes more than taxonomy.

### Q2. Should UACP use the word `council` for all multi-agent orchestration?

Proposed answer:

- Use `Agent Council` for orchestration primitive.
- Use `council mode` for purpose.
- Use `council tier` for depth.

### Q3. Should deep-* wrappers be deleted immediately downstream?

Proposed answer:

- Not immediately.
- First mark them compatibility/deprecated.
- Remove after UACP-derived agent-council is stable.

### Q4. Should Evidence-Domain Registry become a new config file?

Possible future file:

```text
config/evidence-domain-registry.yaml
```

But for the first pass, update existing `config/evidence-clusters.yaml` with direction only to avoid config sprawl.

---

## 7. Downstream Agent-Skills Extraction Plan

After UACP doctrine is patched and verified:

1. Rebuild `agent-council` around UACP definitions.
2. Make `council-taxonomy` derive from `docs/orchestration-model.md`.
3. Merge Guardian concepts so agent-skills Guardian becomes:
   - Guardian Core wrapper
   - runtime adapter hooks
   - policy-pack loader
4. Rename or remove `bridge-*` vocabulary.
5. Deprecate deep-* wrappers as compatibility aliases.
6. Make artifact paths configurable through symbolic roots:
   - `UACP_ROOT/verification/`
   - `UACP_ROOT/outputs/`
   - `ARTIFACT_ROOT/`
   - runtime-specific fallback roots only when configured.
7. Keep runtime adapters as downstream implementation, not UACP canonical docs.

---

## 8. Risks

### R1. Two-source doctrine drift

Risk: agent-skills and UACP evolve separately again.

Mitigation:

- UACP canonical docs win.
- agent-skills branch is source material only until re-extracted.

### R2. Overfitting to Hermes

Risk: UACP doctrine accidentally bakes in Hermes runtime details.

Mitigation:

- use runtime-neutral vocabulary
- describe Hermes as first host, not boundary

### R3. Over-creating docs

Risk: too many UACP docs create more drift.

Mitigation:

- one new orchestration doc only if approved
- otherwise fold content into existing docs

### R4. Premature code port

Risk: implementation code is ported before doctrine is stable.

Mitigation:

- no Guardian code / hook code / runtime adapter code in first patch
- do not port `guardian.py`, adapter scripts, or branch implementation code until the UACP doctrine stabilizes and the later implementation phase is explicitly approved

### R5. Path syntax confusion

Risk: `$UACP_ROOT`, `$$UACP_ROOT`, and symbolic roots get mixed.

Mitigation:

- canonical docs use `UACP_ROOT/path`
- shell examples use `"$UACP_ROOT/path"`

---
