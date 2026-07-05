# Phase 4 — Candidate approaches

## A — Document the dual-surface update contract (only)
Add a "revising artifacts after council" contract to the skills: which writer for
which surface, governed re-write keeps integrity, `artifacts.md` is the drift guard.
- **Pro:** cheap, no schema/code change, unblocks agents today.
- **Con:** does NOT fix the root — the gate still can't see the surface council reviews;
  cat-2 duplication and cat-3 gate-invisibility remain. Treats the symptom.
- **Verdict:** necessary stop-gap, insufficient as the answer.

## B — Single-source: MD=semantic content, YAML=relations+anchors  ← operator's model
Each concern has ONE home. YAML carries ids, edges (`derives_from`, `measured_by`),
**anchors** (pointers to MD sections), and deterministic scalars. MD carries all
semantic substance. The gate measures relations/topology; council judges semantics;
`field_present` retargets to "the anchored MD section resolves & is non-empty."
- **Pro:** removes duplication, makes the reviewed surface the measured surface,
  removes the weak `field_present`-on-prose proxy, aligns with the CMS principle.
- **Con:** real change — touches projection.py + schema + check kinds + skills + tests.
- **Verdict:** the principled fix. Selected direction.

## C — Bind checks to MD sections (only)
Extend `field_present` to bind to an MD heading/section.
- **Verdict:** not a standalone approach — it is the *check-retarget mechanism inside B*.
  Absorbed into B as one component (needs the anchor primitive to be meaningful).

## Cross-cutting lever (applies to B): additive ratchet vs hard cutover
- **Additive ratchet (chosen):** add `anchor`; teach `field_present` an MD-section mode;
  keep YAML `statement` optional/legacy. Old artifacts still validate; the 18 tests
  mostly keep passing; coverage is ADDED, not rewritten. UACP's own established
  migration shape (validate-on-write ratchet, schema ratchet).
- **Hard cutover (rejected):** remove prose from YAML now → rewrite all 18 tests +
  migrate in-flight runs + breaking change. No reason to take this cost.

## Missing primitive that makes B work: the ANCHOR
A stable pointer from a YAML relation-node to its MD content home, e.g.
`scope.in_scope[].anchor: "proposals/{run_id}/01-intent-scope.md#si-1"`.
Same idea as the handoff skill's "anchors-as-edges" and codeflair's `code_anchor`.
