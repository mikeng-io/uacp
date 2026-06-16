---
type: adr
status: accepted
date: 2026-06-16
---

# UACP Skill-Authoring Convention

## Metadata

- **Status**: accepted — Step-1 built and council-cleared (2-lens council, APPROVE-WITH-NITS; all material/minor findings resolved). Step 2 (library-wide application) pending.
- **Date**: 2026-06-16
- **Decision Makers**: UACP maintainer
- **Consulted**: Anthropic `skill-creator` convention (adopted, then improvised for UACP)
- **Informed**: all skill authors; the lifecycle, kernel, reference, and orchestration skills
- **Related**: ADR-0008 (subdirectory + ADR documentation structure); design `docs/plans/2026-06-16-uacp-skill-convention-design.md`; Step-1 plan `docs/plans/2026-06-16-uacp-skills-convention-step1.md`; the goal-driven track (ADR-0016) whose in-flight edits motivated the self-containment rule

## Context and Problem Statement

The `skills/` library grew organically and has no single enforced convention. Three concrete symptoms surfaced:

1. **Vestigial frontmatter.** Lifecycle skills carry `allowed_tools` / `forbidden_tools` / `phase_exit_invariants` in their SKILL.md frontmatter. After the config-collapse (Slices 4b/5), the runtime reads those from the **codified grammar** (`skills/uacp-core/scripts/engines/domain/phase_transitions.py` → `STAGE_ALLOWED_TOOLS`, consumed by Guardian Layer-B and Heartgate), not from the skill file. The frontmatter copies *look* authoritative but are descriptive mirrors that can drift.

2. **Dangling references.** Skills cite `docs/` files (ADRs, decision-log, lifecycle docs). When a skill is installed into a coding agent, only the skill directory ships — `docs/` does not. Those references dangle in an installed agent. This was caught concretely when the goal-driven edits (ADR-0016) cited `ADR-0016` in five SKILL.md bodies.

3. **Monolith + duplication.** The `bridge-*` skills are large monoliths (`bridge-commons` 785 lines; none use `references/`). The six lifecycle skills re-inline the same four boilerplate blocks (operator-phase-return, agent-council-followthrough, autonomous-self-closing-loop, mode_behavior) verbatim, and some duplicate sections within a single file.

There is no authoritative definition of what a UACP skill *is* — its directory shape, frontmatter, size discipline, or what it may reference. Without one, every new skill re-litigates these choices and the drift compounds.

## Decision Drivers

- One clean, clear convention for the whole library — the standard a future author reads once.
- Skills must be **self-contained**: an installed skill cannot depend on files that do not ship with it.
- Remove the "looks authoritative but isn't" ambiguity (the vestigial mirrors).
- Reuse a proven external convention rather than invent one; improvise only where UACP genuinely differs (lifecycle runtime coupling).
- The convention must itself obey its own rules (it cannot live only in `docs/`).

## Considered Options (with rejection reasoning)

1. **Leave it implicit / per-skill** — *rejected.* The status quo; drift and dangling references compound with every new skill.
2. **Author a `docs/`-only convention doc** — *rejected.* It would violate its own self-containment rule (a skill couldn't cite it once installed), and a `docs/plans/` doc has no standing in the authority chain. The convention must ship as a skill.
3. **Adopt `skill-creator` verbatim** — *rejected.* `skill-creator`'s minimal `name` + `description` frontmatter cannot express UACP's lifecycle coupling (`phase`, `authority_source`) or the kernel/reference distinction. Adopt its structure and disclosure model; improvise the frontmatter.
4. **Adopt `skill-creator`, improvised for UACP** — **chosen.** See below.

## Decision Outcome

Establish one convention, codified as a shipping reference skill `uacp-skills` (UACP's analog of `skill-creator`), with this ADR as the decision-of-record.

- **Structure & disclosure (adopt `skill-creator`):** `skills/<kebab-name>/SKILL.md` (required) plus optional `references/`, `scripts/`, `assets/`. Three-level progressive disclosure (metadata → SKILL.md body → bundled resources). **SKILL.md target < 500 lines**; detail moves to `references/` with "Read when…" pointers; reference files > 300 lines carry a table of contents.

- **`kind` taxonomy (improvise):** every skill declares `kind ∈ {kernel, lifecycle, reference, orchestration}`, which sets the minimum frontmatter — nothing decorative.

- **No authority mirrors:** lifecycle skills do **not** copy `allowed_tools` / `forbidden_tools` / `phase_exit_invariants` into frontmatter. They declare `authority_source` (a pointer to the codified grammar) and stop. The codified grammar is the single source of truth.

- **Self-containment rule (load-bearing):** a skill instruction body (`SKILL.md` and any instructing `references/` file) may reference only files that ship with *some* skill — its own bundled resources or another skill's shipped paths (`uacp-core/scripts/...`, `uacp-core/references/...`). It must **not** cite `docs/`. Durable contracts that live in `docs/` are **mirrored into `uacp-core/references/`** and cited there; the `docs/` original remains the origin of record. Source `*.py` files MAY cite ADRs in comments (provenance in code, not instruction prose). Enforced by `tests/unit/skills/test_skill_self_containment.py`.

- **DRY shared content:** content repeated across skills lives once under `skills/references/` and is cited, not re-inlined.

- **`bridge-*` → `uacp-bridge`:** one `kind: reference` skill — `SKILL.md` = the shared contract (today's `bridge-commons`), `references/<runtime>.md` per adapter.

## Consequences

- **Positive:** a single readable standard; installed skills no longer dangle; the vestigial-authority ambiguity is removed; SKILL.md files shrink under the size target; the convention ships and is testable.
- **Negative / risks:** a library-wide application pass is required (sequenced as Step 2) — collapsing `bridge-*`, DRYing boilerplate, slimming frontmatter, rolling out `kind:`. Until that completes, the library is partially converted; the self-containment test starts narrow (ADR citations in SKILL.md bodies) and widens to the `docs/` class in Step 2.
- **Sanctioned provenance carve-outs:** source `*.py` files may cite ADRs in comments, and a `references/` mirror may carry one "Origin of record" provenance line to its `docs/` source. Both ship as non-instruction provenance and are exempt from the self-containment rule.
- **No runtime-behavior change:** this is documentation/structure only. The codified grammar remains the enforcement authority.

## Status / next step

Accepted. Sequenced execution:
- **Step 1** (`docs/plans/2026-06-16-uacp-skills-convention-step1.md`): DONE — authored `uacp-skills`, mirrored the goal-driven contract into `uacp-core/references/`, repointed the five lifecycle skills off `ADR-0016`, added the self-containment test, council-cleared, merged.
- **Step 2** (separate plan): apply the convention library-wide — collapse `bridge-*` → `uacp-bridge`, DRY the shared boilerplate into `skills/references/`, slim lifecycle frontmatter (drop the tool/invariant mirrors), roll out `kind:`, and widen the self-containment test to the `docs/` citation class.
