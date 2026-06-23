---
type: analysis
title: UACP Modular Architecture — Current-State Decomposition (the core.py god-object)
description: Grounded audit of how the kernel is smashed today — core.py is a 3,178-line monolith whose Heartgate class is ~2,400 lines doing ~20 responsibilities across 4 bounded contexts. Maps the responsibilities to line ranges and lists the prioritized extraction seams (low-risk first).
tags: [uacp, architecture, decomposition, core.py, audit, refactor]
timestamp: 2026-06-22
edges:
  - {dst: 29-ddd-ca-reference, rel: depends_on, provenance: asserted}
  - {dst: 31-target-module-graph, rel: relates_to, provenance: asserted}
---

# Current-State Decomposition — the `core.py` god-object

Grounded in `skills/uacp-core/scripts/core.py` (**3,178 lines**), `governed_handlers.py` (717), `skills/uacp-state/scripts/{state_machine.py (472), state.py (452)}`.

## What's already CLEAN (keep as-is)

- **`engines/domain/*`** (~18 leaf modules) — pure rules/schemas; the dependency sink. ✅
- **The registered Checks** (the `ENGINES` registry — `engines/{graph_projection,scope_conformance,evidence_completeness,deferral_completeness,coherence,artifact_integrity,ledger_integrity}.py` + `base.py`) — read-only, pluggable; "validation engines" is the legacy name (they are **Checks**, D44 / node 28). ✅
- **`engines/oracle/*`** — isolated knowledge engine (corpus-boundary-tested). ✅
- **`engines/io/loaders.py`, `config.py`, `filesystem.py`, `hook_kernel.py`** — clean adapters/infra. ✅
- **`uacp-state`** — owns run state; does NOT reach into `core`. ✅
- **No runtime import cycles.** (But see lazy-import coupling below.)

## The monolith: `core.py` responsibility map

| Responsibility | Lines | ~size | Belongs in (target) |
|---|---|---|---|
| Guardian models (`GuardianEvent`/`Decision`/errors) | 56–135 | ~80 | `engines/guardian/models.py` |
| `GuardianPolicy` (data + load + validate) | 138–248 | ~110 | `engines/guardian/policy.py` |
| `Guardian` (classify / containment / evaluate) | 275–677 | ~400 | `engines/guardian/guardian.py` |
| event factory / audit / root+provider helpers | 251–272, 680–763 | ~110 | `engines/guardian/{events,audit}.py` |
| **`Heartgate` — the god-object** | **786–3178** | **~2,392** | `engines/heartgate/` (split, below) |
| · transition/closure orchestration | 786–1001 | ~215 | `engines/heartgate/heartgate.py` (the hub) |
| · phase-exit invariants | 1182–1242 | ~60 | `…/validators/phase_exit.py` |
| · heartgate-coherence (self-attested; legacy?) | 1024–1180 | ~160 | `…/validators/coherence.py` (or retire) |
| · 5 adaptive package gates (propose/plan/execute/verify/resolve) | 1259–2162 | ~350 | `…/validators/adaptive_gates.py` (70% copy-paste → unify) |
| · goal-driven track (checkpoint/closure/track/budget) | 1334–2064 | ~750 | `engines/heartgate/goal_driven.py` |
| · artifact validators (intent/scope/evidence/lessons) | 2387–3129 | ~410 | `…/validators/{phase2,phase3}.py` → fold into the **Manifest engine** |
| · PPV / plan-validation / run-registry gates | 2164–3091 | ~465 | `…/validators/*.py` |
| · artifact loaders (`_load_yaml_under_root`, `_offline_validate_artifacts`, schema load) | 766–1913 (scattered) | ~280 | `engines/io/*` (adapter) |
| · helpers (glob, ledger, transition, safe-id) | scattered | ~150 | `…/helpers.py` |

## The tangles (why it's hard to know what we're fixing)

1. **God-method:** `Heartgate.validate_transition()` (786–933) calls **15+** specialized `_validate_*` methods in sequence — orchestration and implementation in one class. Adding a gate means editing the monolith.
2. **Cross-context bleed:** `Heartgate` validates **manifest documents** (intent/scope/evidence/lessons — belongs to the Manifest engine), reads **state** (run manifests, gate ledger, run registry — belongs to the State engine), and reads **config** inline (4+ `get_config`). Four contexts in one class.
3. **Lazy-import coupling:** ~10 methods lazy-import `engines.*`/`state.*` (core.py:780, 807, 835, 976, 1138, 1238, 1253, 1299, 1356, …) to dodge top-level cycles — the latent-cycle smell; fix with dependency injection.
4. **Copy-paste gates:** the 5 adaptive package gates repeat the same "load YAML → check kind/phase → validate universal_core → validate selected_modules" shape ~70%.

## Prioritized extraction seams (low-risk first)

| # | Extract | ~lines out | Risk | Why this order |
|---|---|---|---|---|
| 1 | **Guardian** → `engines/guardian/` (models/policy/guardian/audit) | ~725 | LOW | Self-contained, no Heartgate coupling; removes ~23% of core.py mechanically |
| 2 | **Artifact loaders** → `engines/io/*` | ~280 | MED | tightens the IO boundary the gates use |
| 3 | **Phase-exit invariants** → `…/validators/phase_exit.py` | ~60 | LOW | pure, mechanical |
| 4 | **Adaptive gates** → `…/validators/adaptive_gates.py` (unify the 5) | ~350 | MED | high ROI (kills copy-paste; new gates = a file) |
| 5 | **Artifact validators** (intent/scope/evidence/lessons) → the **Manifest engine** | ~410 | MED | moves doc-validation to its rightful owner (D43) |
| 6 | **Goal-driven track** → `engines/heartgate/goal_driven.py` | ~750 | MED | cohesive feature; isolates ADR-0016 |
| 7 | PPV / plan-validation / run-registry gates → `…/validators/*.py` | ~465 | MED-HIGH | run-registry couples to State engine — extract last (or move to it) |

**End state:** `core.py` shrinks from ~3,180 → ~a thin re-export hub (~100–300 lines); each gate/validator becomes independently testable. **Sequencing rule:** each extraction is mechanical (no logic change) + guarded by the full suite; do #1 first to prove the pattern.
