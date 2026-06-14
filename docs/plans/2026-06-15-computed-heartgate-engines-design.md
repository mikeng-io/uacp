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

1. **Foundation** — `engines/base.py` (Violation + registry); move/refactor `coherence.py`
   into the package; harness + coherence tests stay green.
2. **Four engines in parallel** (independent files): scope, evidence, ledger, deferral —
   each = module + positive test (good run → 0 violations) + per-rule teeth tests
   (corrupt one thing → specific code). Each grounds in real schemas and flags
   un-computable parts honestly.
3. **Wire** the registry into Heartgate at RESOLVE (handle the finalize-timing rule);
   add a test that a good run passes all engines AND a deliberately-bad run is **blocked**
   by Heartgate.
4. **Update** the design/decision records; supersede the self-attested coherence flag.

## Failure policy

Engines are read-only consumers; do not weaken a check to force green. If a good run
genuinely fails an engine, that's a real finding — keep the check correct, xfail the
positive assertion with a precise reason, and report it (it may reveal a kernel bug like
F-T3-01).

## Success criteria

- One `engines/` package, one `Violation` type, one `ENGINES` registry.
- Each engine: positive test green, teeth proven per rule, never raises.
- Heartgate runs all engines at RESOLVE; a bad run is blocked with a clear reason; a good
  run closes cleanly. Full suite green.
