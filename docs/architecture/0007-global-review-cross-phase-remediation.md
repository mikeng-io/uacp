---
type: adr
status: accepted
---

# Global review — cross-phase audit and R1/R2 remediation

## Metadata

- **Status**: accepted
- **Date**: 2026-05-17
- **Decision Makers**: operator
- **Consulted**: Codex council (global-scope, three reviewers parallel; R1 + R2 confirmation passes)
- **Informed**: Phase 5 implementer

## Context and Problem Statement

After Phase 4 closed and the patch-plan run reached RESOLVE, the operator requested a final global-scope council audit covering all 5 commits (Phases 0–4 + Resolve) as a single change set — i.e. cross-phase coherence rather than per-phase compliance. Per-phase reviews caught per-phase bypasses; cross-phase bypasses (where Phase X's enforcement is silently broken by Phase Y's addition) require a different review lens.

## Decision Drivers

- Cumulative authority surface area grew significantly across phases (10 governed writer tools, 4 Layer A categories, 18 Heartgate checks).
- Phase 4's stub framework introduced new surfaces (`state/escalations/`) that older code paths weren't updated to recognize.
- The patch-plan thesis ("governance must be mechanical") needs end-to-end validation, not just per-phase.

## Considered Options

1. **Close the patch plan at RESOLVE with no global review** — rejected; per-phase reviews have demonstrated structural blind spots.
2. **Run global review; defer ALL findings to Phase 5** — rejected; many findings were 1-line fixes that should land now.
3. **Run global review; batch high-leverage findings as R1 remediation; defer the rest to Phase 5** — selected.

## Decision Outcome

Chosen option: **Option 3**. Three parallel reviewers returned `pass_with_minor` with 14 high-consensus material findings. R1 batched 10 as in-scope code/config changes; R2 confirmation surfaced 2 small residuals which were closed inline. Remaining findings propagated to Phase 5 with evidence pointers.

### Positive Consequences

- Closed `uacp_phase` enum-validation bypass (SKEP-G-001).
- Closed `state/escalations/` write-laundry via `uacp_state_write` (TECH-G-001).
- Closed `state/current.yaml` pointer-clear and foreign-repoint attacks (SKEP-G-005).
- Generalized PIV per-check pass evidence (SKEP-G-002) — Phase 3 R1's PLAN_VALIDATION pattern now also applies to PIV.
- Doc inventory honest (scripts/ + run-artifact roots now listed).
- Lessons artifact carries explicit bootstrap-posture disclosure.
- plugin.yaml manifest synced with adapter `register_tool` calls.

### Negative Consequences

- Total commits to close patch plan now 7 (Phases 0–4 + Resolve + global review remediation), one more than the original proposal envisioned.
- Several constraints (registry atomicity, kernel readers for `uacp_mode`, structured condition DSL for escalation triggers) explicitly deferred to Phase 5.

## Validation

- All 5 `phaseN_verify` scripts continue to pass after global remediation.
- Codex council R1 returned `pass_with_minor` (10/14 remediated, 4+minor propagated).
- R2 confirmation pass returned `pass_with_minor` with two small residuals.
- R2 inline fixes (phase2_verify PIV seeding + current.yaml bootstrap-vs-clear distinction) closed cleanly.

## Related ADRs

- Builds on: ADRs 0002–0006 (the five phases under review).
- Related: [ADR-0008](0008-doc-structure-and-adr-adoption.md) — the doc restructure was triggered by accumulated doctrine drift identified by this global review.

## References

- R0 review (global): `verification/uacp-patch-plan-20260515-global-review.yaml`.
- R1 remediation commit: `93dba83`.
- R2 residual-fix commit: `da5c15f`.
- Propagated constraints to Phase 5: see global-review YAML's `deferred_to_phase_5_with_evidence_pointer`.
