---
type: design
title: "Computed Heartgate Engines (Design)"
description: "Design for replacing Heartgate's honor-system coherence lens with deterministic computed enforcement engines"
tags: ["heartgate", "enforcement", "engines", "computed"]
timestamp: 2026-06-15
status: archived
---

# Computed Heartgate Engines (Design)

> **For Claude:** after approval, drive via `superpowers:subagent-driven-development`.

**Date:** 2026-06-15
**Status:** approved (operator selected all four engines + coherence wiring)

---

## Goal

Replace Heartgate's honor-system "coherence lens" (and add adjacent dimensions) with a
set of **deterministic, computed engines** that Heartgate runs as real blockers. Convert
"the agent says it's fine" into "the machine verified it." One shape, one home, one
registry — not scattered.

## Why

`core.py:819` (`_validate_heartgate_coherence`) today reads a **self-attested**
`heartgate_coherence` object whose `status: pass/block` is set by the agent/council, and
only checks the lens *names* are listed. That violates the "no self-attesting closures"
invariant. The engines below compute each dimension instead of trusting a flag.

## Architecture (locked — operator decisions 2026-06-15)

- **Hexagonal-lite + DDD vocabulary** (not full CA, not full DDD). Dependencies point
  inward: `domain ← engines ← io ← adapters`. No documented CA/DDD precedent existed in
  the repo; the closest is `runtime-adapters/` + the Cognitive Planes model (hexagonal
  bones). We formalize that lightly, reusing UACP's existing ubiquitous language
  (Run, Manifest, Gate, Lens, Violation, Phase, Scope, DeferredItem).
- **Tooling:** adopt **ruff** (lint + format) in `pyproject` + a CI lint step; engines
  parse manifest/artifacts through **Pydantic domain models**, not `yaml.safe_load` +
  dict access. ruff is strict on `engines/`; lenient/gradual on the legacy 2,240-line
  `core.py` (its god-module split is Phase 2, under the harness).

Package layout `skills/uacp-core/scripts/engines/`:
```
engines/
  base.py        # Violation, Engine type, ENGINES registry, run_all_engines (done)
  domain/        # Pydantic models — pure data + invariants, NO I/O
                 #   manifest.py (reuse/import RunManifest), ledger.py (LedgerEntry),
                 #   scope.py (Scope), deferral.py (DeferredItem), artifacts.py
  io/            # the ONLY filesystem layer — load manifest/ledger/artifacts/current.yaml
                 #   -> return domain models (never raises; missing/garbled -> typed result)
  coherence.py   scope_conformance.py  evidence_completeness.py
  ledger_integrity.py  deferral_completeness.py   # use-case engines: read domain, return Violations
```

## The common contract (locked — every engine conforms)

A new package `skills/uacp-core/scripts/engines/`:

- `engines/base.py` — defines the shared types and registry:
  ```python
  @dataclass(frozen=True)
  class Violation:
      code: str        # stable, e.g. "SCOPE_OUT_OF_BOUNDS"
      severity: str    # "block" | "warn"
      message: str     # human-readable, names what disagreed
      detail: dict     # structured context

  # Engine = Callable[[workspace: Path, run_id: str], list[Violation]]
  # Each engine module exposes: def validate(workspace, run_id) -> list[Violation]
  # ENGINES: list[tuple[str, Engine]] — the registry Heartgate iterates.
  ```
- Every engine is **read-only**, **never raises** (malformed/missing input → a violation,
  not an exception), and imports kernel facts (`VALID_TRANSITIONS`, `TERMINAL_PHASES`,
  `_resolve_uacp_path`) rather than re-declaring them.
- `coherence.py` is **moved into the package** and refactored to use the shared
  `Violation` (its checks/tests are unchanged in behavior).

## The five engines

| Module | Computes | Honest computability note |
|---|---|---|
| `coherence.py` | manifest ↔ ledger ↔ artifacts ↔ pointer agree (C1–C6) | built + verified; refactor to shared `Violation` |
| `scope_conformance.py` | the run's changeset stayed within declared `write_paths` / `blast_radius` | no durable write-log exists; compute what IS available (declared scope ↔ run-registry consistency; registered-artifact paths ⊆ declared paths; optional `git diff` mode for real runs) and **flag what can't be checked** rather than fake it |
| `evidence_completeness.py` | every claimed-complete phase/PIV item has a backing artifact + ledger entry | ground in the real plan/PIV/checkpoint schema; compute over what `config/artifact-schemas.yaml` actually supports |
| `ledger_integrity.py` | gate-ledger is append-only: parseable, run_id-consistent, timestamps monotonic non-decreasing, no gaps/dupes where uniqueness is expected | self-contained; cleanest |
| `deferral_completeness.py` | every `deferred_item` carries owner + residual_risk + next-phase obligation, and nothing deferred is silently dropped by RESOLVE | ground in the real `deferred_items` artifact shape |

## Wiring into Heartgate

- Heartgate gains a method `run_engines(run_id) -> list[Violation]` that iterates the
  `ENGINES` registry and aggregates. Any `block`-severity violation becomes a Heartgate
  blocker; `warn` becomes a warning.
- **Call site = RESOLVE / post-finalize**, NOT inside `validate_transition` for the
  `verify→resolved` edge — because `finalized_at` is stamped by `handle_finalize` *after*
  the transition, so C4 (and evidence/deferral closure checks) would false-positive
  mid-transition. (Confirmed: `state_machine.py:236` sets status=resolved with
  `finalized_at=None`; `:357` stamps it later.) Engines that are timing-safe (ledger
  integrity, scope, coherence C1/C2/C3/C5) MAY also run at the execute/verify coherence
  gate; closure-dependent checks run only at RESOLVE.
- The self-attested `_validate_heartgate_coherence` flag-check is **superseded** by the
  computed coherence engine (keep the field for back-compat, but the computed result is
  authoritative).

## Build sequence

0. **base.py + move coherence** — ✅ done (commit a92015b): shared `Violation`, registry,
   `run_all_engines`, coherence moved into the package.
1. **ruff** — add `[tool.ruff]` to `pyproject` + dev dep + CI lint step. Strict on
   `engines/`; lenient on legacy `core.py` (per-file ignores) so legacy noise doesn't
   drown CI. Fix engine-package lint.
2. **domain/ + io/ + refactor coherence** — Pydantic domain models + the single io
   loading layer; refactor `engines/coherence.py` to parse via them (behavior-preserving;
   its 12 tests stay green). This proves the layering before the 4 new engines copy it.
3. **Four engines in parallel** (independent files): scope, evidence, ledger, deferral —
   each = module (uses domain + io) + positive test (good run → 0 violations) + per-rule
   teeth tests (corrupt one thing → specific code). Each grounds in real schemas and flags
   un-computable parts honestly.
4. **Wire** the registry into Heartgate at RESOLVE (handle the finalize-timing rule);
   add a test that a good run passes all engines AND a deliberately-bad run is **blocked**
   by Heartgate.
5. **Update** the design/decision records; supersede the self-attested coherence flag.

## Failure policy

Engines are read-only consumers; do not weaken a check to force green. If a good run
genuinely fails an engine, that's a real finding — keep the check correct, xfail the
positive assertion with a precise reason, and report it (it may reveal a kernel bug like
F-T3-01).

## Status: DELIVERED (2026-06-15)

All five engines built, independently teeth-verified, wired into
`Heartgate.validate_closure` as RESOLVE blockers (decoupled — not auto-called in
`handle_finalize`). F-EV-01 fixed config-wide. Self-attested coherence flag superseded.
321 tests pass; engines/ ruff-clean. See decision-log 2026-06-15.

**Non-blocking follow-ups:** (a) dedupe `C2`/`LI` ledger-malformed overlap at the
reporting layer (one finding per corrupt line, as done for SC/C6); (b) review the
`bridge-commons` three-dot `...outputs` token; (c) the Claude Code **plugin** (MCP server
exposing governed writers + `uacp_validate_closure` as tools + PreToolUse Guardian hook)
is the next effort — the real "Claude Code adapter."

## Success criteria

- One `engines/` package, one `Violation` type, one `ENGINES` registry.
- Each engine: positive test green, teeth proven per rule, never raises.
- Heartgate runs all engines at RESOLVE; a bad run is blocked with a clear reason; a good
  run closes cleanly. Full suite green.
