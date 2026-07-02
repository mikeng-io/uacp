---
type: decision
title: "Scope-witness seam — authored code_refs, produced artifact, advisory-first"
description: "Decides the binding/delivery seam for the codeflair scope witness (Option B: authored code_refs as the falsifiable claim; codeflair writes an independent artifact the gate reads) and the enforce-vs-advise dial (advisory-first with explicit promotion criteria). Grounded in the #83 spike and its adversarial review."
tags: [conformance, witness, seam, codeflair, decision, scope]
timestamp: 2026-07-03
edges:
  - {dst: 01-witness-scoreboard, rel: depends_on, provenance: asserted}
---
# 02 — The scope-witness seam (decision)

## The question

Two seams could bind codeflair's account of a change to the scope gate
(issue #84), under the hard constraint CF-D9: **the kernel never imports the
code plane** (the rejected Shim-B put the seam inside the kernel and was
reverted for exactly that).

- **A — inferred**: the witness derives the "declared" touch-set lazily from
  intent/anchors; the agent authors nothing new.
- **B — authored `code_refs`**: the agent declares its touch-set as an
  explicit, falsifiable claim on the scope artifact; codeflair independently
  derives the actual touched/cascaded set and writes it as a **produced
  artifact**; the gate only compares.

## Decision

**Option B, delivered as a produced artifact, advisory-first.**

The pattern is the initiative's locked shape: *the agent claims, an
independent witness derives, code compares*. Option A collapses claim and
derivation into one actor (whoever infers the touch-set is also grading it),
which reproduces self-attestation one level up — and an inferred boundary is
not falsifiable, so "out-of-scope" loses its meaning. Option B keeps the three
roles separate and gives the governance soul its object: correct-but-
undeclared work is flagged as *ungoverned* and the remedy is **re-declaring**
`code_refs`, never silently widening them.

## The witness-artifact contract (LOCKED for the #85 build)

- **Claim**: optional `code_refs: [<symbol ref>]` on the scope artifact —
  workspace-meaningful symbol references, resolved via **(file, name)** lookup
  against the store, never by bare-substring seed (spike pitfall 1: `validate`
  → 508 silent candidates).
- **Witness artifact**: `verification/<run_id>-code-witness.yaml` under the
  governed namespace, written by the codeflair CLI (`codeflair witness`)
  invoked OUTSIDE the kernel — runtime hook or operator, never an engine.
- **Minimal schema** (producer and consumer must stay byte-identical to this):

  ```yaml
  run_id: <run id>
  generated_by: codeflair            # provenance floor: reject anything else
  graph_stamp: <repo commit the index was built at>
  ingestion: scip                    # gate must see parsed-provenance edges
  symbols_touched: [<symbol ref>, ...]      # derived from the ACTUAL diff
  undeclared_cascade:                # touched/connected but not covered by code_refs
    - {symbol: <symbol ref>, reason: <hop-1 relation>}
  unresolved: [<name>, ...]          # touched symbols the graph cannot resolve
  ```

- **Gate side** (extends `engines/scope_conformance.py`, io-loader read only):
  `undeclared_cascade` not covered by declared `code_refs` →
  `SC_UNDECLARED_CASCADE` (warn); `graph_stamp` disagreeing with the run's
  observed HEAD → `SC_WITNESS_STALE` (warn); malformed/unparseable witness →
  fail-closed advisory, never a crash, never a silent pass. Absent witness or
  absent `code_refs` → no-op while advisory (the claim is opt-in until
  promotion).
- **Unknown symbols** (the review's sharpest finding): a PR that ADDS symbols
  queries a graph that cannot contain them, even rebuilt at base. Decision:
  the witness **must surface them** in `unresolved` and the gate flags them
  advisory — visible-but-not-blocking. Silent fail-open is forbidden; hard
  fail-closed would block every PR that adds a function.
- **Signal discipline** (spike §3/§6): membership and **hop-1 connectivity**
  only. Closure-size magnitude is hub-dominated and inverts the true ranking
  (`run_all_engines` closure 267 vs `Violation` 123 despite 4-vs-65 direct
  callers) — it must not appear in any threshold. This finding also reshapes
  prevention-at-PLAN (#86): "claimed boundary ⊉ dependency-closure" cannot be
  built as written; it needs hop-1 membership, benchmarked in the direction it
  actually uses, only after this seam proves itself.

## Enforce vs advise

**Advisory-first** (`severity: warn`), the Oracle precedent. The spike's
verdict is *trust-provisional, single-repo Python*: it validated magnitude
separation on six curated symbols, not the containment operation itself.
Promotion to blocking is a separate, explicit decision gated on ALL of:

1. the end-to-end containment proof in the #85 build (declared `code_refs` vs
   a real diff's derived set) shows no false positive on real changes;
2. a run of real governed (or dogfood) runs — target ≥10 — with zero
   false-positive advisories at closure;
3. the multi-repo / multi-language bench this spike did not run (Trustless;
   scip-go or scip-typescript exercised on real symbols);
4. staleness discipline holds in practice (`graph_stamp` == observed HEAD, or
   rebuild-before-witness; ~18s/590 files is cheap enough per-PR).

## Where the check runs (honest as-built note)

The engine sweep (`run_all_engines`) fires at **closure** — Heartgate's
`validate_closure`, invoked by `handle_finalize`. The engine itself is
phase-agnostic (`validate(workspace, run_id)`), so nothing here precludes an
EXECUTE→VERIFY invocation later; but this design does not pretend one exists
today. Detection-at-VERIFY lands as: the witness artifact is produced after
EXECUTE, and every closure sweep from then on measures it.
