# Edge `rel` and `provenance` — the closed vocabularies

> **Read when** writing a node's out-edges or the `_index.yaml` edge list and you need the full,
> canonical `rel` / `provenance` values. Companion to `../SKILL.md`.

An edge is **intra-bundle** and has the shape `{dst, rel, provenance}` in a node's frontmatter, and
`{src, dst, rel, provenance}` in the `_index.yaml`. The lint matches a node edge to its `_index` mirror
on `{dst, rel}` only — `provenance` is `_index`-authored metadata and is not part of the match.

## `rel` — relation type (closed enum)

`motivated_by · decides_on · realizes · depends_on · consumes · extends · sequences · relates_to ·
corrects · grounds · supersedes`

Pick by what the edge *means*:

- **motivated_by** — this node exists because of the dst (an audit/problem that motivated the design).
- **realizes** — this node implements/carries out the dst (a design node realizing the intent).
- **depends_on** — this node needs the dst to make sense or be built first.
- **decides_on** — this node settles a choice about the dst.
- **sequences** — this node comes before/after the dst in a build/reading order.
- **grounds** — this node provides the evidence the dst rests on.
- **consumes / extends / corrects / supersedes / relates_to** — uses, builds-on, fixes, replaces, or a
  generic association with the dst.

## `provenance` — how the edge is known (closed enum)

`derived · parsed · asserted · inferred`

For **hand-authored design bundles** you almost always use:

- **asserted** — a human-made design link (an author claim).
- **derived** — a structural dependency that follows from the artifacts.

`parsed` (extracted from source) and `inferred` (statistically suggested) exist for machine-produced
graphs and rarely appear in a hand-authored design bundle — but they are valid values in the enum.
