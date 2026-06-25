---
type: design
title: The Assertion Model — the typed check catalog (uacp.check.*)
description: >-
  What a generated check looks like when FROZEN: a typed, registered entity drawn from a CLOSED,
  versioned catalog of check-KINDS the agent selects and parameterizes from content (never free-form
  code-gen). Each kind is a deterministic predicate with a JSON-Schema in the registry and a matching
  replay engine. Defines the common envelope (from / bind / expect / severity), the initial catalog
  members by plane (graph + artifact-content buildable now; symbol/behavioral gated on the code plane),
  and the mapping to graph-engine D7 metric/prohibition/method_constraint.
tags: [verification, generative-gate, assertion-model, check-catalog, schema, d7]
timestamp: 2026-06-25
edges:
  - {dst: 10-generative-gate, rel: realizes, provenance: asserted}
  - {dst: 31-replay-engine, rel: depends_on, provenance: derived}
---

# The Assertion Model — the typed check catalog

A frozen check is **not** free-form code or a predicate DSL the agent writes from scratch (that is the
black box [10](10-generative-gate.md) warns against). It is a **typed entity** the agent SELECTS from a
**closed, versioned catalog** of check-KINDS and PARAMETERIZES from the artifact's content. Each kind:

- has a JSON-Schema in the registry (`engines/domain/schema.py` — the BUILT serialization sink), so a
  malformed check is rejected fail-closed at write time (the entity-writer's `has_schema`-gated path);
- has exactly one **deterministic replay engine** ([31](31-replay-engine.md)) that computes its verdict;
- is registered in `manifest.artifacts` and projected as a `check` node carrying a `measured_by` edge to
  the target it proves.

> **Built-vs-new correction (council, 2026-06-25).** This projection is **net-new code, not "for free."**
> `projection._load_and_project` loads every registered artifact, but `_project` is a **hardcoded
> extractor** — today it emits nodes only from `scope.in_scope` / `work_units` / `evidence_obligations` /
> `checkpoint_id` / `assessments`. A `uacp.check.*` doc fed through it produces **zero nodes**. Slice 0
> must add a `uacp.check.*` arm to `_project` that emits the `check` node + the `measured_by` edge. (Node
> 34's "a new check function in projection.py + a new edge" is the accurate statement; do not read "the
> substrate is built" as "checks project themselves.") Likewise, a new `kind` needs BOTH a JSON-Schema in
> `schema.py` AND a layout `Entry` (`layout.fmt_of`/`plane_of`) — the entity-writer refuses an unknown
> kind before validation. "Auto-register" = schema + layout, not schema alone.

This is the verification realization of graph-engine **D7** (`metric` / `prohibition` /
`method_constraint` + `measured_by` / `constrains` / `violated`): D7 designs the *shape* of a
deterministic measurable check; this catalog is the *concrete kind family* that implements it for the
verification plane. (D7 is graph-engine Slice 3, design-only — this node specifies the verification
kinds without waiting on it; where they overlap, the kinds adopt D7's edge names.)

## The common envelope

Every `uacp.check.<type>` shares one envelope; the `params` differ per kind.

```yaml
kind: uacp.check.symbol_resolves      # the catalog member (selects the replay engine)
id: check-7                           # node id; registered in manifest.artifacts
from:                                 # PROVENANCE — what content generated this check (re-derivable)
  target: wu-3                        #   the scope_item / work_unit it proves (the measured_by edge dst)
  basis: "wu-3 'wire up the /settle route'"   # the comprehended intent, recorded for audit
bind: {plane: code, ref: settle_route}        # how to resolve to reality (routed by plane — node 32)
expect: {resolves: true}              # the deterministic predicate the engine evaluates
severity: block                       # block | warn  (ERROR is never PASS — node 31)
```

- **`from.target`** is load-bearing: it is the `measured_by` edge endpoint, so the structural coverage
  gate ([34](34-adequacy-and-coverage.md)) can prove *every* target carries ≥1 check.
- **`from.basis`** is the recorded comprehension — the audit trail of *why this check* ([13](13-investigation-ledger.md)),
  the property that makes the gate re-derivable rather than a black box.
- **`bind`** names the plane + reference; the binder ([32](32-reality-binder.md)) resolves it.
- **`expect`** is pure data the engine compares against the bound reality — no agent code runs at replay.

## The initial catalog (by plane — honest about what binds now)

Buildable **now** (RELATION graph + artifact-content; bind via the projection / `artifact_integrity`):

| kind | proves | params / expect |
|---|---|---|
| `uacp.check.field_equals` | a named field of a bound artifact has the required value | `ref` (artifact+json-path), `expect.value` |
| `uacp.check.field_present` | a required field/section exists and is non-empty | `ref` |
| `uacp.check.edge_exists` | a required graph relation holds (e.g. obligation→work_unit) | `src, rel, dst` |
| `uacp.check.obligation_satisfied` | an obligation has a PASS evidence item not cleared by a block | `oid` (reuses `_check_contradicted` logic) |
| `uacp.check.artifact_integrity` | a referenced artifact exists on disk + matches its watermark | `ref` (the BUILT reality-binder precedent) |

Gated on the **code/SCIP plane** (Codeflair) — designed here, built in Slice 3:

| kind | proves | params / expect |
|---|---|---|
| `uacp.check.symbol_resolves` | a named symbol the work claims to add/wire actually resolves | `ref` (symbol), `expect.resolves` |
| `uacp.check.symbol_referenced_by` | a symbol is actually *used* (not just named) — kills the #503 weak proxy | `ref`, `expect.callers≥1` |
| `uacp.check.behavioral` | a declared behavior holds when exercised (the reality-binding pole) | replay-spec ref; needs a runner |

## Why a CLOSED catalog (the trust argument)

A closed catalog is what keeps the gate auditable and fail-closed: the agent's only freedom is
*selection + parameter binding from content* (the bounded semantic act), not authoring logic. Every
verdict is computed by a reviewed, deterministic engine, so a check cannot "pass" by being cleverly
written. Extending the catalog is a governed change (new `kind` + schema + engine + tests + council) —
not something an agent does mid-run. A guarded `uacp.check.custom_predicate` escape hatch is
deliberately deferred (YAGNI) until a real expressiveness gap is demonstrated; if added, it carries the
heaviest council burden.

## Versioning

The catalog is versioned (a `catalog_version` in config). A frozen check records the version it was
authored under, so a later catalog change cannot silently re-interpret an old check (the class-F
spec↔runner drift guard, applied to the catalog itself). Replay engines must read old checks under
their recorded version.

> YAGNI (council): for Slice 0 ship a single `catalog_version` constant + record it on each check; defer
> any multi-version migration machinery until a second version is actually imminent. The *field* is cheap
> insurance against drift; the *migration engine* is not slice-0 work.

## To build (slice 0)

- Add the `uacp.check.*` schemas (graph + artifact-content kinds) to `engines/domain/schema.py`.
- The shared envelope validator (`from`/`bind`/`expect`/`severity`) + per-kind `params` schema.
- Entity-writer wiring so a `uacp.check.*` write validates + auto-registers (it already does for
  RELATION kinds — confirm the plane assignment).
