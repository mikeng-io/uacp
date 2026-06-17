---
name: uacp-skills
description: The UACP skill-authoring convention — directory structure, the kind taxonomy, per-kind frontmatter, progressive disclosure, and the self-containment rule. Read this before creating or refactoring any skill in skills/. UACP's analog of Anthropic skill-creator.
kind: reference
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
- **Do not misuse reserved Claude Code frontmatter keys.** CC ignores *unknown* keys (so our `phase`/`authority_source`/`kind`/`location`/`metadata` are harmless and do not break loading), but these keys have real CC meaning — only use them for that meaning: `context` (value `fork` only), `allowed-tools`/`disallowed-tools`, `model`, `effort`, `agent`, `hooks`, `paths`, `disable-model-invocation`, `user-invocable`, `argument-hint`, `arguments`, `shell`. No skill misuses `context` now — the frontmatter-normalization sweep (Slice 4) is complete and enforced by `tests/unit/skills/test_plugin_readiness.py`.
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

> **Status: rollout complete.** Every skill in the library now declares `kind`; lifecycle skills no longer carry `allowed_tools` / `forbidden_tools` / `phase_exit_invariants` mirrors. Enforced by `tests/unit/skills/test_plugin_readiness.py`.

Per-kind frontmatter fields and examples: **read** `references/frontmatter-by-kind.md`.

## Lifecycle frontmatter — no authority mirrors

Lifecycle skills must NOT copy `allowed_tools` / `forbidden_tools` /
`phase_exit_invariants` into their frontmatter. Those are **codified** in
`uacp-core/scripts/engines/domain/phase_transitions.py` (consumed by Guardian
Layer-B and Heartgate). A SKILL.md copy is a descriptive mirror that drifts and
falsely looks authoritative. Declare `authority_source` (a pointer to the codified
grammar) and stop there.

## Reference boundary (load-bearing) — one-directional

There are two reference layers, and references flow **one way** between them. This
is what keeps documentation from diverging into a tangle of cross-pointers.

| Layer | Holds | Read by | Direction |
|---|---|---|---|
| **skill tree** — `uacp-core/references/` (shared) + each skill's own `references/` | everything a skill *instruction* cites: operational contracts, patterns, schemas | the installed skill, at runtime | skills cite **only** here |
| **`docs/`** — ADRs, decision-log, policy, lifecycle/orchestration reference, `knowledge/` | authority · rationale · canonical reference · history | humans + in-repo authoring | `docs/` **may** point at skills; **skills never point back into `docs/`** |

**The rule:** a skill body (and any instructing `references/` file) cites **only the
skill tree** — its own `references/`/`scripts/`/`assets/`, or another skill's shipped
paths (`uacp-core/references/…`, `uacp-core/scripts/…`). It does **not** cite `docs/`.
`docs/` is one-directional: it governs/describes skills; skills do not depend on it.

This is **not** about dangling — a CC plugin install copies the whole repo (`docs/`
included) to disk, and Hermes loads the full repo, so `docs/` is present either way.
The rule exists for **boundary cleanliness**: one home per kind of content, no
back-pointers, no divergence.

**Two-layer (digest) pattern — the standard way to handle a `docs/` contract a skill
needs:** keep the full authority/rationale in `docs/` (origin of record) and put a
**concise operational digest** in `uacp-core/references/`; the skill cites the digest.
Not duplication — two purposes (rationale vs operational contract). The goal-driven
mirror (`uacp-core/references/goal-driven-track.md`, which digests the goal-driven
track's ADR) is the template. A
digest MAY carry one "Origin of record" provenance line naming its `docs/` source.

**Decision test for any new reference doc** — *"Will a skill's instructions cite it
to operate?"* Yes → skill tree (shared/kernel → `uacp-core/references/`; single-skill
→ that skill's `references/`). No (authority / rationale / history) → `docs/`.

**Paths:** use the runtime-neutral `UACP_ROOT/…` token for skill-tree paths (CC → the
plugin root ≈ `${CLAUDE_PLUGIN_ROOT}`; Hermes → the repo/skill-store root). Source
`*.py` files MAY cite ADRs in comments (provenance in code).

> **Enforcement.** `tests/unit/skills/test_skill_self_containment.py` enforces: no
> citation of the abolished top-level shared references dump (gone), and no
> `ADR-<number>` in `SKILL.md` bodies (cite the `uacp-core/references/` digest). The
> `docs/`-back-pointer ban is being applied to the existing lifecycle skills in a
> dedicated cleanup slice (drop "further reading" pointers; digest the
> operationally-needed ones) and the lint widens to enforce it once that lands.
> Until then, ~60 pre-existing `docs/` pointers in lifecycle skills are known
> transition debt. **New/refactored skills must follow the rule now.**

## Reference-document policy

The reference layer must not balloon into a second dumping ground. **The default is
EXTEND, not create.** Each reference doc owns a **topic**; when a skill needs reference
material, first find the existing doc that owns that topic and **fold the material into
it**. Creating a *new* file is the rare exception. Check `uacp-core/references/index.md`
(the index) first — it answers "which doc owns this topic?" in seconds.

**Creation gate — a NEW reference doc is allowed only if ALL hold:**
1. A skill *instruction* actually needs to cite it (else it belongs in `docs/`, not the skill tree).
2. **No existing reference doc owns the topic** (you checked the index). If one does, EXTEND it — one topic = one doc; do not fragment into near-synonyms.
3. It is a distinct, durable, reusable contract/pattern — not a one-off or session artifact.
4. It is large/standalone enough that folding it into an existing doc would bloat or muddy that doc's single topic.
If any fails → extend an existing doc (or, for non-cited material, put it in `docs/`).

### OKF frontmatter

Every doc in `uacp-core/references/` and `docs/knowledge/` carries Open-Knowledge-Format
frontmatter so the reference/knowledge layer is interoperable across runtimes and tooling:

```yaml
---
type: contract | pattern | digest | lessons | analysis
title: <Human Title>
description: <one-line purpose / trigger>
tags: [<topical>, ...]
timestamp: <ISO date>
resource: <docs/ origin>   # optional; for `type: digest`
---
```

The five `type` values and when to use each:

- **contract** — an operational contract a skill follows; must be followed precisely at runtime.
- **pattern** — a reusable how-to procedure or approach referenced by skill instructions.
- **digest** — a concise mirror of a canonical authority/rationale document (the two-layer pattern).
- **lessons** — distilled session history or post-hoc learning that informs future skill behaviour.
- **analysis** — research or external-source study cited as evidence by a skill instruction.

The per-directory index file is `index.md` (OKF convention). This aligns the reference/knowledge
layer to the Open Knowledge Format for interop.

**Naming:** kebab-case; named by the **contract/topic**, never by date, run-id, or event;
no `-YYYYMMDD` suffixes; one canonical name per topic.

**Two-layer digest pattern** (when a `docs/` contract is what a skill needs): keep the full
rationale in `docs/` (origin of record); put a **concise operational digest** in
`uacp-core/references/`; the skill cites the digest. (See the reference-boundary section.)

**Index:** every doc in `uacp-core/references/` is listed in `uacp-core/references/index.md`
(filename → one-line purpose → citing skill[s]); update it on every add/remove.

**Enforced (lint):** every `uacp-core/references/*.md` is cited by ≥1 skill (an uncited
reference does not belong in the skill tree); every such doc is listed in the index;
filenames are kebab-case with no date suffix. See `tests/unit/skills/`.

## DRY shared content

Content shared across skills lives once under **`uacp-core/references/`** (the kernel skill every skill may cite) and is cited with a "Read when…" pointer, not re-inlined. There is no top-level shared dump under `skills/` outside a skill dir.

## Authoring checklist

1. Pick `kind`; create `skills/<kebab-name>/SKILL.md` with the minimum frontmatter
   for that kind (`references/frontmatter-by-kind.md`).
2. Write the body imperative and < 500 lines; move detail to `references/`.
3. Reference only in-plugin files (stay inside the plugin/repo root; use the
   `UACP_ROOT/…` root token). Prefer a concise `uacp-core/references/` digest for a
   durable shared contract over pointing instruction at a sprawling `docs/` ADR.
4. Do not inline content that already exists under `uacp-core/references/`.
5. Run `python3 -m pytest tests/unit/skills/ -q` before committing.

### Where a shared/reference doc lives
- Cited by exactly ONE skill → that skill's own `references/`.
- Shared across many skills, or a kernel-level contract → `uacp-core/references/`.
- Dated session-history / one-off lessons / external analysis cited by no skill → `docs/knowledge/` (reading + provenance; it ships with the plugin, but it is *not* the operational contract — point skill instruction at the `uacp-core/references/` digest, not at history).

## Plugin-readiness checklist
1. Skill is at `skills/<dir>/SKILL.md`; the dir name is the intended `/uacp:<dir>` invocation name.
2. `description` present and within the listing budget; no reserved-key misuse (above).
3. Body < 500 lines; detail in `references/`; cites only shipped files (self-containment).
4. `.claude-plugin/plugin.json` exists at the plugin root (one-time).
5. `python3 -m pytest tests/unit/skills/ -q` passes (self-containment + readiness lint).
