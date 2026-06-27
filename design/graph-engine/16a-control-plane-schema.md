---
type: contract
title: "Graph Engine — Control-Plane Schema: scope, format, unification (extends 16-schema-registry)"
description: The 2026-06-21 brainstorm result — EVERY non-code control-plane artifact has a registered schema, validated on write, via ONE JSON-Schema registry; format-agnostic (YAML doc or OKF Markdown frontmatter); one YAML structural form, NO JSON, gradient-by-discipline; unify the two existing validators.
tags: [graph-engine, schema, format, control-plane, uacp-schema, validation]
timestamp: 2026-06-21
edges:
  - {dst: 16-schema-registry, rel: extends, provenance: asserted}
---

# Control-Plane Schema — scope, format, unification (D40)

Extends [16-schema-registry](16-schema-registry.md) (the registry / D9-D10) with the three decisions from the 2026-06-21 brainstorm.

## Scope — every non-code control-plane artifact

The schema layer is the validation gate for the **entire control plane**: any file that is *not code* and belongs to the control plane carries a registered schema, validated on write. Not just the governance manifest — the knowledge plane and doctrine too.

| Category | Kinds | Carrier |
|---|---|---|
| Manifest documents | `uacp.proposal / plan / execution / verification / resolution` (+ brainstorm, triage) | YAML |
| Nodes (inside manifests) | scope_item, work_unit, evidence_obligation, checkpoint, assessment, lesson | YAML |
| Aggregates / indexes | `_index` (design_index, proposal_index, …) | YAML |
| Knowledge / OKF | lesson, knowledge_item, observation, reference | **`.md` frontmatter** |
| Runtime state | run_registry, gate_ledger, current_state | YAML |
| Config | uacp.toml, phase-transitions | TOML/YAML |
| Doctrine docs | `docs/**` OKF frontmatter (type/title/description/kind) | `.md` frontmatter |

## Format — one structural serialization, gradient by discipline

**YAML is the only structural format** — standalone for manifests/state/config, and as **frontmatter** inside OKF `.md` for knowledge/doctrine/design. **No JSON.** (A second *structural data* format — JSON *and* YAML — is the mix that's strictly worse: two parsers, two mental models, churn at every boundary. YAML + Markdown-with-YAML-frontmatter is NOT that mix — the structural serialization is YAML in both; Markdown only wraps prose.)

The **gradient is imposed by tooling, not by format**: structural keys → strict (a strict loader that kills YAML implicit typing — the "Norway problem" — + the schema's types/enums/required-FKs + a canonical `uacp-fmt`); prose → human (Markdown body / block scalars). Rigor where it's structural, readability where it's prose — in one form.

## Validation — format-agnostic

`validate_file(path)`: **resolve kind** (from the doc's `kind:` field, else a path→kind map) → **extract the structural dict** (`.yaml` = whole doc; `.md` = parse the YAML frontmatter, with optional required-body-section checks) → `validate(kind, dict)` → error strings. The `validate(kind, doc)` core already exists in `engines/domain/schema.py`; this adds kind-resolution + the loader.

## Unification — one registry, one paradigm

`schema.py` becomes **the** registry. Migrate `artifact_schema.py` (Pydantic transition artifacts) into it; fold `test_okf_frontmatter` (the OKF frontmatter lint) into knowledge/doctrine **schema entries**. One paradigm — JSON-Schema (D9/D10) — not a Pydantic+JSON-Schema mix (the same anti-mix instinct, one level up). Enforcement: validate-on-write (Guardian invokes the pure-leaf rules) + the same registry in CI/lint; `uacp-fmt` canonicalizes (paired, separate).

## Build

Re-scopes Slice 1b inc 3 — **schemas BEFORE the file-validator** (you can't validate a file before its kind's schema exists, and the node-item kinds aren't whole files — they live inside documents): `3a` node-item kinds ✅ → **`3b` DOCUMENT kinds** (`uacp.proposal/plan/execution/verification/resolution`, each *composing* the node-item schemas) + indexes → `3c` migrate `artifact_schema.py` → `3d` knowledge/OKF (+ retire the OKF lint) → `3e` state/config/doctrine → **`3f` the format-agnostic `validate_file`** (kind-resolution + YAML/`.md` loader — now there's something to validate) → `uacp-lint` (validate-on-write) + `uacp-fmt`.
