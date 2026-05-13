# 06 — Verification And Measurement Gates

Status: active follow-through package  
Created: 2026-05-12T18:04:59.583598+00:00  
Authority root: `UACP_ROOT`  
Scope: preserve and execute the UACP Agent-Council integration context without relying on chat memory.  

---

## Gate model

Each task has local acceptance checks. The package also has cross-task measurement gates.

## Gate G1 — YAML/config parse

Command:

```bash
python3 scripts/validate_uacp_artifacts.py --root UACP_ROOT verification/*.yaml
```

Pass:

- validator returns `RESULT PASS` or expected bounded `RESULT WARN`.
- no `RESULT BLOCK`.

## Gate G2 — Schema coverage

Measure:

- phase transition schema includes `phase_local_granularity`, `composite_granularity`, `human_involvement`, `council_synthesis_artifact`.
- council synthesis schema includes mode/tier/roles/dispatch surfaces/findings/verdict.

Pass:

- missing required fields are reported by validator as BLOCK.

## Gate G3 — Cognitive separation drift

Search targets:

- Kanban described as phase state or deliberation engine.
- Agent Council described as durable task store.
- tool/evidence services described as autonomous authority.
- unqualified `deep council` used as canonical doctrine.

Pass:

- no canonical doc/skill violates the cognitive model.

## Gate G4 — Adapter classification coverage

Measure:

- each execution/evidence surface has a class: `agent_runtime`, `tool_adapter`, `evidence_service`, or `control_substrate`.
- each class has authority, side-effect, provenance, and audit requirements.

Pass:

- no adapter is introduced without classification.

## Gate G5 — Human involvement routing

Measure:

- tasks/artifacts record human involvement decision fields.
- HIGH/CRITICAL unresolved findings require human acceptance or block.

Pass:

- no protected action proceeds without authority.

## Gate G6 — Evidence-Domain Registry honesty

Pass:

- `implementation_status` remains `not_runtime_active` until selector exists and is verified.
- verification artifacts never claim runtime implementation when only direction is captured.

## Gate G7 — Council review before RESOLVE

Pass:

- final council review artifact exists,
- no unresolved HIGH/CRITICAL finding remains without explicit accepted risk,
- final RESOLVE artifact links to all task outputs and verification gates.


## Gate G8 — Profile/persona routing

Pass:

- council roles are mapped to explicit execution profile requirements when profile choice affects quality, permissions, or confidence.
- profile-local instructions are downstream of UACP canonical docs/config.
- profile diversity is considered as a routing dimension alongside model/runtime/tool diversity.
