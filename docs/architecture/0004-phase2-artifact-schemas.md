---
type: adr
status: accepted
---

# Phase 2 — structured artifact schemas with Heartgate enforcement

## Metadata

- **Status**: accepted
- **Date**: 2026-05-15
- **Decision Makers**: operator
- **Consulted**: Codex council (two passes)
- **Informed**: Phase 3+ implementers

## Context and Problem Statement

Phase 1 gave Heartgate mechanical pre-flight machinery. Phase 2 had to declare the **artifact shape** that Heartgate enforces at specific transitions:

- `scope` artifact (PLAN→EXECUTE) — write_paths, blast_radius, rollback_path, cross-checked against Layer B tool capabilities.
- `intent` doc (TRIAGE→PROPOSE) — 4 required sections (Success Definition, Explicit Out-of-Scope, Termination Condition, Authority Source).
- `evidence_disposition` pair files (VERIFY→RESOLVE) — verified-facts + assumptions per non-deferred non-NA cluster.
- `lessons` artifact (VERIFY→RESOLVE) — structured YAML with `ledger_citations`.

## Decision Drivers

- Heartgate cannot enforce what isn't declared in schema.
- Schemas must be config-driven (`config/artifact-schemas.yaml`), not kernel-hardcoded.
- Tool path capabilities (which tool can write which root) must live in config too.

## Considered Options

1. **All four artifact schemas in one phase** — selected.
2. **Schemas in Phase 2, validators in Phase 3** — rejected; the patch-plan thesis is mechanical enforcement, not declaration-only.

## Decision Outcome

Chosen option: **Option 1**. Schemas + Heartgate validators ship together.

### Positive Consequences

- `config/artifact-schemas.yaml` declares the canonical shape for all four artifact classes.
- Heartgate validators (`_validate_scope_artifact`, `_validate_intent_doc`, `_validate_evidence_dispositions`, `_validate_lessons_artifact`) enforce shape + cross-check.
- The `tool_path_capabilities` cross-check verifies every scope.write_paths entry is reachable by an admissible tool.

### Negative Consequences

- Phase 2 review surfaced 3 material findings (F1 wildcard semantics broken, F2 hidden authority list, F3 empty-disposition-file bypass) — all remediated in-phase.

## Validation

- `scripts/phase2_verify.py` — 18 checks pass.
- Codex council two-pass review.

## Related ADRs

- Builds on: [ADR-0003](0003-phase1-gate-ledger-layer-b-piv.md).
- Foundation for: [ADR-0005](0005-phase3-plan-validation-gate-and-run-registry.md).

## References

- Implementation commit: `a0644b0`.
- Config: `config/artifact-schemas.yaml`.
- Kernel validators: `runtime-adapters/hermes/plugins/uacp_guardian/kernel.py` (`_validate_scope_artifact`, `_validate_intent_doc`, `_validate_evidence_dispositions`, `_validate_lessons_artifact`).
