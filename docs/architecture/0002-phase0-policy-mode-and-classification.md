---
type: adr
status: accepted
---

# Phase 0 — wire filesystem_guard_verified, real policy.mode, classify governed tools

## Metadata

- **Status**: accepted
- **Date**: 2026-05-15
- **Decision Makers**: operator
- **Consulted**: Codex council (technical, governance, skeptic — two passes)
- **Informed**: future-phase implementers

## Context and Problem Statement

Pre-Phase-0 Guardian had three latent enforcement gaps:
1. The `filesystem_guard_verified` flag carried by tool events was not consumed by the kernel — tools claiming containment were trusted without verification.
2. `policy.mode` (enforce vs observe) was a documented setting with no kernel reader.
3. Governed writer tools (`uacp_state_write`, `uacp_doc_write`, etc.) had no Layer A category classification — they routed through the generic `file.write` category and bypassed the governed-tool authorization branch.

## Decision Drivers

- The mechanical-governance thesis: any policy field not read by the kernel is documentation only and doesn't exist.
- Phase 1+ depend on classified governed writers as the substrate for Layer B.
- Observe mode needs to preserve non-waivable invariants (containment, secret boundaries) while downgrading policy-default blocks.

## Considered Options

1. **Wire all three gaps in one phase** — selected. Tight coupling between filesystem guard, mode evaluation, and classification meant splitting them across phases would require throwaway scaffolding.
2. **Defer classification to Phase 1** — rejected; Layer B (Phase 1) cannot be defined without knowing which tools are governed.
3. **Make observe mode bypass all checks** — rejected; non-waivable invariants must hold in observe too.

## Decision Outcome

Chosen option: **Option 1** — wire all three Phase 0 surfaces in one commit.

### Positive Consequences

- `Guardian.evaluate` now reads `filesystem_guard_verified`, `policy.mode`, and per-tool classification.
- `self_attesting_tools` list moved from a hardcoded frozenset in kernel to `config/guardian-policy.yaml#self_attesting_tools.names` (closed the original hidden-authority instance).
- Observe mode downgrades policy-default blocks but preserves non-waivable containment / secret invariants.

### Negative Consequences

- Phase 0 review surfaced 5 material findings (SK-001..SK-004 plus G0-01) that all remediated in-phase.

## Validation

- `scripts/phase0_verify.py` — 14 checks pass.
- `scripts/live_guardian_probe.py` — Guardian decision-flow probes pass (4 unrelated pre-existing failures documented).
- Codex council two-pass review: first pass surfaced material findings; second pass clean.

## Related ADRs

- Builds on: none (foundational).
- Foundation for: [ADR-0003](0003-phase1-gate-ledger-layer-b-piv.md) (Layer B requires classification).

## References

- Implementation commit: `696e184`.
- Kernel: `runtime-adapters/hermes/plugins/uacp_guardian/kernel.py`.
- Policy: `config/guardian-policy.yaml`.
- Verification: `scripts/phase0_verify.py`.
