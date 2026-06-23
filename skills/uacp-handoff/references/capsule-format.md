---
description: >
  The OKF capsule shape for uacp-handoff — frontmatter (with anchors as typed
  edges), the six body sections, and the inclusion contract. Read when writing or
  validating a handoff capsule. The authoritative design is
  design/handoff/10-capsule-format.md; the empty form is ../assets/handoff-template.md.
kind: reference
---

# Handoff Capsule Format (reference)

A capsule is an **OKF node**: YAML frontmatter + Markdown body, at
`.uacp/handoffs/<workstream>.md`, **one per workstream, overwritten in place**.
Authoritative design: `design/handoff/10-capsule-format.md`. Empty form:
`../assets/handoff-template.md`.

## Frontmatter

| Key | Meaning |
|---|---|
| `kind: handoff` | the node kind |
| `workstream` | stable identity (= filename, kebab-case) |
| `title` | one line: what this workstream is |
| `status` | `active` \| `resolved` \| `superseded` (D18 lifecycle) |
| `scope.in` / `scope.out` | what the workstream is / is not |
| `attribution.generated_by` | `{agent, model, runtime}` |
| `attribution.updated_at` | recency (`YYYY-MM-DD`) |
| `edges` | **the anchors** — typed links to reconstructable refs |

### Anchors = typed edges

Anchors are the ONLY place reconstructable references live. Each is
`{dst, rel, provenance}`:

- `provenance: parsed` — code/git facts: `branch:<b>`, `commit:<sha>`.
- `provenance: asserted` — human links: `design/<bundle>/<node>`, another capsule.
- `provenance: derived` — FK to a governed artifact: `run:<run_id>`.

Common `rel`: `anchored_to` (branch/commit), `relates_to` (design node),
`derived_from` (run), `superseded_by` (a successor capsule). This makes the capsule
a first-class node in UACP's graph.

## Body — six sections (non-reconstructable ONLY)

`Intent` · `Decisions & rationale` (`[locked]`/`[open]`) · `Rejected / not-this`
(why-not) · `Open threads & watch-outs` · `Now → next` (pointer + next intent) ·
`Anchors` (rendered mirror of `edges`).

## The inclusion contract (per line)

> Recoverable from the commits/diff/status? → **anchor** (an edge), never body.
> Requires human input to recover (why / decision / rejected-path / intent /
> judgment / watch-out)? → a **body section**.

If a capsule starts listing files changed or mechanical steps, it is violating the
contract — move those to anchors.
