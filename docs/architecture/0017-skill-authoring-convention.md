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

- **In-plugin reference rule (load-bearing; corrected 2026-06-17):** because the install copies the **whole plugin/repo** (`docs/` included), a skill body may reference **any in-tree file** — its own bundled resources, another skill's shipped paths (`uacp-core/...`), and the repo's `docs/`/`config/` — via the runtime-neutral `UACP_ROOT/…` token (CC → plugin root / `${CLAUDE_PLUGIN_ROOT}`; Hermes → repo root). The only hard rule: **stay inside the plugin/repo root** (path-traversal outside it fails on install). *Preference, not necessity:* keep durable shared contracts as a concise `uacp-core/references/` digest and point instruction there rather than at a sprawling `docs/` ADR; `*.py` may cite ADRs in comments. Enforced by `tests/unit/skills/test_skill_self_containment.py` for two hygiene rules — no citation of the abolished `skills/references/` dump, and no `ADR-<number>` in SKILL.md bodies (a style preference, since ADRs ship too). The lint is **not** widened to forbid `docs/` (that would enforce the disproven "docs/ dangles" premise).

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
- **`docs/` citation class — RESOLVED 2026-06-17 (operator).** The ~60 `docs/` read-pointers in skill bodies are **kept as-is**: the CC plugin spec confirms the whole plugin (incl. `docs/`) ships, so they don't dangle. No mass mirror, no drop, no lint-widening to forbid `docs/`. The convention is corrected to the **in-plugin reference rule** (above); the only requirement is in-tree paths via the resolvable `UACP_ROOT/…` token. Follow-ups (separate, optional): (a) standardize any non-resolving root tokens to `UACP_ROOT`/`${CLAUDE_PLUGIN_ROOT}`; (b) the still-deferred Hermes-store sync + CC marketplace **distribution** (packaging is ready, distribution not built).
