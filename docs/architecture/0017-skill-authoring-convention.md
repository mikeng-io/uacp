---
type: adr
title: UACP skill-authoring convention
description: Establish a single enforced convention for the skills/ library covering directory shape, frontmatter, kind taxonomy, self-containment, and reference boundaries.
tags: [skills, convention, self-containment, okf]
timestamp: 2026-06-16
status: accepted
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

2. **Reference hygiene.** Skills cite `docs/` files (ADRs, decision-log, lifecycle docs) and a sprawling top-level `skills/references/` shared dump. *(Correction — recorded 2026-06-17: the original framing here was "an installed agent receives only the skill dir, not `docs/`, so `docs/` citations dangle." The Claude Code plugin spec disproves that — installing copies the **entire plugin directory** (`docs/` included) to disk; Hermes loads the full repo. So `docs/` does NOT physically dangle. The real concerns were (a) a messy unscoped shared dump, (b) root-relative paths needing a resolvable per-runtime token, and (c) preferring a concise shipped digest over pointing instruction at a large ADR — not literal file absence. See Decision Outcome → in-plugin reference rule.)*

3. **Monolith + duplication.** The `bridge-*` skills are large monoliths (`bridge-commons` 785 lines (now `uacp-bridge/SKILL.md`); none use `references/`). The six lifecycle skills re-inline the same four boilerplate blocks (operator-phase-return, agent-council-followthrough, autonomous-self-closing-loop, mode_behavior) verbatim, and some duplicate sections within a single file.

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

- **Plugin packaging (the install target):** the library ships as a Claude Code plugin — `.claude-plugin/plugin.json` (`name: uacp`) at the repo/plugin root; skills auto-discover from `skills/<dir>/SKILL.md`; **invocation name = directory name** (frontmatter `name:` is a label); do not misuse Claude-Code-reserved frontmatter keys (`context`, `allowed-tools`, `model`, `effort`, `agent`, `hooks`, `paths`, …). The same files are Hermes-ready (`metadata.hermes.*`, `~/.hermes/skills/devops/uacp/`). Hermes sync, marketplace publication, and CC Guardian-hook enforcement are deferred follow-ups; this ADR governs being *loadable and readable*, not distribution.

- **`kind` taxonomy (improvise):** every skill declares `kind ∈ {kernel, lifecycle, reference, orchestration}`, which sets the minimum frontmatter — nothing decorative.

- **No authority mirrors:** lifecycle skills do **not** copy `allowed_tools` / `forbidden_tools` / `phase_exit_invariants` into frontmatter. They declare `authority_source` (a pointer to the codified grammar) and stop. The codified grammar is the single source of truth.

- **Reference boundary (load-bearing; one-directional — settled 2026-06-17):** two reference layers, references flow one way. **Skill tree** (`uacp-core/references/` shared + each skill's own `references/`) holds everything a skill *instruction* cites; **`docs/`** holds authority / rationale / canonical reference / history. A skill cites **only the skill tree** — never `docs/`. `docs/` is one-directional: it governs/describes skills; skills never point back into it. This is for **boundary cleanliness / no divergence**, not for dangling (the whole plugin, `docs/` included, ships to disk on install; Hermes loads the full repo — so `docs/` is present either way; the rule is about not tangling the two layers). When a skill needs a `docs/` contract, use the **two-layer digest pattern**: full rationale stays in `docs/` (origin of record), a concise operational digest lives in `uacp-core/references/`, the skill cites the digest (template: `uacp-core/references/goal-driven-track.md` ← ADR-0016). Decision test for a new reference doc: *does a skill cite it to operate?* yes → skill tree; no → `docs/`. Paths use the runtime-neutral `UACP_ROOT/…` token; `*.py` may cite ADRs in comments. Enforced by `tests/unit/skills/test_skill_self_containment.py` (no abolished-dump citation; no `ADR-<number>` in SKILL.md bodies — cite the digest); the `docs/`-back-pointer ban is applied to existing lifecycle skills in a dedicated cleanup slice, then lint-widened.

- **DRY shared content:** content repeated across skills lives once under `uacp-core/references/` and is cited, not re-inlined. (The former top-level `skills/references/` shared dump is abolished; the relocation is handled in the references slice.)

- **`bridge-*` → `uacp-bridge`:** one `kind: reference` skill — `SKILL.md` = the shared contract (today's `bridge-commons`), `references/<runtime>.md` per adapter.

## Consequences

- **Positive:** a single readable standard; installed skills no longer dangle; the vestigial-authority ambiguity is removed; SKILL.md files shrink under the size target; the convention ships and is testable.
- **Negative / risks:** a library-wide application pass was required (Step 2, now done) — collapsing `bridge-*`, abolishing the `skills/references/` dump, slimming frontmatter, rolling out `kind:`. The self-containment lint binds the ADR-citation class and the abolished-dump class; the broad `docs/` citation class remains an open decision (see Status / next step).
- **Sanctioned provenance carve-outs:** source `*.py` files may cite ADRs in comments, and a `references/` mirror may carry one "Origin of record" provenance line to its `docs/` source. Both ship as non-instruction provenance and are exempt from the self-containment rule.
- **No runtime-behavior change:** this is documentation/structure only. The codified grammar remains the enforcement authority.
- **Plugin-ready, not yet distributed:** after this convention, the library installs as a CC plugin and is Hermes-ready, but is not auto-synced to either runtime; distribution remains an explicit step.

## Status / next step

Accepted. Sequenced execution:
- **Step 1** (`docs/plans/2026-06-16-uacp-skills-convention-step1.md`): DONE — authored `uacp-skills`, mirrored the goal-driven contract into `uacp-core/references/`, repointed the five lifecycle skills off `ADR-0016`, added the self-containment test, council-cleared, merged.
- **Step 2** (4 slices, DONE — merged 2026-06-17): Slice 1 CC plugin readiness (`.claude-plugin/plugin.json`, router relocated, convention re-grounded); Slice 2 `bridge-*` → `uacp-bridge`; Slice 3 abolished the `skills/references/` dump (relocated to `uacp-core/references/` / owning skills / new `docs/knowledge/`); Slice 4 slimmed lifecycle frontmatter (dropped the tool/invariant mirrors), rolled out `kind:` to all skills, and swept the `context:` reserved-key offenders. Frontmatter + `kind:` conformance is now **lint-enforced** (`tests/unit/skills/test_plugin_readiness.py`: valid `kind`, no lifecycle mirrors, no `context` misuse; `test_skill_self_containment.py`: no ADR citation + no abolished-dump citation).
- **`docs/` citation class — DONE + lint-enforced 2026-06-17 (Slice 5).** One-directional boundary fully realized: skills cite only the skill tree; `docs/` is never cited by skills. The ~60 `docs/` back-pointers in the lifecycle skills were resolved — `docs/reference/operator-phase-return-schema.md` repointed to the existing `uacp-core/references/operator-phase-return-presentation.md` digest; `docs/INDEX.md` / `docs/policy/constitution.md` / `docs/lifecycle/lifecycle-reference.md` read-pointers dropped (authority/navigation, already covered by skill bodies + codified grammar + existing digests); `docs/lifecycle/orchestration-model.md`'s operational half (council-invocation schema, mode/tier vocabulary, retrieval-led rule, finding schema, pre-invocation setup, mid-phase escalation) digested into the existing `uacp-core/references/agent-council-followthrough.md` (extend-over-create), its authority half left in `docs/`. The self-containment lint now forbids the rooted `UACP_ROOT/docs/` citation form in SKILL.md bodies (bare `docs/` prose still allowed).
- **Reference-document policy — codified + lint-enforced 2026-06-17 (Slice 5).** Anti-proliferation gate: **default is EXTEND, not create** (each reference doc owns a topic; fold new material into the topic's existing doc; a new file is the rare exception meeting a 4-point gate). Naming = topic/contract, kebab-case, no date suffix. `uacp-core/references/README.md` indexes every doc → purpose → citers. Lint teeth: every `uacp-core/references/*.md` is cited by ≥1 skill, listed in the index, and kebab/no-date named (mutation-verified non-vacuous).
- **OKF alignment — adopted + lint-enforced 2026-06-17 (Slice 7).** The reference/knowledge layer is aligned to the **Open Knowledge Format** (markdown + YAML frontmatter, per-directory `index.md`, cross-linked graph — a vendor-neutral "format not platform" that UACP had independently converged on). Every `skills/uacp-core/references/*.md` and `docs/knowledge/*.md` doc (the per-dir `index.md` exempt) now carries OKF frontmatter: `type` (UACP 5-type vocab — `contract` | `pattern` | `digest` | `lessons` | `analysis`), `title`, `description`, `tags`, `timestamp`, plus `resource:` on `digest` docs (the `docs/` origin of record). Each dir's `README.md` was renamed to `index.md` (OKF convention) and `docs/INDEX.md` repointed. The shared council vocabulary `uacp-council-taxonomy` (a skill cited only as a read-reference by 6 skills) was folded into `uacp-core/references/council-taxonomy.md` (`type: contract`) — a reference doc, not a skill dependency. Lint teeth: `tests/unit/skills/test_okf_frontmatter.py` enforces valid OKF frontmatter (type ∈ vocab + title + description) on both directories (mutation-verified non-vacuous), and the index-completeness check points at `index.md`. OKF frontmatter is for the reference/knowledge layer only — SKILL.md files keep the Claude Code plugin frontmatter.
- **Still deferred (packaging-ready, not built):** Hermes skill-store sync + CC marketplace **distribution**.
