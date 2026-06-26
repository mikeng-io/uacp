---
type: adr
title: Design-bundle convention — codified and gated by decidability
description: Establish the design-bundle convention (design/<topic>/ = decomposed facet nodes + _index) as a gated invariant, split by decidability into a uacp-design SKILL (judgment) and a design-bundle LINT (decidable structure). Motivated by 100+ violations of the guidance-only form. Gets the same treatment as uacp-skills (ADR-0017).
tags: [design-bundles, convention, lint, uacp-design, decidability]
timestamp: 2026-06-27
status: accepted
---

# ADR-0020 — Design-Bundle Convention: Codified and Gated by Decidability

## Metadata

- **Status**: accepted
- **Date**: 2026-06-27
- **Decision Makers**: UACP maintainer
- **Consulted**: design/uacp-design/ (the scoping bundle); ADR-0017 (uacp-skills precedent)
- **Related**: design/uacp-design/; ADR-0017 (skill-authoring convention)

## Context and Problem Statement

"A UACP design is a decomposed bundle under `design/<topic>/` — facet nodes + an `_index.yaml`
— never a single doc, never `docs/plans`" is a **documented** convention (`CONTRIBUTING.md`,
the `design_index` schema, memory notes) that has been violated **100+ times**, including by
this agent. That is the empirical proof that **guidance-only does not hold**.

UACP's own thesis says why: *determinism belongs to the gate, not the agent's judgment.*
Relying on the author to remember the convention is the self-attestation pattern UACP exists to
kill.

An as-built audit (`design/uacp-design/10-taxonomy-audit.md`) confirmed drift in the live
corpus: a non-conforming `_index.md` (no `kind:design_index`, no `members`, no `edges`); a
node-type sprawl of 11 values; and widespread edge-mirror drift. The audit also established the
correct file model: a bundle's **nodes** are its **top-level `*.md`** (excluding `_index*`);
nested files (e.g. `prompts/`, `eval/README.md`) are sub-assets, out of node scope.

## Decision Drivers

- The 100+× violation rate proves the guidance-only bar is empirically failed.
- Decidable structure violations (wrong placement, missing `_index`, single doc, members drift,
  edge-mirror drift) are **fully automatable** — they must be gated.
- Judgment violations (poor decomposition, over-serialization, propagation) are **not decidable**
  from the files — a lint cannot catch them; a skill must teach them.
- The right split is by **decidability** — matching UACP's own comprehend→measure→serialize
  principle applied to design authorship.
- Precedent: ADR-0017 (uacp-skills) is exactly this shape — a skill paired with hard lints.

## Considered Options

1. **Guidance-only (status quo)** — *rejected.* Already proven empirically failed at 100+×
   violation rate.
2. **Lint-only** — *rejected.* The lint can gate structure but cannot teach decomposition quality,
   anti-propagation discipline, or over-serialization. A skill is needed for the non-decidable half.
3. **Skill-only** — *rejected.* Without a deterministic gate, the same guidance-only failure
   recurs. The 100+× miss is structural (wrong placement, single doc), not a teaching failure.
4. **Skill + decidable-structure lint (chosen)** — matches UACP's split: skill owns judgment;
   lint owns decidable structure. Same shape as ADR-0017.

## Decision Outcome

Codify the design-bundle convention as:

- **`uacp-design` skill** (`kind: reference`) — the judgment layer. Teaches decomposition
  quality, node shape, the reference boundary, the Status/Checkpoint pattern, and design-review
  anti-patterns (propagation, over-serialization). Does NOT re-implement the decidable checks
  (its own single-source rule).

- **Design-bundle lint** (`engines.domain.design_lint`, wired into `uacp-lint` / CI) — the
  measure layer. Enforces the 7 decidable checks (see below). Fail-closed on violation; staged
  rollout (REPORT → RECONCILE → ENFORCE) so the gate never lands on an unvalidated corpus as a
  red wall.

### The 7 decidable checks

| ID | Severity | Check |
|---|---|---|
| DESIGN_INDEX_MISSING / DESIGN_INDEX_MD_NOT_YAML | error | Exactly one `_index.yaml` (not `.md`); fail-closed on absent `kind`/`members`/`edges` keys |
| DESIGN_INDEX_SCHEMA_VIOLATION | error | `_index.yaml` validates against `design-index.schema.json` |
| DESIGN_MEMBERS_MISSING / DESIGN_MEMBERS_EXTRA | error | `_index.members` == top-level `*.md` set (excluding `_index*`); nested sub-assets ignored |
| DESIGN_SINGLE_DOC | error | ≥2 member nodes (the 100+× miss: single-doc is not a bundle) |
| DESIGN_WRONG_PLACEMENT / DESIGN_NESTED_PLACEMENT | error | Bundle under `design/<topic>/`; not nested, not `docs/plans` |
| DESIGN_NODE_TYPE_MISSING / DESIGN_NODE_TYPE_MALFORMED | error (hard-fail) | Every top-level node has required frontmatter keys; `type` present + non-empty |
| DESIGN_NODE_TYPE_UNKNOWN | warn only | `type` value not in the known vocabulary (vocabulary not closed in v1) |
| DESIGN_EDGE_UNMIRRORED / DESIGN_EDGE_NOT_IN_INDEX | error | Edges mirror on `{dst, rel}` only; a node with `edges: []` is exempt from the forward direction; `rel`/`provenance` values must be in schema enums |
| DESIGN_CHECKPOINT_NO_DATE | error | If a `## Status / Checkpoint` heading is present, the section must contain a YYYY-MM-DD date (absence is fine) |

### Settled scoping decisions

1. **ADR — yes.** This ADR establishes the convention (as ADR-0017 did for skills).
2. **Lint coverage — all `design/**/`, staged.** Not new-only. Via reconcile-then-enforce.
3. **Status/Checkpoint — SOFT.** Skill-recommended; lint validates shape-if-present only.
4. **Node `type` taxonomy — two-tier, CORE derived, vocabulary NOT closed in v1.** CORE set:
   `analysis | design | contract | reference | decision | pattern`. One-offs `roadmap | lessons |
   evidence` are warn-only; folding/closing the vocabulary is deferred to the REPORT pass.

### Rollout

1. **REPORT** — lint runs in report-only mode over all `design/**/`; produces the violation
   inventory (this PR provides it).
2. **RECONCILE** — fix cheap violations in a focused PR; grandfather genuine debt in a tracked
   allowlist (each entry: name + reason; allowlist is itself linted for staleness).
3. **ENFORCE** — flip lint fail-closed in CI once the corpus (minus allowlist) is clean.
4. **DOGFOOD** — `design/uacp-design/` must pass before enforce; it passes as of this PR.

## Consequences

- **Positive:** single enforced gate for the structure half of the convention; the 100+× miss is
  now a CI blocker for new bundles; the dogfood bundle (`design/uacp-design/`) passes as the
  first conformance case; the violation inventory is produced by the REPORT mode (first run: 58
  errors across 7 bundles — the reconcile PR will address them).
- **Negative / risks:** 7 of 10 existing bundles need reconciliation before enforce can flip.
  The allowlist is a debt ledger, not a silent opt-out; each entry carries a reason and is
  checked for staleness.
- **No runtime-behavior change:** this is documentation/lint structure only.
- **Precedent:** same shape as ADR-0017 — a skill + hard lints. If review later finds the
  judgment half too thin for a standalone skill, the fallback is a `references/` page under
  `uacp-skills`.
