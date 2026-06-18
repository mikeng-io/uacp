---
type: adr
title: Phase 3 — plan_validation_gate, run_registry, authority docs
description: Add the plan-validation pre-flight gate, a run registry for concurrent-run write-path overlap detection, and three canonical authority docs.
tags: [heartgate, run-registry, plan-validation, authority]
timestamp: 2026-05-15
status: accepted
---

# Phase 3 — plan_validation_gate, run_registry, authority docs

## Metadata

- **Status**: accepted
- **Date**: 2026-05-15
- **Decision Makers**: operator
- **Consulted**: Codex council (three passes — R0 / R1 / R2)
- **Informed**: Phase 4 implementer

## Context and Problem Statement

Phases 0–2 built the per-call and per-transition enforcement floor. Phase 3 had to add two new gate categories and the documentation layer that explains them:

- **plan_validation_gate** — a structural pre-flight at PLAN→EXECUTE. Six checks (pv_1..pv_6) declared in config; a `PLAN_VALIDATION` ledger entry must precede the transition.
- **run_registry** — `state/run-registry.yaml` records active runs; Heartgate detects write-path overlap at PLAN→EXECUTE between concurrent runs.
- **Three canonical authority docs** — skill-enforcement-spec, proposal-schema, lifecycle-trace-table.
- **Phase 2 propagated constraints** — pc_p2_n1, n2, t3, t4, t5, minor.

## Decision Drivers

- PLAN must self-certify before EXECUTE may begin (defense-in-depth against PLAN→EXECUTE shortcuts).
- Concurrent runs must not silently clobber each other's write surfaces (Phase 4 autonomous mode prerequisite).
- The skill→config→spec authority chain must be explicitly documented to prevent doctrine drift.

## Considered Options

1. **plan_validation_gate as a ledger entry + run_registry as a YAML file** — selected.
2. **plan_validation_gate as a Heartgate-internal check, no ledger** — rejected; the ledger entry is necessary for auditability across runs.

## Decision Outcome

Chosen option: **Option 1**. Phase 3 ships the four items above; the R0+R1+R2 council review iterations harden each against bypass attempts.

### Positive Consequences

- `_validate_plan_validation_gate` enforces ledger_required_fields, ledger_required_phase, and per-check pass evidence (the R1 hardening generalized from SKEP-001).
- `_validate_run_registry_overlap` uses PurePosixPath segment normalization (R1 fix to SKEP-003 bypass).
- `uacp_run_registry_update` is the exclusive registry mutator with caller-binding (`entry.run_id == caller.uacp_run_id`).
- `docs/reference/skill-enforcement-spec.md`, `docs/reference/proposal-schema.md`, `docs/reference/lifecycle-trace-table.md` codify the authority chain.

### Negative Consequences

- Phase 3 required three review iterations (R0 surfaced 14 findings, R1 surfaced 10 more, R2 confirmed pass). The high finding count reflected new surface area, not implementation quality.
- The two-pass Codex protocol was upgraded to three-pass for phases that introduce a new enforcement category.

## Validation

- `scripts/phase3_verify.py` — 30 checks pass (12 added in R1 to lock in the new contract).
- Codex council three-pass review: see `verification/uacp-patch-plan-20260515-phase3-codex-review.yaml`.

## Related ADRs

- Builds on: [ADR-0004](0004-phase2-artifact-schemas.md).
- Foundation for: [ADR-0006](0006-phase4-autonomous-mode-stub.md).

## References

- Implementation commit: `bee42cd`.
- Config: `config/phase-transitions.yaml#plan_validation_gate`, `config/phase-transitions.yaml#run_registry_rule`, `config/artifact-schemas.yaml#run_registry`.
- Kernel: `runtime-adapters/hermes/plugins/uacp_guardian/kernel.py` (`_validate_plan_validation_gate`, `_validate_run_registry_overlap`).
- Adapter: `runtime-adapters/hermes/plugins/uacp_guardian/__init__.py` (`_handle_uacp_run_registry_update`).
