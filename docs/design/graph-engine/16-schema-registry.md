---
type: contract
title: Graph Engine — Schema Registry (uacp-schema)
description: The schema-first doctrine (every YAML validated, closed-world, enums), the foundational uacp-schema package, the audited as-is coverage (mostly absent), and the schema catalog to define.
tags: [graph-engine, schema, validation, uacp-schema, contract]
timestamp: 2026-06-19
edges:
  - {dst: 10-edge-schema, rel: realizes, provenance: asserted}
---

# Schema Registry — `uacp-schema` (contract)

## Doctrine (D9)

Every YAML in the system validates against a **fixed JSON-Schema** (draft 2020-12):

- **closed-world** — `additionalProperties: false`; an unknown/typo'd key is a load-time error, not a
  silently dropped edge.
- **enums for every closed vocabulary** — `kind`, `provenance`, `rel_type`, `result`, `status`,
  `phase`, `severity`. Invalid values fail validation.
- **descriptions required** — every field documents what it is / does / does not.
- **no "trust me" YAML** — including this bundle's own `_index.yaml`, dogfooded by
  `schema/design-index.schema.json`.

## The package (D10)

`uacp-schema` is a **separate, minimal, foundational pure-leaf package**: JSON-Schema files + an enums
module + a thin `jsonschema`-based `validate(kind, doc)`. No kernel logic, no policy. It is the **sink
of the dependency graph** — `uacp-lint`, `uacp-fmt`, Guardian, Heartgate, the projection engine, and
the `uacp-core` writer all import it; it imports nothing. `uacp-core` *composes* it.

## As-is coverage (audited 2026-06-19) — mostly absent

Schema validation today is **scattered, manual, and largely missing**:

- `scripts/validate_uacp_artifacts.py` — an **orphan manual-drill tool**, ~6 kinds, **not** wired into
  CI/hooks. Its own docstring: *"intentionally not a full schema engine."*
- **Heartgate** validates only `uacp.phase_transition` (+ nested `council_synthesis`), and runtime
  enforcement is *"not yet implemented"* (`config/state.yaml`).
- **Write path is permissive** — YAML parse + path containment only; **no** kind / shape / enum check.
- **State files** have a schema in `config/state.yaml` but are **loaded as raw dicts** (no model
  validation).
- **No schema at all** for `uacp.proposal`, `uacp.plan`, `uacp.execution`,
  `uacp.execution_checkpoint`, `uacp.verification`, `uacp.resolution`, `uacp.lesson`, + ~20 misc kinds.
- **No central registry** mapping `kind → schema`; knowledge is split across config YAMLs + hardcoded
  validators + pydantic models.

**Conclusion:** schema-first is **largely greenfield** — we are wiring up validation that does not
exist, not replacing a working one. (This is also the answer to "do we already have a validator?": no,
not meaningfully.)

## Catalog (to define in `uacp-schema`)

- **Node schemas** — scope_item, work_unit, evidence_obligation, checkpoint, assessment, lesson;
  (Slice 2) prohibition, method_constraint, metric; (Slice 3) code_symbol.
- **Index schemas** — proposal_index, plan_index, execution_index, verification_index,
  resolution_index, design_index.
- **Edge record** — `{src, dst, rel_type, provenance}` (see [10-edge-schema](10-edge-schema.md)).
- **Migrate** the existing partial schemas (phase_transition, council_synthesis, gate_selection,
  run_state, current_state) into the registry as the single source.

## What it does NOT do

- not cross-node **closure** (orphan/phantom/uncovered) — that is the [projection engine](14-projection-engine.md) at Heartgate.
- not **semantic correctness** (is the decomposition good?) — that is council.
- not **formatting** — that is `uacp-fmt`.
- not **policy** (may this write happen?) — that is Guardian.

## Format

JSON Schema 2020-12 — language-agnostic, enum/closed-world native. Pydantic models may *export* to it
so code and schema stay one source. Editor validation via the `# yaml-language-server: $schema=...`
directive (see `_index.yaml`).
