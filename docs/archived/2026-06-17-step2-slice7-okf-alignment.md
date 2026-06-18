# Step 2 · Slice 7 — OKF frontmatter alignment + council-taxonomy → reference

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Align UACP's reference/knowledge layer to the Open Knowledge Format (OKF) — markdown + YAML frontmatter, per-dir `index.md`, cross-linked graph — so UACP knowledge is OKF-interoperable; and fold `uacp-council-taxonomy` (a shared reference read by 6 skills) into the reference home with that frontmatter.

**OKF frontmatter for every `uacp-core/references/*.md` and `docs/knowledge/*.md`:**
```yaml
---
type: contract | pattern | digest | lessons | analysis   # OKF-required (UACP 5-type vocab)
title: <Human Title>
description: <one-line purpose / trigger>
tags: [<topical>, ...]
timestamp: 2026-06-17        # ISO date; keep a doc's own origin date if dated
resource: <docs/ origin path>   # OPTIONAL — for `digest` docs, the docs/ origin of record
---
```
**Type vocab:** `contract` (operational contract a skill follows — agent-council-followthrough, governed-canonical-writers, operator-phase-return-presentation, council-taxonomy); `pattern` (reusable how-to — adaptive-package-*, the guardian/kanban/porting/containment patterns, semantic-package, full-lineage); `digest` (concise mirror of a docs/ ADR — goal-driven-track); `lessons` (distilled session history — most docs/knowledge); `analysis` (research/source study — trustless-acp-source-analysis, architecture-packet, lexa). Assign per doc by reading its top.

**Index:** rename each dir's `README.md` → `index.md` (OKF convention) and keep it as the OKF bundle index. Branch `skills/step2-slice7-okf-alignment`. Baseline suite 909/2.

## Hard constraints
- `uacp-skills/SKILL.md` is lint-scanned: no literal abolished-dump path, no `ADR-<digit>`, no `UACP_ROOT/docs/`.
- timestamp: don't fabricate per-edit times; use `2026-06-17` (alignment date) or a dated doc's own date. (No `Date.now` available; the literal date is fine.)
- Verify GREEN before merge (burned before).

---

## Task 1: Codify OKF frontmatter in the reference-doc policy
`skills/uacp-skills/SKILL.md` — in the "Reference-document policy" section, add an **OKF frontmatter** subsection: every `uacp-core/references/*.md` and `docs/knowledge/*.md` carries OKF frontmatter (the block above); the 5-type vocab; the per-dir index is `index.md`. State it's OKF-aligned (cite "Open Knowledge Format" by name; do not write a `docs/` rooted path or ADR-digit). Suite green. Commit.

## Task 2: Move `uacp-council-taxonomy` → `uacp-core/references/council-taxonomy.md`
- `git mv skills/uacp-council-taxonomy/SKILL.md skills/uacp-core/references/council-taxonomy.md`. Replace its SKILL frontmatter with OKF frontmatter (`type: contract`, title "Council Taxonomy", description, tags `[council, taxonomy]`, timestamp 2026-06-17). Keep the body.
- Repoint the 7 citers (`skills/uacp-council/SKILL.md`, `uacp-debate`, `uacp-parallel`, `uacp-context`, `uacp-brainstorm`, `uacp/SKILL.md`, `uacp-council/references/phase-1-registration.md`) from `uacp-council-taxonomy` (skill name / `dependencies:` / read-pointer) → `uacp-core/references/council-taxonomy.md` (read-pointer) or remove the now-defunct `dependencies: uacp-council-taxonomy` entry (a reference doc isn't a skill dependency — repoint body read-pointers to the file path; drop frontmatter dep entries).
- `git rm -r skills/uacp-council-taxonomy` (confirm empty after the SKILL.md move). `grep -rn "uacp-council-taxonomy" skills/` → only intentional mentions (the new file's own name in index, etc.); no dangling skill ref.
- Suite green. Commit.

## Task 3: OKF frontmatter on `uacp-core/references/` (13 docs) + index.md
- For each `*.md` (the 12 existing + council-taxonomy from T2), read its top, prepend OKF frontmatter with the right `type` (per the vocab), title, description (reuse the index's one-liner), tags, timestamp; for `digest` docs add `resource:` (goal-driven-track → its ADR path). Preserve the body (H1 etc. stays below frontmatter, or fold the existing "Read when…" into description).
- `git mv skills/uacp-core/references/README.md skills/uacp-core/references/index.md`; update it to the OKF bundle index (keep the table; note it's the OKF index). Ensure it lists all 13 incl council-taxonomy.
- Suite green. Commit.

## Task 4: OKF frontmatter on `docs/knowledge/` (19 docs) + index.md
- Same: prepend OKF frontmatter to each `docs/knowledge/*.md` (most are `type: lessons`; trustless-acp = `analysis`; pick per doc). timestamp = the doc's date if dated, else 2026-06-17.
- `git mv docs/knowledge/README.md docs/knowledge/index.md`; update it as the OKF index. Update `docs/INDEX.md` registration (the `knowledge/` row → point at `index.md`).
- Suite green. Commit.

## Task 5: Lint — enforce OKF frontmatter; index.md; council-taxonomy cited-by
`tests/unit/skills/` — add/extend:
- **OKF frontmatter present + valid** on every `skills/uacp-core/references/*.md` and `docs/knowledge/*.md` (except `index.md`): has `type` ∈ {contract,pattern,digest,lessons,analysis}, `title`, `description`. Parametrize; clear ids.
- **index-complete:** point the existing index check at `index.md` (not README.md) for `uacp-core/references/`; every doc listed.
- The existing **cited-by-≥1-skill** check now naturally covers `council-taxonomy.md` (it's cited by the 7) — confirm it passes.
- Mutation-check the OKF-frontmatter check is non-vacuous (a doc missing `type` fails). ruff clean. Commit.

## Task 6: Verify + ADR/log + council + merge
- `python3 -m pytest -q` 0 failures; ruff clean; `claude plugin validate .` passes; `grep` no dangling `uacp-council-taxonomy` skill ref; both `index.md` exist + complete.
- ADR-0017 + decision-log: record OKF adoption (reference/knowledge layer is OKF-aligned, lint-enforced) + council-taxonomy relocation.
- Council (1-2 lens): OKF frontmatter applied correctly (types sane, no body lost); council-taxonomy move clean (7 citers resolve, skill dir gone); index.md complete; lint non-vacuous.
- Verify GREEN, then merge `--no-ff` (branch `skills/step2-slice7-okf-alignment`), delete branch.

## After
- Remaining: the `uacp-core/SKILL.md` Scripts-table drift fix (separate small follow-up); distribution (Hermes sync + CC marketplace).

## Out of scope
- The Scripts-table drift; distribution; applying OKF frontmatter to SKILL.md files (skills keep the CC plugin frontmatter — OKF is for the reference/knowledge layer only).
