# 11 — Full-scope build plan (B1, sliced)

The whole-bundle build trail. Realises the model ([02-model](02-model.md)) across every surface
in the blast radius ([07-blast-radius-open-questions](07-blast-radius-open-questions.md)) as an
**additive ratchet** ([05-migration](05-migration.md)) — never a cutover. Node 10 is the deep dive
on one slice (the meaning-gate witness); this node is the master sequence. Each slice carries the
four axes: **measurement · verify/validate · invariant · constraint.**

## The structural split that shapes the slices

Gates that touch prose are **not one problem**. Two kinds, two treatments:

- **Presence gates** — assert "content exists here" (`field_present` on a prose field; `schema`
  `statement`-required). Retarget = bind to an **anchored MD section** (resolves + non-empty).
  Deterministic, no witness. Slices 1–2.
- **Meaning gates** — derive *meaning* from the prose (`class-underclaim` only). Presence is not
  enough; they need an **independent witness** (codeflair / semantic). Retarget = claim-vs-witness.
  Slice 3 (= node 10).

Getting this split right is what keeps the heavy witness machinery scoped to the one gate that
actually needs it, instead of every gate.

> **Slice 0 result (2026-06-30, grounded):** of the prose-reading gates the council named, **only
> `class-underclaim` reads meaning** (`candidate_class` in `manifest/projection.py`). D43
> `_scope_concern_is_keyed` (in `heartgate/validators/adaptive_gates.py`) checks
> `statement is not None` — **presence, not meaning**; `domain/schema.py` `uacp.proposal` scope
> requires `["id","statement"]` — **presence**; `heartgate.py` gate handlers only consume D43's
> boolean — structure.
> ⇒ D43 + schema-required move to **Slice 2** (anchor-bound presence, no witness); the codeflair
> witness (Slice 3) narrows to a **single gate**. The risky surface shrank. *(Slice 0's remaining
> question — do `heartgate.py`/`adaptive_gates.py` read scope content elsewhere — answered: no, only
> the structural `is not None` / boolean reads above.)*

---

## Slice 0 — Blast-radius confirmation (precondition, read-only) ✅ SHIPPED — PR #70 / `c7bd737` / 2026-06-29

Resolve open question #1 ([07](07-blast-radius-open-questions.md)): do `heartgate.py` /
`adaptive_gates.py` read scope **content** or only **structure**? This sizes everything.

- **Measurement:** a grounded yes/no per file — does it read `in_scope`/`objective`/`statement`
  *text*, or only ids/edges/structure? Each answer cites file:line.
- **Verify/validate:** LSP `findReferences` + grep on `in_scope`/`objective`/`statement`,
  reconciled (suite decides on disagreement); findings recorded in this bundle.
- **Invariant:** no later slice proceeds on an *assumed* radius — the map is grounded first.
- **Constraint:** read-only; zero code change; output is a finding, not an edit.

## Slice 1 — Anchor primitive, inert (migration stage 1) ✅ SHIPPED — PR #70 / `c7bd737` / 2026-06-29

Schema accepts optional `anchor`; projection records an `anchored_to` edge; section-resolution is
a deterministic read. Nothing requires it yet. ([03-anchor-primitive](03-anchor-primitive.md))

- **Measurement:** a run with anchored nodes projects `anchored_to` edges; an anchor pointing at a
  missing/empty section **FAILs** (not a silent pass); full suite green (purely additive).
- **Verify/validate:** projection unit tests (anchor resolves / anchor-at-nothing fails); schema
  accept+reject tests; non-vacuity (delete the section body → the fail fires).
- **Invariant:** anchor-points-at-nothing is FAIL, never silent ([03] property 1); **one-directional
  authority** — YAML names the anchor, MD never declares relations.
- **Constraint:** optional/inert — zero behavior change for existing runs; no prose removed; same
  trust class as the existing `artifact_integrity` watermark read.

## Slice 2 — Presence retarget: `field_present` → anchored MD (migration stage 2) ✅ SHIPPED (gate-side substrate) — PR #70 / `c7bd737` / 2026-06-29

`field_present` gains an anchor binding mode, opt-in per check. (`field_equals` combined with an
anchor is a fail-closed ERROR in the as-built implementation — anchor mode is `field_present`-only.)
**What shipped:** the anchor-binding substrate for `field_present` checks. **Pending (not delivered
by Slice 2):** the D43 `_scope_concern_is_keyed` and schema `statement`-required opt-in wiring is
still forward plan — the shipped slice provides the substrate; per-gate opt-in flip is the next
step within Slice 2. ([04-check-retarget](04-check-retarget.md))

- **Measurement:** an anchor-bound check passes iff the section resolves + is non-empty; bound to a
  missing/empty section → FAIL; relational checks (`measured_by`, no-orphan, no-dropped-intent)
  unaffected.
- **Verify/validate:** check-replay tests on anchor-bound checks; non-vacuity (empty section fails);
  the existing ~18 tests stay green (added coverage, not rewritten).
- **Invariant:** the check asserts **only** deterministic facts (resolves / non-empty / header) —
  *adequacy stays council's call* ([02] non-negotiable: no semantic claim measured by a structural
  proxy).
- **Constraint:** opt-in per check; YAML prose path still valid (legacy); no kind is forced yet.

## Slice 3 — Meaning-gate witness retarget (= node 10)

The claim-vs-witness pattern for `class-underclaim` (the sole meaning gate, per Slice 0). Proven viable in
[09-grounding-retarget-experiment](09-grounding-retarget-experiment.md); full build sequence
(codeflair oracle → prevention → semantic witness → generalise) in
[10-implementation-roadmap](10-implementation-roadmap.md). Axes summarised here:

- **Measurement:** the gate catches under-claim / under-scope via an **independent witness**
  (codeflair `entailed_class`), not prose; `oracle_source` is the grounded relation; floor/escalate
  synthesis behaves. *(As-built from P0: synthesis is `entailed_class` vs the legacy prose
  keyword-match; the semantic-witness CEILING is deferred within Slice 3.)*
- **Verify/validate:** the P0 experiment (2202 green) + codeflair-wired tests at the new boundary;
  **Invariant #4 council + cross-provider** (kernel change).
- **Invariant:** deterministic floor cannot be overridden; synthesis is `max(floor, ceiling)` **in
  code, never an agent**; correctness ≠ conformance (out-of-scope-but-correct = flag → re-declare).
- **Constraint:** codeflair grounds **structure only** (the `wires_symbol` boundary);
  `changes_behavior` / doc-only fall to the deferred semantic witness; assumes a fresh codeflair
  index.

## Slice 4 — First full kind: evidence_disposition (migration stage 3–4)

Convert `evidence_disposition`: `cluster`/`half` become **typed YAML relations + anchors**, content
in MD; gate checks relations, not hyphenated filenames. Fixes the live unwriteable bug **and** the
`half: left|right` doc fiction in main. ([06-evidence-disposition-case](06-evidence-disposition-case.md))

- **Measurement:** both halves are writeable through governed writers; the VERIFY→RESOLVE gate
  passes iff both halves present + anchors resolve + assumptions has no unowned-pending rows; the
  hyphen-filename path is gone for this kind.
- **Verify/validate:** the empirical write test (both halves write — the bug reproduces red first,
  then green); VERIFY→RESOLVE gate tests; non-vacuity (drop a half → block).
- **Invariant:** **no relation data encoded in filenames**; governed-writers-only still holds; no
  self-attesting closure.
- **Constraint:** this kind only (per-kind ratchet); other kinds' paths untouched; the doc-fiction
  correction lands with the model change, not separately.

## Slice 5 — Per-kind tighten, then (much later) retire legacy prose (stages 4–5)

Once a kind's producers + consumers are all anchor-aware, make the anchor the **floor** for that
kind. Retire legacy YAML prose fields only when no producer emits them.

- **Measurement:** per kind, a non-anchored artifact of a *converted* kind FAILs; removing a legacy
  prose field leaves the suite green (no producer/consumer still reads it).
- **Verify/validate:** per-kind ratchet tests; council per kernel/schema change; grep proof that no
  producer emits the retired field before removal.
- **Invariant:** additive until a kind is *fully* converted; each stage independently shippable +
  reversible; suite green at every stage.
- **Constraint:** no eager migration of in-flight on-disk runs; legacy optional-prose path stays
  until stage 5; never a big-bang.

---

## Sequence logic

0 grounds the radius → 1 lays the anchor substrate everything else needs → 2 (presence) and 3
(meaning) are **independent** retargets on top of the substrate and can proceed in parallel → 4 is
the first end-to-end kind conversion (smallest, cleanest, fixes a live bug) → 5 is the slow tail.
Slices 3-P3, 3-P4, and 5 are the deferred/heaviest; 0–2 + 4 are the near-term, each green and
additive. The boundary redesign never lands as one big bang.
