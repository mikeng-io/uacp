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

## Related

- Foundational policy: [`../policy/`](../policy/INDEX.md).
- Runtime enforcement of these specs: [`../runtime/runtime-enforcement.md`](../runtime/runtime-enforcement.md).
- Schemas in YAML form: `config/artifact-schemas.yaml`, `config/phase-transitions.yaml`, `config/guardian-policy.yaml`, `config/autonomy-policy.yaml`.
