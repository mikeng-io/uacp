---
type: plan
title: "Step 2 · Slice 5 — Reference-document policy + `docs/` back-pointer cleanup"
description: "Slice 5 plan to codify the anti-proliferation reference-doc policy and resolve remaining `docs/` back-pointers in lifecycle skills"
tags: ["step2", "reference-policy", "docs", "skills"]
timestamp: 2026-06-17
status: archived
---

# Step 2 · Slice 5 — Reference-document policy + `docs/` back-pointer cleanup

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the one-directional reference boundary fully real and self-enforcing: codify a strict reference-document policy for the skill tree (anti-proliferation gate + naming + index), resolve the remaining `docs/` back-pointers in the lifecycle skills under that policy, and widen the lint to enforce it.

**Architecture:** Convention + index + lint + a bounded set of skill-body edits (resolve 5 distinct `docs/` targets across 7 skills). The boundary rule (skills cite only the skill tree; `docs/` one-directional) is already in `uacp-skills`/ADR-0017 — this slice adds the *reference-doc policy* under it and makes it enforced. Branch `skills/step2-slice5-refdoc-policy-and-docs-cleanup`. Baseline suite 896/2.

## The reference-document policy (to codify)

**Default = EXTEND, not create.** Each reference doc owns a **topic**; when a skill
needs reference material, the first and strong default is to **fold it into the
existing doc that owns that topic**. Creating a *new* file is the rare exception that
must be justified against the gate below. The `uacp-core/references/README.md` index
is the lookup tool — scan it first to find the topical home before writing anything.

**Creation gate (required review checklist + council) — a new doc is allowed ONLY if ALL hold:**
1. A skill *instruction* actually needs to cite it (else → `docs/`, not the skill tree).
2. **No existing reference doc owns this topic** (you checked the index) — if one does,
   EXTEND it. One topic = one doc; do not fragment into near-synonyms.
3. It is a distinct, durable, reusable contract/pattern — not a one-off/session artifact.
4. It is large/standalone enough that folding it into an existing doc would bloat or
   muddy that doc's single topic.
Only when 1–4 ALL hold → create, named by topic/contract. Otherwise → extend an existing doc.

**Naming:** kebab-case; named by the contract/topic, never by date/run-id/event; no `-YYYYMMDD` suffixes; one canonical name per topic (no near-synonym fragmentation).

**Two-layer digest pattern:** a `docs/` contract a skill needs → full rationale stays in `docs/`; concise operational digest in `uacp-core/references/`; skill cites the digest.

**Index:** `uacp-core/references/README.md` lists every doc → one-line purpose → citing skill(s).

**Enforced mechanically (lint):** (a) every `uacp-core/references/*.md` is cited by ≥1 skill; (b) every such doc is listed in the index; (c) naming (kebab-case, no date suffix); (d) no `UACP_ROOT/docs/…` **citation** in SKILL.md bodies (the rooted read-pointer form — bare `docs/` prose mentions, e.g. in the convention/router, are allowed).

---

## Task 1: Codify the reference-document policy in `uacp-skills`
**Files:** `skills/uacp-skills/SKILL.md` (add a "## Reference-document policy" section after the reference-boundary section); optionally a `skills/uacp-skills/references/reference-doc-policy.md` if the section would push SKILL.md detail too far (keep SKILL.md < 500 lines).
Write the creation gate (4 questions), naming convention, the two-layer digest pattern (already partly there — cross-link), and the index requirement. **Do NOT write the literal `skills/references/` path or an `ADR-<digit>` token in this file** (the lint scans it — describe indirectly). Suite green. Commit.

## Task 2: Build the `uacp-core/references/` index
**Files:** Create `skills/uacp-core/references/README.md`.
Table of the 12 current docs: filename → one-line purpose → citing skill(s) (grep each doc's basename across `skills/*/SKILL.md` to find citers). Note: this index is lint-checked for completeness in Task 5. Add a header noting the directory holds shared/kernel operational references that ≥1 skill cites (per the reference-doc policy). Suite green. Commit.

## Task 3: Triage the two judgment targets (lifecycle-reference, orchestration-model)
Dispatch an assessment of `docs/lifecycle/lifecycle-reference.md` and `docs/lifecycle/orchestration-model.md`: for each, determine whether the lifecycle skills cite it for **operationally load-bearing** content (a contract the skill needs to act) vs **context/authority** ("read for the full picture"). Produce a per-doc disposition:
- **drop** the skill read-pointers (content is authority/context; skills function from their own bodies + codified grammar + existing `uacp-core/references` digests), OR
- **digest** the operationally-needed essence into `uacp-core/references/` — **prefer extending an existing doc** (e.g. fold lifecycle-gate operational bits into `lifecycle-semantic-gates.md`) over creating a new one (gate question 2); only create a new doc if the gate passes.
Operator reviews the disposition before Task 4 applies it. (Default lean: these are canonical *authority/context* docs → drop the pointers unless a specific operational contract is found that isn't already in a skill body or an existing digest.)

## Task 4: Resolve the `docs/` back-pointers across the 7 skills
Apply, per the dispositions:
- **`docs/reference/operator-phase-return-schema.md`** (×6: execute/plan/propose/resolve/verify/triage) → **repoint** to `uacp-core/references/operator-phase-return-presentation.md` (existing digest). Confirm that digest covers the schema the skills need; if a gap, extend it (don't create new).
- **`docs/INDEX.md`** (×6) → **drop** the read-pointer (repo navigation; not operational). Keep the surrounding "Read first/Read additionally" list coherent (remove the line).
- **`docs/policy/constitution.md`** (×2: propose/state) → **drop** (authority that governs skills).
- **`docs/lifecycle/lifecycle-reference.md`** (×6) and **`docs/lifecycle/orchestration-model.md`** (×6) → apply Task 3's disposition (drop or repoint-to-digest).
After: `grep -rn "UACP_ROOT/docs/" skills/*/SKILL.md` → ZERO. Each repointed `uacp-core/references/…` target exists. (Leave `UACP_ROOT/config/…` references alone — config/ is operational policy, out of scope for the docs/ boundary; note it.) Suite green. Commit (can batch per a few skills).

## Task 5: Reference-doc lint (the teeth) + widen self-containment to `docs/`
**Files:** `tests/unit/skills/test_skill_self_containment.py` and/or `test_plugin_readiness.py`.
Add:
1. **cited-by-≥1-skill:** every `skills/uacp-core/references/*.md` (excluding `README.md`) is cited by at least one `skills/*/SKILL.md` (grep its basename). Fail naming the orphan. (This is the anti-proliferation teeth — an uncited reference doesn't belong in the skill tree.)
2. **index-complete:** every `uacp-core/references/*.md` (excluding README) is listed in `uacp-core/references/README.md`, and the index lists no nonexistent file.
3. **naming:** `uacp-core/references/*.md` filenames are kebab-case with no `-\d{8}` date suffix.
4. **docs/ citation ban (widen):** no `SKILL.md` body contains the rooted citation form `UACP_ROOT/docs/` (the read-pointer form). Do NOT forbid bare `docs/` prose mentions (the convention/router legitimately describe `docs/`). Sanity-check: this must pass after Task 4 (no `UACP_ROOT/docs/` left) and must FAIL if one is re-added (mutation check).
Run all; green. ruff clean. Commit.

## Task 6: Full verification + council
- `python3 -m pytest -q` 0 failures; `ruff check tests/` clean (note any pre-existing unrelated finding); `claude plugin validate .` passes.
- `grep -rn "UACP_ROOT/docs/" skills/*/SKILL.md` → ZERO; every `uacp-core/references` doc cited + indexed; README index complete.
- Update ADR-0017 + decision-log: the `docs/`-back-pointer cleanup is DONE and lint-enforced; the reference-doc policy is codified + lint-enforced; Step 2 fully closed.
- Council (1–2 lens): boundary now enforced (no skill cites docs/ via the rooted form); the policy lint is non-vacuous (mutation-tested); no operational content lost in the drops/digests (spot-check lifecycle-reference/orchestration-model dispositions); index accurate.
- Do NOT merge until council clears.

## After this plan
- Merge `--no-ff`; delete branch. **Step 2 fully complete + the reference boundary/policy is self-enforcing.**
- Remaining (deferred, separate): distribution (Hermes-store sync + CC marketplace publish); optionally extend the boundary policy to `config/` references if desired.

## Out of scope
- `config/` citations (operational policy, not authority — left as-is this slice).
- Distribution; per-skill `references/` index (only `uacp-core/references/` gets the central index — per-skill refs are scoped to their skill and governed by the same gate).
