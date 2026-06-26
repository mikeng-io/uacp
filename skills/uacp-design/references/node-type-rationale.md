# Node `type` — the set, and why the vocabulary is not closed

> **Read when** choosing a node's `type`, or wondering why the lint only *warns* (not fails) on an
> unknown `type`. Companion to `../SKILL.md`.

## The CORE set (derived from the as-built corpus, not invented)

`analysis | design | contract | reference | decision | pattern`

These are the recurring, non-redundant node types found across the existing `design/*/` bundles.
`design-node` is a duplicate of `design` (reconciled away). Pick the one that names the node's *job*:

- **analysis** — investigates / surveys / grounds (an audit, a gap analysis, an as-built study).
- **design** — proposes structure or behavior (the spine, a roadmap, a sub-system design).
- **contract** — pins an interface/check/schema the build must satisfy (a lint spec, an API shape).
- **reference** — a lookup digest (a glossary, an enum table) cited by other nodes.
- **decision** — records a settled choice + its rationale (a mini-ADR inside the bundle).
- **pattern** — a reusable shape/idiom the bundle establishes.

## Why the vocabulary is NOT closed in v1 (two-tier)

The lint **hard-fails** on a missing/malformed `type` (that is decidable and uncontroversial), but only
**warns** on an unknown value. The set is deliberately left open because closing it prematurely is the
exact mistake the framework already made and reverted once (inventing doc-kinds that did not match the
as-built). A few **one-off** types exist in the corpus (`roadmap`, `lessons`, `evidence`); they are
**deferred, not folded** — e.g. folding `evidence`→`analysis` would erase the one distinction the
framework's *evidence, not assertion* thesis cares about most. Closing the vocabulary is a later
decision, taken only after a full corpus survey — not asserted now.

## Sub-assets are not nodes

Nested files under a subdir (e.g. `prompts/`, an `eval/README.md`) are **sub-assets**, not nodes —
they are out of the node-`type` scope and are not bundle members. A type like `prompt` therefore never
needs to be in this set.
