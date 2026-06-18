---
type: design
title: "UACP Skill Convention — Design"
description: "Design for the `uacp-skills` meta-skill defining a single enforced convention for every skill in the UACP library"
tags: ["skills", "convention", "meta-skill", "frontmatter"]
timestamp: 2026-06-16
status: archived
---

# UACP Skill Convention — Design

**Status:** approved (2026-06-16), pending implementation plan.
**Deliverable:** a meta-skill `uacp-skills` — UACP's analog of Anthropic's `skill-creator` — that defines one clean, clear convention for every skill in the library, plus a sequenced application of that convention.

## Problem

The skill library has no single, enforced convention. Three concrete symptoms:

1. **Vestigial frontmatter.** Lifecycle skills carry `allowed_tools` / `forbidden_tools` / `phase_exit_invariants` in their SKILL.md frontmatter, but after the config-collapse the runtime reads those from the **codified grammar** (`skills/uacp-core/scripts/engines/domain/phase_transitions.py` → `STAGE_ALLOWED_TOOLS`, consumed by Guardian Layer-B and Heartgate). The frontmatter copies are descriptive mirrors that *look* authoritative but are not — they can drift.
2. **Dangling references.** Skills cite `docs/architecture/00NN-*.md` (ADRs) and other `docs/` files. When a skill is installed into a coding agent, only the skill directory ships — `docs/` does not. Those references dangle in an installed agent. (Surfaced by the goal-driven edits, which cited `ADR-0016`.)
3. **Monolith + duplication.** `bridge-*` skills are large monoliths (`bridge-commons` 785 lines, none using `references/`). Lifecycle skills re-inline the same four boilerplate blocks (operator-phase-return, agent-council-followthrough, autonomous-self-closing-loop, mode_behavior) verbatim across all six, and some duplicate sections within a single file.

## Decisions (operator-approved)

1. **Drop the vestigial frontmatter mirrors** — authority is the codified grammar; the skill points to it via `authority_source`.
2. **Convention-first** — author the convention as a skill, then apply it library-wide in follow-on plans.
3. **Fold the in-flight goal-driven edits into this effort** — mirror the goal-driven contract into `uacp-core`, repoint the six skills there.
4. **The convention ships as a skill** (`uacp-skills`), not a `docs/` file — it must obey its own self-containment rule.
5. **Name:** `uacp-skills`. **`kind:` classifier:** included on every skill.

## The convention (what `uacp-skills` codifies)

Adopt Anthropic `skill-creator`; improvise for UACP.

### Structure & progressive disclosure (adopt)
- `skills/<kebab-name>/SKILL.md` (required) + optional `references/`, `scripts/`, `assets/`.
- **SKILL.md target < 500 lines.** Detail goes to `references/`, loaded on demand.
- Every reference cited from SKILL.md with a "**Read when…**" pointer. Reference files > 300 lines carry a table of contents.
- Imperative voice; explicit output templates; reasoning over rigid rules.

### Skill taxonomy + per-kind frontmatter (improvise)
Every skill declares `kind`. Frontmatter is the minimum each kind needs — nothing decorative.

| `kind` | examples | frontmatter |
|---|---|---|
| `kernel` | `uacp-core` | `name, description, kind, version` (imported by adapters; not invoked) |
| `lifecycle` | triage, propose, plan, execute, verify, resolve | `name, description, kind, phase, authority_source` — **no tool/invariant mirrors** |
| `reference` | `uacp-bridge`, `domain-registry`, `uacp-skills` | `name, description, kind, context: reference` |
| `orchestration` | council, debate, parallel, context, web, brainstorm | `name, description, kind` |

`description` remains the primary triggering mechanism (functionality + when to use).

### Self-containment rule (the ADR fix)
A skill may reference only files that ship with *some* skill: its own `references/`/`scripts/`, or another skill's shipped paths (e.g. `uacp-core/scripts/engines/domain/checkpoint.py`). **No references to `docs/`** (ADRs, decision-log, lifecycle docs) from within a skill body. Durable contracts that skills must cite are **mirrored into `uacp-core/references/`** and cited there. The ADR/decision-log remains the *origin of record*; the skill-side mirror is the *shipped, citable* copy.

### DRY shared boilerplate
The four blocks repeated across lifecycle skills move to shared references; each SKILL.md keeps a one-line "Read when…" pointer:
- `agent-council-followthrough.md` (already exists at `skills/references/`),
- `operator-phase-return.md`,
- `autonomous-self-closing-loop.md`,
- `mode-behavior.md`.

This alone brings every lifecycle SKILL.md well under the 500-line target.

### `bridge-*` → `uacp-bridge`
One `kind: reference` skill:
- `SKILL.md` = the shared contract (today's `bridge-commons`: pre-flight SOP, input/output schema, tier system, status semantics).
- `references/{claude,codex,gemini,kimi,opencode}.md` = per-adapter specifics, loaded on demand.
- Repoint dispatch-contract pointers in `CLAUDE.md` / `AGENTS.md` (currently `skills/bridge-claude/SKILL.md`, `skills/bridge-codex/SKILL.md`).
- `domain-registry` dependency references update to the collapsed skill.

## Sequenced execution

**Step 1 (this branch — folds in the goal-driven edits):**
1. Author `skills/uacp-skills/` (the convention).
2. Create `skills/uacp-core/references/goal-driven-track.md` mirroring the goal-driven contract (the kernel facts: `CheckpointEntry`, `ConvergenceBudget`, the budget artifact path, track binding, EXECUTE→VERIFY + closure coherence).
3. Repoint the six goal-driven SKILL.md edits to cite that mirror + the `engines/domain/*.py` scripts, not `ADR-0016`.

**Step 2 (separate plan):** apply the convention library-wide — `bridge-*` → `uacp-bridge`, boilerplate DRY into shared references, lifecycle frontmatter slimming, `kind:` classifier rollout.

Each step: branch → subagent-driven edits with two-stage review → council before merge → `--no-ff` to main.

## Non-goals
- Not changing any runtime enforcement behavior (the codified grammar is the authority; this is documentation/structure only).
- Not changing skill *content* beyond structure, references, and frontmatter — except the goal-driven additions already in flight.
- Not introducing a build/packaging step; "what ships" is the skill directory as-is.
