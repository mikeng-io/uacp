---
type: index
tags: [index, reference, schema, spec]
status: living-document
---

# Reference Specs — Index

Canonical schemas and per-skill authority records. These are the machine-readable surfaces that Heartgate and Guardian consume; this directory is the human-readable mirror.

## Documents

| File | Purpose |
|---|---|
| [proposal-schema.md](proposal-schema.md) | Canonical reference for the `uacp.propose` artifact (fields, semantics, validation rules, routing-outcome examples). |
| [skill-enforcement-spec.md](skill-enforcement-spec.md) | Per-skill authority record: allowed_tools, forbidden_tools, write surfaces, PIV obligations, mechanical-enforcement table. |
| [lifecycle-trace-table.md](lifecycle-trace-table.md) | Per-transition table (TRIAGE→…→RESOLVE) listing required inputs, required outputs, Heartgate checks, gate-ledger entry. Cross-phase dependency graph. |
| [operator-phase-return-schema.md](operator-phase-return-schema.md) | Presentation contract for Telegram/Discord phase returns: conclusion-first summaries with evidence pointers, not raw data dumps. |

## Related

- Foundational policy: [`../policy/`](../policy/INDEX.md).
- Runtime enforcement of these specs: [`../runtime/runtime-enforcement.md`](../runtime/runtime-enforcement.md).
- Artifact schemas (codified): `engines/domain/artifact_schema.py` (`artifact_schemas_dict()`; `config/artifact-schemas.yaml` deleted Slice 5). Phase-transition doctrine + operator knobs: `config/phase-transitions.yaml` (gate-rule grammar codified to `engines/domain/gate_rules.py` Slice 4b). Autonomy/mode policy: `config/uacp.toml [autonomy]` (collapsed from legacy autonomy-policy.yaml in Slice 3). Guardian policy: `config/uacp.toml [guardian]` (collapsed from legacy guardian-policy.yaml in Slice 3).
