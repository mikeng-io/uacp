# Design bundle — Artifact content/relation model

**Status:** Slices 0–2 BUILT + MERGED — PR #70 / `c7bd737` / 2026-06-29. Council returned REWORK and deferred B1/B2 to the operator ([08-review-findings](08-review-findings.md)); operator chose **B1**; the central blocker was settled by experiment on the hardest gate ([09-grounding-retarget-experiment](09-grounding-retarget-experiment.md), commit `da86643`); gate-side substrate (blast-radius confirmation, anchor primitive, anchor-bound `field_present`) shipped. **Pending:** wire codeflair as the real oracle ([10-implementation-roadmap](10-implementation-roadmap.md) Phase 1 / [11-full-scope-build-plan](11-full-scope-build-plan.md) Slice 3). Lifecycle-executability fixes remain a separate sibling initiative.
**Origin:** brainstorm run `acrs-20260628` (vault: `.uacp/brainstorm/acrs-20260628/`)
**Branch:** `design/artifact-content-relation-split`

## One-line thesis
Markdown carries **semantic content** (what an agent/council *comprehends*); YAML carries
**relations** (ids, edges, anchors, deterministic scalars — what the gate *measures*).
This is `comprehend → measure` (the CMS core principle) applied to the artifact layer.

## Why
Today an artifact's substance is split three ways, and the surface council *reviews*
(Markdown) barely overlaps the surface the gate *measures* (YAML). `field_present` checks
a YAML prose field is non-empty — a proxy the principle warns against as the sole review surface.
After council, remediation lands in gate-invisible Markdown. The shipped design **relocates** this
presence check to an anchored MD section (same presence semantics, aligned surface); it does not
remove presence-checking. See [01-problem](01-problem.md).

## Nodes
| node | covers |
|---|---|
| [01-problem](01-problem.md) | the as-built 3-category split + the boundary violation, grounded in code |
| [02-model](02-model.md) | the canonical content(MD) vs relations(YAML) rule, per artifact kind |
| [03-anchor-primitive](03-anchor-primitive.md) | the YAML relation-node → MD section anchor; schema + projection |
| [04-check-retarget](04-check-retarget.md) | `field_present` binds to an anchored MD section, not a YAML prose field |
| [05-migration](05-migration.md) | additive ratchet (not cutover); legacy YAML prose stays optional |
| [06-evidence-disposition-case](06-evidence-disposition-case.md) | the concrete first instance (the live unwriteable-file bug) |
| [07-blast-radius-open-questions](07-blast-radius-open-questions.md) | measured surface + the must-resolve-early questions |
| [08-review-findings](08-review-findings.md) | council verdict (REWORK) + the B1/B2 fork deferred to the operator |
| [09-grounding-retarget-experiment](09-grounding-retarget-experiment.md) | the B1 viability proof — plan / outcome / measurement (claim-vs-witness; independence finding) |
| [10-implementation-roadmap](10-implementation-roadmap.md) | the gate-side (meaning-witness) build — codeflair oracle (P1) → prevention (P2) → semantic witness + generalise (deferred) |
| [11-full-scope-build-plan](11-full-scope-build-plan.md) | the WHOLE-bundle sliced ratchet (slices 0–5), each with measurement · verify · invariant · constraint |

## Authority / scope boundary
- Gate-side build for Slices 0–2 has shipped (PR #70 / `c7bd737`); remaining slices (3–5) are future runs. This bundle stays design-only for content not yet built.
- Council-required (Invariant #4, kernel + schema + all lifecycle skills), cross-provider reviewer.
- The authority model is UNCHANGED: semantics judged by council, relations by the gate.

## Out of scope
Hard cutover; eager migration of in-flight on-disk runs; a standalone sanitizer patch for
evidence_disposition (would reinforce the model being replaced); changing council/gate authority.
