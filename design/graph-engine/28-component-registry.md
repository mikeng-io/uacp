---
type: reference
title: UACP Component & Engine Registry (canonical, as-built)
description: The single authoritative naming for every UACP COMPONENT — name / what it does / which package+script — grounded in the real code (skills/uacp-core, skills/uacp-state, engines/*). Resolves the "manifest engine vs state engine" chaos and the overloaded word "engine". Read before naming any component/engine; nothing else is canonical.
tags: [uacp, components, engines, nomenclature, reference, drift-guard]
timestamp: 2026-06-22
edges:
  - {dst: 26-nomenclature, rel: relates_to, provenance: asserted}
  - {dst: 18-glossary, rel: supersedes, provenance: asserted}
---

# UACP Component & Engine Registry (canonical, as-built)

> **One name per component**, grounded in the real package/script (not design aspiration).
> This node is authoritative for **component names**; [26-nomenclature](26-nomenclature.md) is
> authoritative for **artifact kinds**; [27-directory-taxonomy](27-directory-taxonomy.md) for
> **file layout**. [18-glossary](18-glossary.md)'s engine/topology names are **superseded here**
> (it invented "manifest engine" / "indexer engine" that don't exist as code).

## The word "engine" is overloaded — two distinct senses

1. **Component-actor** (a top-level thing that acts): Guardian, Heartgate, the State engine, the Oracle.
2. **Validation engine** (a registered read-only check run by Heartgate): `graph_projection`,
   `scope_conformance`, etc. — entries in `engines/base.py::ENGINES`.

When unqualified, "engine" is ambiguous — **say which sense.** Prefer the specific name below.

## Kernel — package `skills/uacp-core/`

| Canonical name | What it does | Script(s) |
|---|---|---|
| **Guardian** | Write-time gate: tool/path classification, containment, policy; blocks raw writes to governed paths. | `core.py` (`class Guardian`, `GuardianPolicy`) |
| **Heartgate** | Phase-transition gate: runs the validation engines + the offline artifact validator + phase-exit invariants; emits the block/pass decision. | `core.py` (`class Heartgate`) |
| **Governed writers** | The ONLY sanctioned write surface for governed artifacts (`uacp_artifact_write`, `uacp_doc_write`, `uacp_config_write`, `uacp_gate_ledger_append`, …). | `governed_handlers.py`, `tool_specs.py` |
| **Validation engines** (registered, read-only) | Per-run integrity checks Heartgate runs: `graph_projection` (structural graph), `scope_conformance`, `evidence_completeness`, `deferral_completeness`, `coherence`, `artifact_integrity`, `ledger_integrity`. | `engines/base.py` (`ENGINES`) + `engines/<name>.py` |
| **Domain leaf modules** (pure rules/data; the dependency sink, no I/O) | `schema` (artifact SHAPE), `layout` (file TOPOLOGY), `artifact_schema`, `phase_transitions`, `gate_rules`, `evidence_cluster`, `pointer`, `ledger`, `escalation`, `corpus`, `scope`, `checkpoint`, `budget`, `registry`, `phase_graph`, `artifact_hashes`. | `engines/domain/*.py` |
| **Offline artifact validator** | The 27-function per-kind artifact validator; kernel-invoked by Heartgate (`core.py:1862`). **Becomes `uacp-lint`** (D41) — its shape checks delegate to `schema`. | `scripts/validate_uacp_artifacts.py` |
| **Oracle** | Knowledge/semantic engine: embed + retrieve + rerank over the knowledge/lesson corpus; **sole owner** of the corpus (`test_corpus_boundary`). | `engines/oracle/*.py` |
| **Config** | Config loader + `[paths]` resolver. | `config.py` + `config/uacp.toml` / `config/*.yaml` |
| **IO loaders** | Read the manifest + artifacts off disk for the engines. | `engines/io/loaders.py` |

## State — package `skills/uacp-state/`

| Canonical name | What it does | Script(s) |
|---|---|---|
| **State engine** (`uacp-state`) | Owns the **run manifest** + all lifecycle state: `RunManifest`, artifact registration into the manifest, the run-registry, the current pointer, the gate ledger. | `state.py`, `state_machine.py` |

> **The "manifest engine vs state engine" answer:** they are the **same component** — the **State
> engine (`uacp-state`)**, which owns the run manifest. There is **no separate "manifest engine"**.
> The design's "manifest engine" actually split across two real components: the **State engine**
> (run manifest + state) and the **Governed writers** (artifact writes) — name those two, never
> "manifest engine".

## Lifecycle skills (agent-facing, one per phase — SKILL.md, no kernel logic)

`uacp-brainstorm` · `uacp-triage` · `uacp-propose` · `uacp-plan` · `uacp-execute` · `uacp-verify` · `uacp-resolve` — each guides the agent through its phase; the kernel (Guardian/Heartgate) enforces.

## Orchestration / review

| Canonical name | What it does | Package |
|---|---|---|
| **Council** | Semantic-judgment review gate (correctness, not just structure). | `uacp-council` |
| **Debate** | Multi-round adversarial review substrate (reused by Council). | `uacp-debate` |
| **Parallel** | Fan-out / parallel sub-agent dispatch. | `uacp-parallel` |
| **Bridge** | Runtime dispatch mapping (Hermes / Claude Code / Kimi). | `uacp-bridge` + `runtime-adapters/` |

## Router / meta / surface

`uacp` (router skill) · `uacp-skills` (skill-authoring convention/meta) · `uacp-context` · `uacp-web`; `runtime-adapters/{hermes,mcp,hooks}` (runtime integration).

## DRIFT GUARD — deprecated component names (do not use)

| ❌ deprecated / aspirational | ✅ canonical real component | why |
|---|---|---|
| "Manifest engine" | **State engine (`uacp-state`)** + **Governed writers** | the design's one "manifest engine" = two real components; no `manifest_engine.py` exists |
| "State engine" *as distinct from* manifest engine | **State engine (`uacp-state`)** | same component — one name |
| "Indexer engine" | the **Validation engines** (`engines/`) + the **Oracle** | no `indexer_engine.py`; structural checks = `engines/`, semantic = Oracle |
| "the projection engine" | **`graph_projection`** (a registered validation engine) | `engines/graph_projection.py` |
| "uacp-schema" (as a standalone package) | the **`schema` domain leaf module** | it is `engines/domain/schema.py`, not a separate package (D27 deferred packaging) |
| bare "engine" (unqualified) | name the component-actor OR the validation engine | the word is overloaded — see top |
