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
in code, not instruction prose.) Enforced by
`tests/unit/skills/test_skill_self_containment.py`.

## DRY shared content

Content repeated across skills lives once under `skills/references/` and is cited
with a "Read when…" pointer, not re-inlined. Existing shared references include
`agent-council-followthrough.md` and `operator-phase-return-presentation.md`.

## Authoring checklist

1. Pick `kind`; create `skills/<kebab-name>/SKILL.md` with the minimum frontmatter
   for that kind (`references/frontmatter-by-kind.md`).
2. Write the body imperative and < 500 lines; move detail to `references/`.
3. Cite only shipped files (self-containment). Mirror any `docs/` contract into
   `uacp-core/references/` first.
4. Do not inline content that already exists under `skills/references/`.
5. Run `python3 -m pytest tests/unit/skills/ -q` before committing.
