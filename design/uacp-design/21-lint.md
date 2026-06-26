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
becomes `uacp-lint`), wired into the same CI job as the other lints. **Schema scope (honest):** the
existing `design_index` schema (`design/graph-engine/schema/design-index.schema.json`) covers the
**`_index.yaml` ONLY** — it says nothing about node `.md` frontmatter or a `type` vocabulary. So the
lint **reuses that schema for `_index`** and adds a **NEW node-frontmatter validator** (required keys +
the two-tier `type` rule below). The "new" part is small but real — do not pretend the schema covers nodes.

## The file model (decides checks 2 + 5)

Per [10](10-taxonomy-audit.md): a bundle's **nodes** are its **top-level `*.md`** (excluding `_index*`).
Nested `*.md` (e.g. `prompts/`, `eval/README.md`) are **sub-assets, out of node scope** — not members,
not subject to node-`type` validation.

## The checks (each is DECIDABLE — that is the entry criterion)

For every `design/<topic>/` bundle:

1. **`_index` exists + conforms** — exactly one `_index.yaml` (not `.md`), validating against the
   `design_index` schema (`kind: design_index`, required fields). The parser is **fail-closed against
   absent keys** — a missing `kind`/`members`/`edges` is a clean violation, not a crash. *(Catches the
   audited `work-unit-status/_index.md`, which has none of the three — a RECONSTRUCT, not a rename.)*
2. **`members == files`** — `_index.members` is exactly the **top-level** `*.md` set (excluding
   `_index*`); nested sub-assets are ignored. No missing, extra, or stale entry.
3. **It is a BUNDLE, not a single doc** — ≥2 member nodes + the `_index`. *(The headline 100+× miss.)*
4. **Placement** — under `design/<topic>/`, never `docs/plans` or a bare `docs/`.
5. **Node frontmatter (two-tier)** — every top-level node has the required keys (`type`, `title`,
   `description`, `tags`, `timestamp`, `edges`). On `type`: **HARD-FAIL** if missing/malformed;
   **WARN-ONLY** if it is an unknown value (allowlist = the CORE set + known one-offs,
   [10](10-taxonomy-audit.md)). The vocabulary is **not closed** in v1 — closing it is a later decision.
6. **Edges mirror** — match key is **`{dst, rel}` only** (`provenance` is `_index`-authored metadata,
   not matched). For each `_index` edge `{src,dst,rel}`, node `src` carries a frontmatter edge
   `{dst,rel}`, and every node out-edge appears in `_index`. A node with `edges: []` (a leaf/root, e.g.
   `00-intent`) is **exempt from the forward direction** — empty is legal. `rel`/`provenance` values
   are from their enums.
7. **Status/Checkpoint — shape-if-present only** — NOT required (soft, per the skill). Presence is
   detected by a `## Status / Checkpoint` heading; if present, it must contain a date. Detecting
   presence + a date is decidable; the lint never judges whether it is a *good* checkpoint.

## Fail-closed + honest scope

- Block-severity on a violation — but **only once the corpus is reconciled**
  ([22](22-rollout-and-decisions.md)); until then it runs as a report + an allowlist.
- It validates **structure, never semantics** — never decomposition quality, over-serialization, or
  single-source (that is the skill + council). Entry criterion for any check: "deterministically
  decidable from the files." (A decidable *slice* of the reference boundary — that a cross-bundle link
  RESOLVES to an existing file — is a candidate future check; duplication-detection stays judgment.)
- **Dogfood:** this `uacp-design` bundle must itself pass the lint — the first conformance case.

## To expand
- Exact violation codes (e.g. `DESIGN_INDEX_MISSING`, `DESIGN_MEMBERS_MISMATCH`, `DESIGN_SINGLE_DOC`,
  `DESIGN_NODE_TYPE_MISSING` vs `_UNKNOWN`, `DESIGN_EDGE_UNMIRRORED`) — pinned at build (TDD), not here.
- Whether the lint `--fix`es trivial cases (members-list drift), or report-only.
