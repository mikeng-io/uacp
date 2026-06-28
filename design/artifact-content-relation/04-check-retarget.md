# 04 — Retargeting field_present to Markdown

## Today
`field_present` binds to a YAML field path and asserts it is non-empty
(`projection.py` check-replay: `_read_path(loaded.value, ref.path)` on a loaded **dict**).
MD can't be a target — it has no field paths.

## The change
`field_present` (and where appropriate `field_equals`) gains a binding mode that resolves an
**anchored MD section** and asserts the deterministic floor:
- the anchor resolves (file + heading exist),
- the section body is non-empty.

```yaml
bind:
  ref:
    anchor: "proposals/{run_id}/01-intent-scope.md#si-1"
```

This makes the gate measure the surface council actually reviews — closing the
review↔measure gap from [01-problem](01-problem.md).

## What it does NOT do
It does not judge whether the content is *good/adequate/correct* — that stays council's job
(the model invariant in [02-model](02-model.md)). The check proves *presence of real content
at the reviewed location*, which is strictly stronger than today's "a YAML prose field is
non-empty" while still being deterministic.

## Relational checks are unaffected (and become the backbone)
`edge_exists`, `obligation_satisfied`, `measured_by` coverage, no-orphan / no-dropped-intent —
all operate on the YAML relation graph and need no prose. Under the model these carry the
deterministic load; `field_present`-on-anchor is the thin content-presence floor on top.

## Floor interaction
The class→required-kind floor (`verification-floor.yaml`) is unchanged in spirit: a PROPOSE
presence-check stays `field_present` (now anchor-bound); stronger classes still require
stronger kinds (`symbol_resolves`, `behavioral`, …) which already bind to non-prose reality.
