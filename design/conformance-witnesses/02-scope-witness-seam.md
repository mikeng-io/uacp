---
type: decision
title: "Scope-witness seam — authored code_refs, gate-invoked derivation, advisory-first"
description: "Decides the binding/delivery seam for the codeflair scope witness: the agent authors code_refs (the falsifiable claim); the GATE derives the independent account by exec'ing the codeflair CLI at measure time (process boundary — git-parity, no import); code compares. Rejects the file-handoff seam as agent-forgeable. Advisory-first with measurable promotion criteria. Grounded in the #83 spike, its adversarial review, and the seam review that killed the artifact handoff."
tags: [conformance, witness, seam, codeflair, decision, scope]
timestamp: 2026-07-03
edges:
  - {dst: 01-witness-scoreboard, rel: depends_on, provenance: asserted}
---
# 02 — The scope-witness seam (decision)

## The question

How does codeflair's account of a change reach the scope gate (issue #84),
under the constraint that killed Shim-B: the code plane must not enter the
kernel. Candidate claims: **A inferred** (witness derives the "declared"
touch-set itself) vs **B authored `code_refs`** (agent declares; witness
derives; code compares). Candidate deliveries: **produced artifact** (a file
the gate reads) vs **gate-invoked derivation** (the gate execs the codeflair
CLI at measure time and consumes its output directly).

## Decision

**B authored `code_refs` × gate-invoked derivation, advisory-first.**

*Claim side* — Option A collapses claim and derivation into one actor
(whoever infers the boundary also grades it): self-attestation one level up,
and an inferred boundary is not falsifiable. Option B keeps the roles apart
and gives the governance soul its object: correct-but-undeclared work is
*ungoverned*, and the remedy is re-declaring `code_refs`, never silently
widening them.

*Delivery side* — the produced-artifact handoff was REJECTED by adversarial
review: the gate would read a file at a path the agent's own governed writer
can target (`uacp_artifact_write` accepts arbitrary non-manifest YAML under
`verification/` — `governed_handlers.py:492-541`), and `generated_by:
codeflair` is a plaintext string, not provenance. EXECUTE could hand-author a
friendly witness and the "deterministic witness" would still be
self-attested. Instead the gate **derives** the account itself: at sweep time
it execs the codeflair CLI (subprocess, stdout) exactly as the landed
`SC_DIFF_*` half execs git via `engines/io/gitio.py`. The working tree and
the symbol graph are the ground truth; no agent-writable file sits between
witness and gate. (If the gate chooses to serialize the result under
`verification/` as an evidence record, that is a gate-written convenience
copy — never the input.)

**CF-D9, stated precisely**: the kernel must never *import or link* the code
plane (that was Shim-B's sin — codeflair types and calls inside kernel code).
A subprocess exec across a process boundary does not put codeflair in the
kernel: the kernel gains only an *optional external prober*, with the same
doctrine as git — prober absent or failing → an UNAVAILABLE advisory, never a
crash, never a silent pass.

## The witness contract (LOCKED for the #85 build)

- **Claim**: optional `code_refs` on the scope artifact. Each ref is
  `{file, name}` where `file` is the repo-root-relative POSIX path exactly as
  the codeflair store's `file` column records it, and `name` is the
  class-qualified symbol name (`Violation`, `Heartgate.validate_closure`).
  Resolution is by (file, name) lookup — never bare-substring seeding (spike
  pitfall 1: `validate` → 508 silent candidates).
- **Derivation**: the engine calls a new io capability (`engines/io/`
  subprocess wrapper, gitio doctrine: never raises, typed result, timeout)
  that execs `codeflair witness --repo <workspace> --run-id <id>
  [--code-ref file:name ...]` and parses **stdout JSON**:

  ```yaml
  run_id: <run id>
  graph_stamp:
    commit: <HEAD the index was built at>
    tree_token: <content token of the working tree at witness time>
  ingestion: scip                    # gate rejects weaker provenance floors
  symbols_touched: [{file, name}, ...]      # derived from the ACTUAL diff
  undeclared_cascade:                # touched/hop-1-connected, not covered by code_refs
    - {file, name, reason}           # reason ∈ {calls, references, defines}
  over_declared: [{file, name}, ...] # declared refs outside touched ∪ hop-1(touched)
  unresolved_declared: [{file, name}, ...]  # declared refs the graph cannot resolve
  unresolved_touched: [<name>, ...]  # touched symbols the graph cannot resolve (new code)
  ```

- **Freshness is by construction, not by stamp comparison**: `witness`
  (re)indexes the run's **current working tree** — dirty state included —
  immediately before deriving (~18s/590 files: cheap enough per sweep). A
  bare `graph_stamp.commit == HEAD` check is explicitly WRONG (it passes
  precisely when the index is most stale relative to the uncommitted diff);
  `tree_token` is what records what was actually indexed. Newly-added symbols
  therefore resolve (they are in the tree that was indexed); only symbols the
  ingester cannot parse land in `unresolved_touched`.
- **Gate side** (extends `engines/scope_conformance.py`; all advisory
  `severity: warn` in v1):
  - `undeclared_cascade` non-empty → `SC_UNDECLARED_CASCADE` (under-declaration:
    the boundedness catch);
  - `over_declared` non-empty → `SC_SCOPE_OVERDECLARED` (a claim ⊇ the graph
    makes every cascade "covered" — `write_paths: ["**"]` in symbol clothing;
    the claim must be a superset AND near-minimal);
  - `unresolved_declared` non-empty → `SC_WITNESS_UNRESOLVED_CLAIM` (a bogus
    ref must never silently count as coverage);
  - `unresolved_touched` non-empty → surfaced inside the cascade advisory's
    detail (visible-but-not-blocking; silent fail-open forbidden, hard
    fail-closed would flag every unparseable artifact);
  - CLI absent / non-zero / garbled stdout / timeout →
    `SC_WITNESS_UNAVAILABLE` (fail-closed visibility, gitio parity);
  - no `code_refs` declared → no-op while advisory (the claim is opt-in until
    promotion).
- **Signal discipline** (spike §3/§6): membership and **hop-1 connectivity**
  only. Closure-size magnitude is hub-dominated and inverts the true ranking
  (`run_all_engines` closure 267 vs `Violation` 123 despite 4-vs-65 direct
  callers) — it must not appear in any threshold. This finding also reshapes
  prevention-at-PLAN (#86): "claimed boundary ⊉ dependency-closure" cannot be
  built as written; it needs hop-1 membership, benchmarked in the direction
  it actually uses, only after this seam proves itself.

## Enforce vs advise

**Advisory-first** (`severity: warn`), the Oracle precedent. The spike's
verdict is *trust-provisional, single-repo Python*: it validated magnitude
separation on six curated symbols, not the containment operation itself.
Promotion to blocking is a separate, explicit decision gated on ALL of:

1. the end-to-end containment proof in the #85 build (declared `code_refs` vs
   a real diff's derived set) shows no false positive on real changes;
2. ≥10 real (or dogfood) runs with zero false-positive advisories at closure,
   measured over the population the witness can actually witness (edits to
   parseable, resolvable symbols — `unresolved_touched` entries are outside
   that population and are not counted as false positives);
3. the multi-repo / multi-language bench the spike did not run (Trustless;
   scip-go or scip-typescript exercised on real symbols);
4. at promotion, absence itself escalates: missing `code_refs`, missing
   codeflair, or `SC_WITNESS_UNAVAILABLE` become blocking for runs whose
   scope declares code — a run must not escape the witness by never feeding
   it (the advisory-phase no-op is explicitly temporary).

## Where the check runs (honest as-built note)

The engine sweep (`run_all_engines`) fires at **closure** — Heartgate's
`validate_closure`, invoked by `handle_finalize` — so as-built this lands as
detection-at-closure, not a literal EXECUTE→VERIFY hook. The engine is
phase-agnostic (`validate(workspace, run_id)`); adding a VERIFY-entry
invocation later needs no contract change. Because the gate derives the
witness itself, there is no separate "who produces the file, and when"
trigger to define — every sweep re-derives from ground truth.
