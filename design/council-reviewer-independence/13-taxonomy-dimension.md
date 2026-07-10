---
type: design
title: The pull-vs-push axis — identified now, serialized later (DEFERRED with the teeth)
description: council-taxonomy.md's Diversity Dimensions (role/model/runtime/toolchain/evidence-channel/debate-layer) has no axis for grounding independence — pushed narrative vs pulled grounding. This node NAMES the gap (which alone dissolves the "Tier>=2 therefore independent" confusion) but DEFERS committing the vocabulary to the canonical taxonomy until the check that makes `pull` truthful exists. Serializing canonical vocabulary for an unverifiable property would be premature.
tags: [taxonomy, diversity-dimensions, pull-vs-push, deferred, vocabulary]
timestamp: 2026-07-10
edges:
  - {dst: 11-grounding-provenance, rel: depends_on, provenance: derived}
  - {dst: 00-problem, rel: motivated_by, provenance: asserted}
---

# The pull-vs-push axis

## The gap (real, and worth naming now)

`council-taxonomy.md`'s Diversity Dimensions are `role`, `model`, `runtime`, `toolchain`,
`evidence-channel`, `debate-layer`; each council artifact records the active set in `diversity_sources`.
There is **no dimension for grounding independence** — whether the reviewer's understanding was *pushed*
to it (orchestrator narrative) or *pulled* by it (retrieved from the artifact).

This absence is *why* the confusion in [[00-problem]] was possible: "external reviewer" collapsed into
"runtime diversity" because runtime is the only nearby axis. But a Tier-2 dispatch can have full
runtime + model + toolchain diversity and still be push-grounded. Pull-vs-push is genuinely orthogonal to
runtime: you can swap the runtime and keep pushing; you can (with [[10-minimal-non-leading-dispatch]])
keep the runtime and switch toward pull. **Naming the axis is the cheap, high-value part** — it dissolves
the "Tier >= 2 therefore independent" anti-pattern regardless of what else gets built.

## Decision: name now, serialize later (DEFERRED)

Split the change in two, and only do the first now:

- **NOW (documentation, Slice 1-adjacent):** state, in prose in this bundle and optionally as a one-line
  note in `council-taxonomy.md`'s anti-patterns, that runtime-swap ≠ grounding independence, and that
  "Tier >= 2 therefore independent" is a fallacy. This carries no enforcement claim and cannot overclaim.
- **DEFERRED (with [[11-grounding-provenance]]):** adding `pull` as a first-class Diversity Dimension and
  recording it in `diversity_sources`. This must wait, because a recorded `pull` is only honest if it is
  backed by the check — and per [[11-grounding-provenance]] that check does not yet work. Serializing
  canonical vocabulary (authority-layer 2) for a property nothing can truthfully assert would be premature
  serialization: the dimension would certify independence the system cannot yet measure.

The rule when it does land: record `pull` **only** when the (path-scoped, evidence-beyond-diff) provenance
check actually passes — the dimension is backed by the same teeth, not by intent.

## Why a node, not a silent deferral

Recording the axis (even deferred) is the payload: it gives the "runtime-swap = independence" fallacy a
named home and prevents the next person from re-deriving the wrong mental model. The enforcement that makes
`pull` truthful lives in [[11-grounding-provenance]]; this node does not re-specify it, and commits no
canonical-vocabulary change until that exists.
