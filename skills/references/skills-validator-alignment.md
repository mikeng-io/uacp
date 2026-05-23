# UACP Skills + Artifact Validator Alignment

Use when UACP canonical docs/config have changed and the executable skill layer may be stale.

## Trigger

Run this alignment workflow after changes to:

- lifecycle semantics or phase-transition schema,
- Agent Council / Kanban / runtime/tool/evidence adapter doctrine,
- phase-local or composite granularity,
- human involvement routing,
- council synthesis artifact shape,
- Evidence-Domain Registry status,
- Guardian/Heartgate artifact requirements.

## Phase-first workflow

Do not patch docs, skills, and validators ad hoc in one stream. Use a whole phased plan, then execute phase by phase:

1. **Phase 0 — Inventory and plan**
   - Inspect canonical docs/config and currently loaded UACP lifecycle skills.
   - Write a bounded phased plan naming targets, acceptance checks, and deferred runtime work.
2. **Phase 1 — Skill alignment**
   - Patch lifecycle skills and shared lifecycle contract to implement the new doctrine.
   - Skills should point back to canonical docs/config, not redefine doctrine.
3. **Phase 2 — Lightweight validation**
   - Add or update a validator script for manual-drill artifact sanity.
   - Keep it lightweight unless strict schemas are explicitly approved.
4. **Phase 3 — Verification**
   - Parse YAML, run validator, search for stale terminology, and write a verification artifact.
5. **Phase 4 — Runtime hardening handoff**
   - Defer Guardian/Heartgate production wiring, adapter manifests, and strict schema systems unless explicitly in scope.

## Skill alignment checklist

Every lifecycle skill should account for these fields when relevant:

```yaml
phase_local_granularity:
  phase: triage | propose | plan | execute | verify | resolve
  entry_estimate: 1-10
  exit_actual: 1-10
  delta_reason: ""
  downstream_projection: {}
composite_granularity: 1-10
human_involvement:
  required: true | false
  reason: ""
  authority_needed: ""
  decision_owner: ""
  accepted_risk_artifact: ""
```

Skills should preserve the cognitive separation:

- UACP = governance cognition.
- Agent Council = deliberative orchestration.
- Kanban = coordination memory.
- Runtimes/tool adapters/evidence services = bounded work or observation.
- Guardian/Heartgate = boundary enforcement.

## Validator scope

A lightweight UACP validator should check at minimum:

- core config YAML parses,
- phase-transition artifacts include required fields from `config/phase-transitions.yaml`,
- council synthesis artifacts include required fields from `council_synthesis_schema`,
- finding states are canonical only: `open`, `resolved`, `accepted_risk`, `not_applicable`, `deferred`,
- Evidence-Domain Registry is not reported as runtime-active while `implementation_status: not_runtime_active`.

Use `scripts/validate_uacp_artifacts.py` in this skill package as a starter validator script.

## Pitfalls

- Do not leave lifecycle skills stale after canonical docs/config move forward.
- Do not treat a config seed/stub as implemented runtime behavior.
- Do not let a validator become a hidden authority source; it implements canonical docs/config.
- Do not harden session-specific bypasses into normal workflow. Record manual-drill bypasses as accepted risk or blockers depending on severity.
