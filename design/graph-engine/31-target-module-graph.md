---
type: contract
title: UACP Modular Architecture — Target Module Graph + Decomposition Roadmap
description: The target component/module graph for UACP (the "graph for our modules") — the components, their Clean-Architecture ring, target file, the inward-pointing dependency DAG, the target file tree, and the prioritized roadmap to get there from the core.py monolith.
tags: [uacp, architecture, module-graph, target, roadmap, refactor]
timestamp: 2026-06-22
edges:
  - {dst: 29-ddd-ca-reference, rel: depends_on, provenance: asserted}
  - {dst: 30-current-state-decomposition, rel: depends_on, provenance: asserted}
  - {dst: 28-component-registry, rel: realizes, provenance: asserted}
---

# Target Module Graph + Decomposition Roadmap

The code-structure analog of the artifact graph engine: the components, their ring, their home, and the dependency DAG. Consistent with [28-component-registry](28-component-registry.md) (names) + D42/D43.

## Target components

| Component | Responsibility | Ring | Target home |
|---|---|---|---|
| **Guardian** | write-time policy gate (classify / contain / decide) | application | `engines/guardian/` |
| **Heartgate** | phase-transition gate (orchestrate validators → pass/block) | application | `engines/heartgate/` (hub + `validators/`) |
| **Manifest engine** (D43) | own the manifest documents: entity-writer + projection | application | `engines/manifest/` |
| **State engine** | run lifecycle state + document index + registry/pointer/ledger | application | `skills/uacp-state/` (unchanged) |
| **Validation engines** | per-run read-only integrity checks | application | `engines/*.py` (registered in `base.py`) |
| **Oracle** | knowledge/semantic engine | application | `engines/oracle/` (unchanged) |
| **Governed writers** | the low-level Guardian-gated FS write primitive | adapter | `engines/manifest/governed_writers.py` (moved from root) |
| **Config / IO / Contracts / ToolSpecs / HookKernel** | adapters/glue | adapter | unchanged |
| **Domain leaves** | pure rules/schemas (`schema`, `layout`, `gate_rules`, …) | domain | `engines/domain/*` (unchanged) |
| **Runtime adapters / filesystem** | runtimes + low-level FS | framework/infra | `runtime-adapters/*`, `filesystem.py` |

## Dependency DAG (inward-only; no cycles)

```
runtime-adapters/ (hermes · mcp · hooks)        ← FRAMEWORK
        │ calls
        ▼
tool_specs · hook_kernel · config · io.loaders · contracts · governed_writers   ← ADAPTER
        │ uses
        ▼
Guardian   Heartgate   Manifest engine   State engine   Oracle   validation engines   ← APPLICATION
        │  (orchestrate; read via IO; NEVER import an outer ring)
        ▼
engines/domain/*  (schema · layout · gate_rules · phase_graph · artifact_schema · …)   ← DOMAIN (sink; stdlib only)
```

Selected edges (who imports whom):
- `Heartgate` → validation-engine registry (`base.ENGINES`), `Manifest engine` (doc validation), `engines/io` (loaders), domain leaves. **Injected, not lazy-imported** (kills the latent-cycle smell from node 30).
- `Manifest engine` → `layout` + `schema` (domain) + `uacp-lint`/`uacp-fmt` + Governed writers (adapter) + Guardian (on write) + registers paths into the **State engine** index.
- `Guardian` → `GuardianPolicy` + domain helpers only.
- Validation engines → `engines/io` + domain leaves (NOT `core`; move `resolve_uacp_root` → `engines/domain/paths.py`).
- Domain leaves → stdlib / pydantic / jsonschema only.

**Rule of the graph:** an arrow may only point down/inward. A new module that needs to point *up* (a domain leaf importing an engine, an engine importing a runtime) is a design error — re-place it.

## Target file tree (kernel)

```
skills/uacp-core/scripts/
  core.py                      # SHRINK → thin public re-exports (Guardian.load, Heartgate.load)
  config.py contracts.py filesystem.py hook_kernel.py tool_specs.py   # adapters (keep)
  engines/
    base.py                    # Violation + ENGINES + run_all_engines (keep)
    guardian/  {models,policy,guardian,events,audit}.py
    heartgate/ heartgate.py  models.py  validators/{phase_exit,coherence,adaptive_gates,phase2,phase3,helpers}.py  goal_driven.py
    manifest/  manifest.py  projection.py  entity_writer.py  governed_writers.py   # D43 (NEW)
    graph_projection.py scope_conformance.py evidence_completeness.py
    deferral_completeness.py coherence.py artifact_integrity.py ledger_integrity.py  # validation engines (keep)
    domain/    {schema,layout,gate_rules,phase_graph,artifact_schema,scope,checkpoint,
                budget,registry,pointer,ledger,escalation,corpus,evidence_cluster,
                deferral,artifact_hashes,phase_transitions, paths(NEW)}.py           # domain leaves (keep)
    io/        loaders.py  (+ phase_transitions_io, artifact_schema_io extracted)
    oracle/    … (keep)
skills/uacp-state/scripts/  state.py state_machine.py   # State engine (keep)
```

## Decomposition roadmap (low-risk first; each step mechanical + suite-guarded)

Follows the seam priority in [30-current-state-decomposition](30-current-state-decomposition.md):

1. **Guardian → `engines/guardian/`** (~725 lines out; LOW risk) — prove the extraction pattern.
2. **Artifact loaders → `engines/io/`** (~280; MED).
3. **Phase-exit invariants → `…/validators/phase_exit.py`** (~60; LOW).
4. **Adaptive gates → `…/validators/adaptive_gates.py`** (~350; MED) — unify the 5 copy-pastes.
5. **Stand up the Manifest engine** (`engines/manifest/`) — move Governed writers in; build the **entity-writer** (composes layout+schema+lint+fmt); migrate the doc validators (intent/scope/evidence/lessons) into it. *(This is the wiring the lite-council's BLOCKER demanded — the entity-writer is what finally calls `layout`+`schema`.)*
6. **Goal-driven track → `engines/heartgate/goal_driven.py`** (~750; MED).
7. **Remaining gates** (PPV / plan-validation / run-registry) → `…/validators/*.py`; run-registry may move to the State engine.
8. **Convert lazy imports → constructor injection** in `Heartgate` (pass dispatcher/config/loaders) — removes the latent-cycle defense.

**Guardrails:** never let a new module import an outer ring; `core.py` must not grow back; each extraction is a pure move + full-suite green + ruff. This roadmap is sequencing only — each step is its own governed increment (TDD where logic moves).
