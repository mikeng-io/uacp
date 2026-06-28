# Design bundle — Artifact content/relation model

**Status:** REWORK — parked pending B1/B2 operator decision (see [08-review-findings](08-review-findings.md)). Lifecycle-executability fixes split out as a separate higher-priority initiative.
**Origin:** brainstorm run `acrs-20260628` (vault: `.uacp/brainstorm/acrs-20260628/`)
**Branch:** `design/artifact-content-relation-split`

## One-line thesis
Markdown carries **semantic content** (what an agent/council *comprehends*); YAML carries
**relations** (ids, edges, anchors, deterministic scalars — what the gate *measures*).
This is `comprehend → measure` (the CMS core principle) applied to the artifact layer.

## Why
Today an artifact's substance is split three ways, and the surface council *reviews*
(Markdown) barely overlaps the surface the gate *measures* (YAML). `field_present` checks
a YAML prose field is non-empty — a weak proxy the principle warns against. After council,
remediation lands in gate-invisible Markdown. See [01-problem](01-problem.md).

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

## Authority / scope boundary
- This bundle is DESIGN only — no kernel/schema/skill code changes here; build is a later run.
- Council-required (Invariant #4, kernel + schema + all lifecycle skills), cross-provider reviewer.
- The authority model is UNCHANGED: semantics judged by council, relations by the gate.

## Out of scope
Hard cutover; eager migration of in-flight on-disk runs; a standalone sanitizer patch for
evidence_disposition (would reinforce the model being replaced); changing council/gate authority.
