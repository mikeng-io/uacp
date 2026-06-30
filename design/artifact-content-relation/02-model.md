---
type: design
title: "The Canonical Model — content in Markdown, relations in YAML"
description: "Defines the principled rule: Markdown holds semantic content (what agents comprehend), YAML holds relations and deterministic facts (what gates measure). Corrects the three-category split identified in node 01."
tags: [artifact, content-relation, design, model, markdown, yaml, gate, cms]
timestamp: 2026-06-30
edges:
  - {dst: 01-problem, rel: motivated_by, provenance: asserted}
---
# 02 — The canonical model

## The rule
For every lifecycle manifest artifact:

- **Markdown = semantic content.** The prose an agent or council must read to *comprehend*
  the artifact: intent, scope statements, authority rationale, risk/containment/verification
  analysis, transition reasoning. One home per concern.
- **YAML = relations + deterministic facts.** Stable ids; typed edges (`derives_from`,
  `measured_by`, `supersedes`, …); **anchors** (id → MD section); and genuinely
  deterministic scalars (phase, granularity_level, risk_level enum, timestamps). No prose.

## What changes per category (from [01-problem](01-problem.md))
- **Cat 1 (machine spine)** — stays in YAML. Unchanged.
- **Cat 2 (duplicated)** — the *prose* moves to MD; YAML keeps only the **id + anchor**.
  e.g. `scope.in_scope[]` becomes `{id: si-1, anchor: "<md>#si-1"}` — the `statement`
  prose lives in the MD section, not the YAML.
- **Cat 3 (council substance)** — already MD; now made gate-*visible* via anchored checks
  (see [04-check-retarget](04-check-retarget.md)), instead of invisible.

## Why this is the principled fix
- One home per concern → no cat-2 duplication, no drift.
- The reviewed surface (MD) becomes the measured surface (via anchors) → council and gate
  see the same thing.
- Removes the `field_present`-on-prose proxy; the deterministic gate goes back to what it
  is actually good at — **relations/topology** (coverage, no-orphan, no-dropped-intent),
  all of which are pure-YAML and need no prose.
- Authority split is preserved and *clarified*: **gate measures relations; council judges
  semantics.** Nothing moves between authorities; the surfaces just stop overlapping wrong.

## Non-negotiable invariant of the model
A semantic claim is NEVER measured by a structural proxy. If a check needs to touch content,
it binds (via an anchor) to the MD that holds that content and asserts only what is
deterministically checkable there (section resolves, non-empty, header present) — adequacy
remains council's call.
