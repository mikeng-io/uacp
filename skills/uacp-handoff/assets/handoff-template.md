---
kind: handoff
workstream: <kebab-workstream-id>           # = this file's name
title: <one line — what this workstream is>
status: active                              # active | resolved | superseded
scope:
  in: [<what this workstream IS>]
  out: [<what it is NOT>]
attribution:
  generated_by: { agent: <id>, model: <id>, runtime: <hermes|cc|kimi> }
  updated_at: <YYYY-MM-DD>
edges:                                      # ANCHORS — reconstructable refs live ONLY here
  - {dst: 'branch:<branch>', rel: anchored_to, provenance: parsed}
  - {dst: 'commit:<sha>',    rel: anchored_to, provenance: parsed}
  # - {dst: 'design/<bundle>/<node>', rel: relates_to,  provenance: asserted}
  # - {dst: 'run:<run_id>',           rel: derived_from, provenance: derived}
  # - {dst: '<predecessor>.md',       rel: superseded_by, provenance: asserted}  # if superseding
---

# Handoff — <workstream>

## Intent
<Why this work exists; the goal/outcome. The directional abstraction a fresh agent
needs and cannot get from the diff. NOT the task list.>

## Decisions & rationale
- [locked] <decision> — <why> (do not re-litigate)
- [open] <decision under consideration> — <why / what is still unresolved>

## Rejected / not-this
- <path considered and dropped> — <why-not, so it is not retried>

## Open threads & watch-outs
- <unresolved fork / deliberately-deferred item>
- watch-out: <non-obvious trap discovered this session>

## Now → next
- **Position:** <branch>, last commit <sha> (see Anchors).
- **Next intent:** <what to achieve next — the goal, not the mechanical steps>.

## Anchors
<Rendered mirror of frontmatter `edges:` — the click-through to all reconstructable
detail. Everything recoverable from the repo belongs here, not above.>
- branch: <branch>
- commit: <sha> — <one line: what it did>
- design: <node path>  (if any)
- run: <run_id>  (if any)
