---
type: plan
title: "Step 2 · Slice 4 — Frontmatter slim + `kind` rollout"
description: "Slice 4 plan to drop vestigial authority mirrors from lifecycle skills and roll the `kind:` classifier to all 23 skills"
tags: ["step2", "frontmatter", "kind", "skills"]
timestamp: 2026-06-17
status: archived
---

# Step 2 · Slice 4 — Frontmatter slim + `kind` rollout

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bring every skill's frontmatter into convention compliance: drop the vestigial authority mirrors from lifecycle skills, roll the `kind:` classifier to all skills, sweep the last `context: reference` reserved-key offenders, and enforce all three with the lint. Flip the convention's "rollout status" caveats to done for frontmatter.

**Scope note:** the `docs/`-citation-class lint widening (60 `docs/` read-pointers across 12 skills) is **NOT** in this slice — it is a genuine design decision (mirror vs drop vs accept-as-repo-context), surfaced separately. Slice 4 is frontmatter only.

**Architecture:** Frontmatter edits + lint enforcement. No body/behavioral change. The dropped mirrors are already non-functional (CC ignores underscore keys; the runtime reads the codified grammar). Branch `skills/step2-slice4-frontmatter-kind`. Baseline suite 827/2.

## The `kind` table (23 skills)
| kind | skills |
|---|---|
| `kernel` | uacp-core |
| `lifecycle` | uacp-triage, uacp-propose, uacp-plan, uacp-execute, uacp-verify, uacp-resolve, uacp-state |
| `reference` | uacp-bridge ✓, domain-registry, uacp-council-taxonomy, uacp-skills ✓ |
| `orchestration` | uacp, uacp-council, uacp-debate, uacp-parallel, uacp-context, uacp-brainstorm, uacp-web, uacp-guardian, uacp-heartgate, uacp-lifecycle, state |

(✓ = already declares `kind: reference`; leave as-is. The "orchestration" set includes the router `uacp` + the compatibility-conductor skills `uacp-guardian`/`uacp-heartgate`/`uacp-lifecycle`/`state` — invocable routers, not phase/kernel/pure-reference. Flag for council if a better fit exists.)

---

## Task 1: Drop vestigial authority mirrors (7 lifecycle skills)
**Files:** `skills/uacp-{triage,propose,plan,execute,verify,resolve,state}/SKILL.md`

For each, remove the frontmatter keys `allowed_tools:`, `forbidden_tools:`, and `phase_exit_invariants:` (and their list items). **KEEP** `name`, `description`, `phase`, `authority_source`, and (uacp-state only) `cross_phase` + `note`. The runtime reads these from the codified grammar (`uacp-core/scripts/engines/domain/phase_transitions.py`); `authority_source` already points there. Verify the YAML still parses (frontmatter delimited correctly).

Suite green. Commit: `refactor(skills): drop vestigial allowed_tools/forbidden_tools/phase_exit_invariants mirrors from lifecycle frontmatter (authority is the codified grammar)`.

## Task 2: Roll `kind:` to all skills + sweep `context:`
**Files:** all `skills/*/SKILL.md` lacking `kind:` (21 of 23).

Add `kind: <value>` to each per the table above (place it after `description`/`phase`). For the 2 `reference` skills that still carry the reserved-key footgun — `domain-registry` and `uacp-council-taxonomy` — **remove `context: reference`** and add `kind: reference` (kind carries the semantic; `context` is CC-reserved for `fork` only). uacp-bridge + uacp-skills already have `kind: reference` — leave them.

Verify: `grep -L "^kind:" skills/*/SKILL.md` → empty (every skill has kind). `grep -rE "^context: reference" skills/*/SKILL.md` → empty. Suite green. Commit: `refactor(skills): roll kind: classifier to all skills + sweep context:reference reserved-key offenders`.

## Task 3: Enforce in the readiness/self-containment lint
**Files:** `tests/unit/skills/test_plugin_readiness.py` (add) — keep additions minimal.
Add parametrized checks over all `skills/*/SKILL.md` (one-level skill dirs):
- every skill declares `kind:` with a value in `{kernel, lifecycle, reference, orchestration}`.
- no lifecycle skill (`kind: lifecycle`) declares `allowed_tools`/`forbidden_tools`/`phase_exit_invariants` in frontmatter.
- no skill frontmatter sets `context:` to anything other than `fork` (the CC-reserved meaning) — i.e. `context: reference` etc. is forbidden.
Run; all green. `ruff` clean. Commit: `test(skills): enforce kind: classifier + no authority mirrors + no context reserved-key misuse`.

## Task 4: Flip the convention's rollout-status caveats
**Files:** `skills/uacp-skills/SKILL.md`, `docs/architecture/0017-skill-authoring-convention.md`
- In `uacp-skills/SKILL.md`: the "Rollout status" note (in the kind taxonomy section) and the reserved-key "Rollout:" caveat — update to state the frontmatter normalization (mirrors dropped, `kind:` rolled out, `context:` swept) is now **complete and lint-enforced**. Remove the "some skills still carry…" hedges for these (they no longer do).
- In ADR-0017: update the Consequences/Status to note Slice 4 done (frontmatter + kind complete, enforced). Add that the **`docs/`-citation class remains an open decision** (60 read-pointers; mirror vs drop vs accept) — explicitly NOT yet enforced, so the convention's self-containment rule currently binds the ADR-citation + abolished-dump classes, with the broad `docs/` class pending an operator decision.
Suite green. Commit: `docs(convention): flip frontmatter rollout caveats to done; record docs/-class as the remaining open decision`.

## Task 5: Full verification + council
- `python3 -m pytest -q` 0 failures (≥ 827/2). `ruff check tests/` clean. `claude plugin validate .` passes.
- Every skill has a valid `kind:`; no lifecycle mirror remains; no `context: reference` remains.
- Do NOT merge — council gate (lighter: 1 architecture/conformance lens is sufficient for a bounded frontmatter slice; add devil's-advocate if the lens flags anything).

## After this plan
1. Council; resolve findings; merge `--no-ff`; delete branch.
2. **Step 2 is then COMPLETE** (Slices 1-4). Surface the remaining cross-cutting decision: the **`docs/`-citation class** — what to do with the 60 `docs/` read-pointers in skill bodies (mirror durable ones into `uacp-core/references/`, drop "additional reading" pointers, or formally accept canonical-doc pointers as a self-containment carve-out). This is its own brainstorm/decision, not auto-bundled.

## Out of scope
- The `docs/`-citation-class lint widening + any relocation of canonical docs (separate decision).
- Any skill body/behavioral change; renaming dirs; the conductor/router taxonomy redesign (classified as orchestration for now).
