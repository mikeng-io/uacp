---
type: adr
title: Phase 4 — uacp_mode, autonomy-policy, escalation-event stub
description: Wire the operating-mode framework (uacp_mode field, autonomy-policy config, escalation-event tool) as honest stubs ahead of Phase 5 kernel activation.
tags: [autonomy, escalation, uacp-mode, stub]
timestamp: 2026-05-16
status: accepted
---

# Phase 4 — uacp_mode, autonomy-policy, escalation-event stub

## Metadata

- **Status**: accepted
- **Date**: 2026-05-16
- **Decision Makers**: operator
- **Consulted**: Codex council (two passes — R0 / R1)
- **Informed**: Phase 5 implementer

## Context and Problem Statement

Phases 0–3 hardened the static-governance plane. Phase 4 introduces the **operating-mode framework** as a stub for the Phase 5 full autonomous-mode landing. The mandate was deliberately limited to wiring (schema fields, config surface, tool registration) without kernel readers — Phase 5 will activate the behavior.

- **Item 4.1**: `uacp_mode` field in state schema (manual | semi_auto | supervised_auto | full_auto).
- **Item 4.2**: `config/autonomy-policy.yaml` — operating modes, escalation trigger registry, canonical_state_paths, advisory_field_convention.
- **Item 4.3**: mode_behavior stubs in all 7 SKILL.md files.
- **Item 4.4**: `uacp_escalation_event` tool stub writing JSONL to `state/escalations/{run_id}.jsonl`.

## Decision Drivers

- Phase 5 requires the operating-mode framework to be wired (tool registration, schema, layer A/B coverage) before kernel readers can land.
- Operator wants the framework available for documentation/skill consultation even before activation.
- The R0 council surfaced that the patch plan's foundational thesis ("governance must be mechanical") risked being violated by decorative YAML fields. R1 introduced `enforcement_status: stub_only_phase_4` tagging on every decorative block.

## Considered Options

1. **Ship wiring only, defer behavior to Phase 5** — selected, with explicit `enforcement_status` honesty tagging.
2. **Ship wiring + minimal kernel readers** — rejected; the mode-aware readers are non-trivial and would have expanded Phase 4 scope beyond the stub mandate.

## Decision Outcome

Chosen option: **Option 1**. Phase 4 ships honest stubs.

### Positive Consequences

- `uacp_escalation_event` is registered and enforces UACP context, required mode field, severity/mode enums, PIPE_BUF bound, embedded-newline refusal, escalations-dir containment.
- `autonomy-policy.yaml` declares the four modes, seven escalation triggers, canonical_state_paths, and the `_advisory` suffix convention — every decorative block carries `enforcement_status: stub_only_phase_4`.
- The drift-reconciliation YAML uses honest classification keys (REMEDIATED_IN_PHASE_4 / DEFERRED_TO_PHASE_5 / DOCUMENTED_NOT_ENFORCED).

### Negative Consequences

- Phase 4's framework is honestly labeled "documentation-only" until Phase 5 lands kernel readers; an inattentive operator could mistake stub for production.
- 17 propagated constraints (pc_p3_*) inherited from Phase 3 partially remediated; 8 deferred to Phase 5.

## Validation

- `scripts/phase4_verify.py` — 20 checks pass (14 original + 6 R1 honesty checks).
- Codex council two-pass review: see `verification/uacp-patch-plan-20260515-phase4-codex-review.yaml`.

## Related ADRs

- Builds on: [ADR-0005](0005-phase3-plan-validation-gate-and-run-registry.md).
- Foundation for: future Phase 5 ADR (not yet authored).

## References

- Implementation commit: `3c48406`.
- Config: `config/autonomy-policy.yaml`, `config/state.yaml#current_pointer_schema.fields.uacp_mode`, `config/state.yaml#escalations`.
- Adapter: `runtime-adapters/hermes/plugins/uacp_guardian/__init__.py` (`_handle_uacp_escalation_event`).
- Phase 5 reserved-slot doc: [`../plans/phase5-reserved-slot.md`](../plans/phase5-reserved-slot.md).
