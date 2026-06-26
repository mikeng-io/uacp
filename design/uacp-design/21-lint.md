---
type: contract
title: The design-bundle lint — the decidable structure gate
description: The exact, deterministic checks the design-bundle lint enforces in uacp-lint (validate_uacp_artifacts.py) — only the decidable structure (schema conformance, members==files, edges mirror, >=2 nodes, placement, valid node type). Fail-closed, staged per the rollout. The measure half of the split.
tags: [uacp-design, lint, validation, uacp-lint, gate, contract]
timestamp: 2026-06-26
edges:
  - {dst: 00-intent, rel: realizes, provenance: asserted}
  - {dst: 10-taxonomy-audit, rel: depends_on, provenance: derived}
---

# The design-bundle lint — the decidable structure gate

## Where it lives

A validator in `skills/uacp-core/scripts/.../validate_uacp_artifacts.py` (the 27-validator set that
becomes `uacp-lint`), wired into the same CI job as the other lints. It REUSES the existing
`design_index` schema (`design/graph-engine/schema/design-index.schema.json`) — it does not invent a
new one.

## The checks (each is DECIDABLE — that is the entry criterion)

For every `design/<topic>/` bundle:

1. **`_index` exists + conforms** — there is exactly one `_index.yaml` (not `.md`), and it validates
   against the `design_index` schema (`kind: design_index`, required fields). *(Catches the audited
   `_index.md` non-conformer.)*
2. **`members == files`** — `_index.members` is exactly the set of `*.md` node files (no missing, no
   extra, no stale entry).
3. **It is a BUNDLE, not a single doc** — ≥2 member nodes + the `_index`. *(The headline 100+× miss.)*
4. **Placement** — it is under `design/<topic>/`, never `docs/plans` or a bare `docs/`.
5. **Node frontmatter** — every node has the required keys (`type`, `title`, `description`, `tags`,
   `timestamp`, `edges`) and a `type` in the **closed canonical set** ([10](10-taxonomy-audit.md)).
6. **Edges mirror** — every edge in `_index.edges` has a matching out-edge in the named node's
   frontmatter, and vice versa (the graph is consistent); edge `rel`/`provenance` are from their enums.
7. **Status/Checkpoint — shape-if-present only** — NOT required (soft, per the skill), but IF a bundle
   has a Status/Checkpoint block it must be well-formed (dated). No retroactive requirement.

## Fail-closed + honest scope

- Block-severity on a violation (a malformed/incomplete bundle is a fail-closed lint error) — but
  **only once the corpus is reconciled** ([22](22-rollout-and-decisions.md)); until then it runs as a
  report + an allowlist.
- It validates **structure, never semantics** — it cannot and does not judge decomposition quality,
  over-serialization, or single-source (that is the skill + council). The entry criterion for any
  check here is "deterministically decidable from the files."
- **Dogfood:** this `uacp-design` bundle must itself pass the lint — the first conformance case.

## To expand
- Exact violation codes (e.g. `DESIGN_INDEX_MISSING`, `DESIGN_MEMBERS_MISMATCH`, `DESIGN_SINGLE_DOC`,
  `DESIGN_NODE_TYPE_UNKNOWN`, `DESIGN_EDGE_UNMIRRORED`) — pinned at build (TDD), not here.
- Whether the lint also fixes-with-`--fix` the trivial cases (members list drift), or report-only.
