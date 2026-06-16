---
name: uacp-skills
description: The UACP skill-authoring convention — directory structure, the kind taxonomy, per-kind frontmatter, progressive disclosure, and the self-containment rule. Read this before creating or refactoring any skill in skills/. UACP's analog of Anthropic skill-creator.
kind: reference
context: reference
---

# UACP Skills — Authoring Convention

This is a REFERENCE skill. Read it (via the Read tool) before creating or
refactoring any skill under `skills/`. It defines one clean, clear convention for
the whole library. It is UACP's analog of Anthropic's `skill-creator`, improvised
for UACP's lifecycle/runtime needs.

## Directory structure

```
skills/<kebab-name>/
├── SKILL.md          (required) — frontmatter + imperative instructions
├── references/       (optional) — detail loaded on demand
├── scripts/          (optional) — executable code (runs without being read in)
└── assets/           (optional) — templates, fixtures
```

- Names are **kebab-case**. UACP skills are prefixed `uacp-` unless they are a
  shared reference library consumed by name (e.g. `domain-registry`).
- **SKILL.md target: < 500 lines.** When you approach it, move detail into
  `references/` and leave a "Read when…" pointer. Reference files > 300 lines get
  a table of contents.
- Imperative voice. Define output formats with explicit templates. Explain the
  reasoning behind a rule, not just the rule.

## Progressive disclosure

Three levels load in order: (1) **metadata** — `name` + `description`, always
available, the trigger; (2) **SKILL.md body** — loaded when the skill triggers;
(3) **bundled resources** — `references/` read on demand, `scripts/` executed
without being read into context. Put only what is always needed in the body.

## Plugin packaging (the install target)

These skills ship as a **Claude Code plugin** (and, deferred-but-ready, a Hermes skill package). The convention exists so they load correctly once installed. Conform to the real format:

- **Manifest:** the plugin root carries `.claude-plugin/plugin.json` (`name: uacp` — this namespaces every skill as `/uacp:<dir>`). Adding/owning the manifest is a one-time packaging step, not per-skill.
- **Location = discovery:** every skill MUST be `skills/<dir>/SKILL.md`. A bare `skills/SKILL.md` is **not discovered**. The plugin loader auto-discovers from `skills/`.
- **Directory name = invocation name.** `skills/uacp-execute/` → `/uacp:uacp-execute`. Frontmatter `name:` is only a display label — do not rely on it for invocation, and keep dir name = intended invocation name.
- **Do not misuse reserved Claude Code frontmatter keys.** CC silently ignores *unknown* keys (so our `phase`/`authority_source`/`kind`/`location`/`metadata` are harmless), but these keys have real CC meaning — only use them for that meaning: `context` (value `fork` only), `allowed-tools`/`disallowed-tools`, `model`, `effort`, `agent`, `hooks`, `paths`, `disable-model-invocation`, `user-invocable`, `argument-hint`, `arguments`, `shell`.
- **Bundled resources ship:** `references/`, `scripts/`, `assets/` under a skill dir are bundled and readable at their relative paths. Keep `description` (+ `when_to_use`) under ~1536 chars (the listing budget) and SKILL.md under 500 lines.

**Dual-target (Hermes).** The same files install into Hermes' skill store (`~/.hermes/skills/devops/uacp/<dir>/SKILL.md`); Hermes reads `metadata.hermes.{tags,related_skills}`. CC ignores the Hermes keys and Hermes ignores the CC keys, so one frontmatter serves both. Hermes packaging/sync is deferred but the layout is ready.

**Deferred (not built yet):** the Hermes sync mechanism, marketplace publication, and the Guardian-enforcement hooks for CC (a separate effort). This convention is about being *loadable and readable*; distribution is a follow-up.

## The `kind` taxonomy

Every UACP skill declares `kind`. It sets the minimum frontmatter — nothing
decorative.

| `kind` | role | examples |
|---|---|---|
| `kernel` | imported by runtime adapters; not invoked as a skill | `uacp-core` |
| `lifecycle` | a phase skill; behavior gated by the codified grammar | triage, propose, plan, execute, verify, resolve |
| `reference` | read via the Read tool; never invoked standalone | `domain-registry`, `uacp-skills` (and `uacp-bridge`, planned) |
| `orchestration` | invocable helpers around the lifecycle | council, debate, parallel, context, web, brainstorm |

> **Rollout status.** This is the target convention. Existing skills are being
> brought into compliance incrementally — some still carry pre-convention
> frontmatter (e.g. lifecycle skills with `allowed_tools` mirrors, or skills with
> no `kind:` yet). The examples below show the **target** form a new or refactored
> skill should adopt, not a claim that every skill already conforms.

Per-kind frontmatter fields and examples: **read** `references/frontmatter-by-kind.md`.

## Lifecycle frontmatter — no authority mirrors

Lifecycle skills must NOT copy `allowed_tools` / `forbidden_tools` /
`phase_exit_invariants` into their frontmatter. Those are **codified** in
`uacp-core/scripts/engines/domain/phase_transitions.py` (consumed by Guardian
Layer-B and Heartgate). A SKILL.md copy is a descriptive mirror that drifts and
falsely looks authoritative. Declare `authority_source` (a pointer to the codified
grammar) and stop there.

## Self-containment rule (load-bearing)

A skill instruction body (`SKILL.md`, and any `references/` file that *instructs*)
may reference only files that ship with **some** skill:
- its own `references/` / `scripts/` / `assets/`, or
- another skill's shipped paths (e.g. `uacp-core/scripts/...`,
  `uacp-core/references/...`).

**Do not cite `docs/` (ADRs, decision-log, lifecycle docs) from a skill body** — an
installed coding agent receives the skill directory, not the repo's `docs/` tree, so
the reference dangles. When a skill must cite a durable contract that lives in
`docs/`, **mirror the contract into `uacp-core/references/`** and cite the mirror.
The `docs/` original remains the origin of record; the mirror is the shipped,
citable copy. (Source `*.py` files MAY cite ADRs in comments — that is provenance
in code, not instruction prose.) A `references/` mirror MAY carry a single "Origin of record" provenance line naming the `docs/` original it mirrors (e.g. the goal-driven mirror's header), provided the file is fully usable without following that link. Enforced by
`tests/unit/skills/test_skill_self_containment.py`.

> **Enforcement scope (rollout).** The regression test currently enforces only
> the `ADR-<number>` citation class in `SKILL.md` bodies. The broader `docs/`
> citation class (e.g. `docs/INDEX.md`, `docs/lifecycle/...` read-pointers) is
> being migrated incrementally and the test widens to it in the library-wide
> rollout. Until then, existing skills may still carry `docs/` read-pointers —
> that is known debt, not a counter-example. New/refactored skills must follow the
> full rule now.

## DRY shared content

Content shared across skills lives once under **`uacp-core/references/`** (the kernel skill every skill may cite) and is cited with a "Read when…" pointer, not re-inlined. There is no top-level shared dump under `skills/` outside a skill dir.

## Authoring checklist

1. Pick `kind`; create `skills/<kebab-name>/SKILL.md` with the minimum frontmatter
   for that kind (`references/frontmatter-by-kind.md`).
2. Write the body imperative and < 500 lines; move detail to `references/`.
3. Cite only shipped files (self-containment). Mirror any `docs/` contract into
   `uacp-core/references/` first.
4. Do not inline content that already exists under `uacp-core/references/`.
5. Run `python3 -m pytest tests/unit/skills/ -q` before committing.

### Where a shared/reference doc lives
- Cited by exactly ONE skill → that skill's own `references/`.
- Shared across many skills, or a kernel-level contract → `uacp-core/references/`.
- Dated session-history / one-off lessons / external analysis cited by no skill → `docs/knowledge/` (human/agent reading + provenance; **not** skill-citable — skills must not cite `docs/`).

## Plugin-readiness checklist
1. Skill is at `skills/<dir>/SKILL.md`; the dir name is the intended `/uacp:<dir>` invocation name.
2. `description` present and within the listing budget; no reserved-key misuse (above).
3. Body < 500 lines; detail in `references/`; cites only shipped files (self-containment).
4. `.claude-plugin/plugin.json` exists at the plugin root (one-time).
5. `python3 -m pytest tests/unit/skills/ -q` passes (self-containment + readiness lint).
