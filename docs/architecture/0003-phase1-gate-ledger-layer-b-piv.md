---
type: adr
status: accepted
---

# Phase 1 — mechanical pre-flight contracts (gate ledger, Layer B, phase exit invariants, PIV)

## Metadata

- **Status**: accepted
- **Date**: 2026-05-15
- **Decision Makers**: operator
- **Consulted**: Codex council (two passes)
- **Informed**: Phase 2+ implementers

## Context and Problem Statement

Phase 0 wired Guardian's per-call enforcement; Phase 1 had to deliver the pre-flight machinery Heartgate needs to validate phase transitions mechanically rather than via prose-only documentation:

- An **append-only gate ledger** so phase transitions and per-phase PIV checks leave durable evidence.
- A **Layer B** per-phase admissibility allowlist so each phase admits only its declared tool set.
- **Phase exit invariants** (artifact glob + gate ledger entry) per phase.
- **PIV (Post-Phase Verification)**: a 5-check self-evaluation run before every transition, max 2 attempts, second-failure block-unconditional.

## Decision Drivers

- Heartgate must be able to refuse a transition based on machine-checkable evidence, not prose.
- The ledger should be tamper-resistant (append-only, exclusive writer) and atomic under O_APPEND.
- Layer B should be config-driven (per-phase allowed_tools / forbidden_tools), not hardcoded.

## Considered Options

1. **Ship all four contracts in one phase** — selected.
2. **Ledger + Layer B in Phase 1; PIV in Phase 2** — rejected; PIV depends on the ledger, and Phase 2 was already scoped to artifact schemas.

## Decision Outcome

Chosen option: **Option 1**. Phase 1 ships the kernel-level machinery; Phase 2 builds the artifact-schema layer on top.

### Positive Consequences

- `uacp_gate_ledger_append` is the exclusive writer for `state/gate-ledger/{run_id}.jsonl`.
- Layer B's per-phase allowed_tools / forbidden_tools is enforced in `Guardian._phase_layer_check`, reading `config/phase-transitions.yaml`.
- Phase exit invariants and PIV records are enforced by Heartgate validators.
- The PIPE_BUF (3584-byte) atomicity bound is established for append-only JSONL ledgers.

### Negative Consequences

- Phase 1 review surfaced 7 material findings (gate-ledger forge bypass via uacp_state_write, malformed config crash paths, etc.) — all remediated in-phase.

## Validation

- `scripts/phase1_verify.py` — 23 checks pass.
- Codex council two-pass review.

## Related ADRs

- Builds on: [ADR-0002](0002-phase0-policy-mode-and-classification.md).
- Foundation for: [ADR-0004](0004-phase2-artifact-schemas.md), [ADR-0005](0005-phase3-plan-validation-gate-and-run-registry.md).

## References

- Implementation commit: `49d8929`.
- Kernel: `runtime-adapters/hermes/plugins/uacp_guardian/kernel.py` (`_validate_phase_exit_invariants`, `_validate_piv_record`).
- Adapter: `runtime-adapters/hermes/plugins/uacp_guardian/__init__.py` (`_handle_uacp_gate_ledger_append`).
- Config: `config/phase-transitions.yaml#stages` (Layer B), `config/phase-transitions.yaml#piv_rule`.
