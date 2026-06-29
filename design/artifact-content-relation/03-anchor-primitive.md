---
type: design
title: "The Anchor Primitive — YAML relation-node to Markdown section"
description: "Specifies the anchor as the join between a YAML relation-node and its Markdown content section: resolvable, stable, one-directional. Covers projection support, prior art in-repo, and the deferred serialization details."
tags: [anchor, primitive, yaml, markdown, projection, design, join]
timestamp: 2026-06-30
edges:
  - {dst: 02-model, rel: realizes, provenance: asserted}
---
# 03 — The anchor primitive

The anchor is the join that makes the model work: a stable pointer from a YAML
relation-node to the Markdown section that holds its content.

## Shape (illustrative — build decides exact serialization)
```yaml
# proposal.yaml  (relations surface)
scope:
  in_scope:
    - id: si-1
      anchor: "proposals/{run_id}/01-intent-scope.md#si-1"   # → content home
```
```markdown
<!-- proposals/{run_id}/01-intent-scope.md  (content surface) -->
## si-1
Root plugin.yaml + __init__.py shim at repo root so `hermes plugins install` …
```

## Properties the design must guarantee
1. **Resolvable + checkable.** Anchor resolution is itself a *relation* the projection
   engine can verify: the target file + section must exist and be non-empty. An anchor
   that points at a missing/empty section is a FAIL, not a silent pass (this is how we avoid
   re-introducing a *new* drift — the anchor-points-at-nothing failure mode).
2. **Stable.** The section key (`#si-1`) is the same id as the YAML node, so the two are
   bound by identity, not by position or fuzzy text match.
3. **One-directional authority.** YAML names the anchor; MD holds the content. The MD never
   declares its own relations (no relations smuggled back into prose).

## Projection support
`projection.py` gains: when it reads a relation-node carrying an `anchor`, it records an
`anchored_to` edge (node → md-section) so the graph + the check engine can reason about it.
Section resolution (file exists, heading present, body non-empty) is a deterministic read,
same trust class as the existing `artifact_integrity` watermark read.

## Prior art in-repo (not new ground)
- the handoff skill's "anchors-as-edges" idea,
- codeflair's `code_anchor` (checkpoint → code symbol),
- existing MARKDOWN kinds (`uacp.intent`, `evidence_disposition`) already prove MD content
  artifacts are first-class.

## Open: serialization details deferred to build
Exact anchor syntax (path#fragment vs structured {file, section}), and whether anchors live
inline on each node or in a sidecar map, are BUILD decisions — tests will arbitrate. This
node fixes the *contract* (resolvable, checkable, stable, one-directional), not the syntax.
