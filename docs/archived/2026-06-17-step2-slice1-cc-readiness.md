# Step 2 · Slice 1 — Claude Code plugin readiness + convention re-grounding

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the UACP skills library an actually-installable **Claude Code plugin** (skills only) and re-ground the `uacp-skills` convention + ADR-0017 in the *real* dual-target (Claude Code + Hermes) plugin format — verified against the official CC plugin/skills spec. Hermes packaging stays deferred-but-ready.

**Architecture:** Docs/structure only; no runtime-behavior change, no skill *content* rewrites. Add the CC plugin manifest; relocate the one mis-placed skill so it's discoverable; correct the rulebook (which was install-naive); add a readiness lint so conformance is enforced going forward.

**Tech Stack:** Markdown skills; JSON manifest; `pytest` (`python3`, `testpaths=["tests"]`); `ruff` at `/Users/mike/.local/bin/ruff`. Baseline suite: 633 passed / 2 skipped.

**Design source / grounding:** `docs/plans/2026-06-16-step2-eval-maps.md`; ADR-0017; the authoritative CC spec (https://code.claude.com/docs/en/plugins.md, plugins-reference.md, skills.md). Branch: `skills/step2-slice1-cc-readiness` (already carries the eval-maps doc).

## Authoritative facts this slice relies on (from the CC spec)
- A plugin is declared by `.claude-plugin/plugin.json` at the plugin root; **required field `name`** (kebab-case); `description`/`version` recommended. Unknown top-level keys are **silently ignored**.
- Skills auto-discover from `skills/<skill-name>/SKILL.md`. **A bare `skills/SKILL.md` (not in a named subdir) is NOT discovered.**
- **Invocation name = the skill's DIRECTORY name** (namespaced `/<plugin>:<dir>`); frontmatter `name:` is only a display label.
- CC **silently ignores unknown frontmatter keys** (so `phase`, `authority_source`, `kind`, `location`, `metadata.hermes`, `allowed_tools` [underscore] do NOT break loading). But these keys are **reserved with real CC meaning** — do not use them for non-CC purposes: `context` (only `fork`), `allowed-tools`/`disallowed-tools`, `model`, `effort`, `agent`, `hooks`, `paths`, `disable-model-invocation`, `user-invocable`, `argument-hint`, `arguments`, `shell`.
- `references/`, `scripts/`, `assets/` inside a skill dir ship and stay readable. `description` (with `when_to_use`) is capped at 1536 chars in the skill listing. SKILL.md < 500 lines advisory.
- Hermes reads `metadata.hermes.*` and loads from `~/.hermes/skills/devops/uacp/<name>/SKILL.md`; it ignores CC keys and vice-versa, so one frontmatter serves both.

---

## Task 1: Add the Claude Code plugin manifest

**Files:** Create `.claude-plugin/plugin.json`

**Step 1: Write the manifest**
```json
{
  "name": "uacp",
  "description": "Universal Agent Control Plane — runtime-neutral governance, six-phase lifecycle (TRIAGE→PROPOSE→PLAN→EXECUTE→VERIFY→RESOLVE), Guardian/Heartgate enforcement, and Agent Council orchestration, as installable skills.",
  "version": "0.1.0",
  "license": "see repository"
}
```
(Only `name` is required. Skills auto-discover from `skills/` — do NOT add a `skills` array; auto-discovery covers it. Do NOT declare `hooks`/`mcpServers` — Guardian enforcement wiring is a separate, deferred effort, out of scope here.)

**Step 2: Validate if the CLI is available**
Run: `claude plugin validate . 2>/dev/null || echo "claude CLI not available — skip (manifest is spec-valid JSON)"`
Expected: validation passes, or the CLI is absent (acceptable — the JSON is well-formed and spec-conformant).

**Step 3: Commit**
```bash
git add .claude-plugin/plugin.json
git commit -m "feat(plugin): add Claude Code plugin manifest (name: uacp, skills auto-discovered)"
```

---

## Task 2: Relocate the `uacp` router so it is discoverable

The router lives at `skills/SKILL.md` (bare) → **not discovered** by a CC plugin loader. Move it into a named subdir.

**Files:** `skills/SKILL.md` → `skills/uacp/SKILL.md` (+ fix its internal reference pointers)

**Step 1: Move with git**
```bash
mkdir -p skills/uacp && git mv skills/SKILL.md skills/uacp/SKILL.md
```

**Step 2: Fix its internal reference pointers**
The body cites ~10 `references/<file>.md` pointers that mean `skills/references/<file>.md` (resolved relative to the old `skills/` location). From `skills/uacp/`, those now need `../references/<file>.md` to keep resolving. Edit every body reference of the form `` `references/… ` `` → `` `../references/… ` `` (lines ~34, 50, 78, 113, 117, 121, 125, 127, 129 and any others — grep to be exhaustive).

Run after editing: `grep -nE '\breferences/' skills/uacp/SKILL.md` → every hit must be `../references/…` (no bare `references/…`).

> NOTE: `../references/` (the shared dump) is pre-existing debt; the later references slice repoints these to their final homes (`uacp-core/references/` or `docs/knowledge/`) when it abolishes `skills/references/`. Slice 1 only keeps them resolving.

**Step 3: Check nothing external hardcoded the bare path + phase4_verify still passes**
- `grep -rn "skills/SKILL.md" --include=*.py --include=*.md . | grep -v docs/plans` → expect no live code/skill pointer (only this plan / historical docs).
- Run `python3 scripts/phase4_verify.py 2>&1 | tail -5` if it exists — confirm the new `skills/uacp/` dir doesn't trip its `uacp-*` mode_behavior check (the dir is `uacp`, the router is not a phase skill). If it newly flags `skills/uacp`, adjust the check's scope to phase skills only (smallest fix) and note it.

**Step 4: Confirm discovery + suite**
- `ls skills/uacp/SKILL.md` exists; `test ! -f skills/SKILL.md` (bare one gone).
- `python3 -m pytest tests/unit/skills/ -q` → green (the `**/SKILL.md` glob now catches `skills/uacp/SKILL.md`; it cites no ADR).

**Step 5: Commit**
```bash
git add -A skills/uacp/ skills/SKILL.md
git commit -m "refactor(skills): move uacp router to skills/uacp/SKILL.md so it is plugin-discoverable

A bare skills/SKILL.md is not discovered by the CC plugin loader (skills must be in
named subdirs). Internal references/ pointers rewritten to ../references/ to keep
resolving until the references slice finalizes them."
```

---

## Task 3: Re-ground the `uacp-skills` convention in the real plugin format

**Files:** Modify `skills/uacp-skills/SKILL.md`; modify `skills/uacp-skills/references/frontmatter-by-kind.md`

**Step 1: Add a "Plugin packaging (the install target)" section to `skills/uacp-skills/SKILL.md`**
Insert after the "Progressive disclosure" section, before "The `kind` taxonomy":
```markdown
## Plugin packaging (the install target)

These skills ship as a **Claude Code plugin** (and, deferred-but-ready, a Hermes skill package). The convention exists so they load correctly once installed. Conform to the real format:

- **Manifest:** the plugin root carries `.claude-plugin/plugin.json` (`name: uacp` — this namespaces every skill as `/uacp:<dir>`). Adding/owning the manifest is a one-time packaging step, not per-skill.
- **Location = discovery:** every skill MUST be `skills/<dir>/SKILL.md`. A bare `skills/SKILL.md` is **not discovered**. The plugin loader auto-discovers from `skills/`.
- **Directory name = invocation name.** `skills/uacp-execute/` → `/uacp:uacp-execute`. Frontmatter `name:` is only a display label — do not rely on it for invocation, and keep dir name = intended invocation name.
- **Do not misuse reserved Claude Code frontmatter keys.** CC silently ignores *unknown* keys (so our `phase`/`authority_source`/`kind`/`location`/`metadata` are harmless), but these keys have real CC meaning — only use them for that meaning: `context` (value `fork` only), `allowed-tools`/`disallowed-tools`, `model`, `effort`, `agent`, `hooks`, `paths`, `disable-model-invocation`, `user-invocable`, `argument-hint`, `arguments`, `shell`.
- **Bundled resources ship:** `references/`, `scripts/`, `assets/` under a skill dir are bundled and readable at their relative paths. Keep `description` (+ `when_to_use`) under ~1536 chars (the listing budget) and SKILL.md under 500 lines.

**Dual-target (Hermes).** The same files install into Hermes' skill store (`~/.hermes/skills/devops/uacp/<dir>/SKILL.md`); Hermes reads `metadata.hermes.{tags,related_skills}`. CC ignores the Hermes keys and Hermes ignores the CC keys, so one frontmatter serves both. Hermes packaging/sync is deferred but the layout is ready.

**Deferred (not built yet):** the Hermes sync mechanism, marketplace publication, and the Guardian-enforcement hooks for CC (a separate effort). This convention is about being *loadable and readable*; distribution is a follow-up.
```

**Step 2: Fix the shared-home in the DRY + self-containment sections of `skills/uacp-skills/SKILL.md`**
- In "## Self-containment rule": the mirror home is `uacp-core/references/` (already correct) — no change beyond confirming.
- In "## DRY shared content": replace the sentence naming `skills/references/` as the shared home with:
  `Content shared across skills lives once under **\`uacp-core/references/\`** (the kernel skill every skill may cite) and is cited with a "Read when…" pointer, not re-inlined. There is no top-level \`skills/references/\` shared dump.`
- In the "Authoring checklist", update step 4 to reference `uacp-core/references/` instead of `skills/references/`.

**Step 3: Add the destination rule + a plugin-readiness checklist to `skills/uacp-skills/SKILL.md`**
Append a short subsection under DRY:
```markdown
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
```

**Step 4: Update `skills/uacp-skills/references/frontmatter-by-kind.md`**
Add a leading note: "Invocation name comes from the skill **directory** name, not `name:`; `name:` is a display label. Avoid Claude-Code-reserved keys (`context`, `allowed-tools`, `model`, `effort`, `agent`, `hooks`, `paths`, …) except for their real CC meaning." Keep the per-kind examples. Where the `reference` example shows `context: reference`, change it to `kind: reference` only (drop the reserved `context` key) so the convention's own example is conformant.

**Step 5: Verify + commit**
- `grep -nE "skills/references" skills/uacp-skills/SKILL.md` → zero (shared home is now uacp-core/references).
- `wc -l skills/uacp-skills/SKILL.md` → < 500.
- `python3 -m pytest tests/unit/skills/ -q` → green.
```bash
git add skills/uacp-skills/
git commit -m "docs(uacp-skills): re-ground convention in real CC plugin format + dual-target; shared home = uacp-core/references"
```

---

## Task 4: Re-ground ADR-0017

**Files:** Modify `docs/architecture/0017-skill-authoring-convention.md`

**Step 1: Add a Decision-Outcome bullet** (after the "Structure & disclosure" bullet):
```markdown
- **Plugin packaging (the install target):** the library ships as a Claude Code plugin — `.claude-plugin/plugin.json` (`name: uacp`) at the repo/plugin root; skills auto-discover from `skills/<dir>/SKILL.md`; **invocation name = directory name** (frontmatter `name:` is a label); do not misuse Claude-Code-reserved frontmatter keys (`context`, `allowed-tools`, `model`, `effort`, `agent`, `hooks`, `paths`, …). The same files are Hermes-ready (`metadata.hermes.*`, `~/.hermes/skills/devops/uacp/`). Hermes sync, marketplace publication, and CC Guardian-hook enforcement are deferred follow-ups; this ADR governs being *loadable and readable*, not distribution.
```

**Step 2: Fix the shared-home references** — change the "DRY shared content" decision bullet and the Step-2 consequence bullet from `skills/references/` to `uacp-core/references/`; add that the top-level `skills/references/` dump is abolished (relocation handled in the references slice).

**Step 3: Add a Consequences bullet:**
```markdown
- **Plugin-ready, not yet distributed:** after this convention, the library installs as a CC plugin and is Hermes-ready, but is not auto-synced to either runtime; distribution remains an explicit step.
```

**Step 4: Commit**
```bash
git add docs/architecture/0017-skill-authoring-convention.md
git commit -m "docs(adr-0017): add plugin-packaging decision (CC manifest, dir=invocation, reserved keys); shared home = uacp-core/references"
```

---

## Task 5: Readiness lint (enforce layout going forward)

**Files:** Modify `tests/unit/skills/test_skill_self_containment.py` (add readiness checks) OR create `tests/unit/skills/test_plugin_readiness.py`. Prefer a new file for clarity.

**Step 1: Write the failing test first** — create `tests/unit/skills/test_plugin_readiness.py`:
```python
"""Plugin-readiness lint: skills must be in the shape the Claude Code plugin
loader discovers and reads (ADR-0017 'Plugin packaging').

Step-1 scope: enforce the two things that affect LOADING — every skill is at
skills/<dir>/SKILL.md (no bare skills/SKILL.md; the loader skips it), and each
SKILL.md has a usable description. Frontmatter reserved-key normalization is
enforced once the kind rollout lands (later frontmatter slice).
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = REPO_ROOT / "skills"
DESCRIPTION_BUDGET = 1536


def _skill_md_files() -> list[Path]:
    return sorted(SKILLS_DIR.glob("**/SKILL.md"))


def test_plugin_manifest_present() -> None:
    assert (REPO_ROOT / ".claude-plugin" / "plugin.json").is_file(), (
        "Claude Code plugin manifest missing (.claude-plugin/plugin.json)"
    )


def test_no_bare_skills_root_skill() -> None:
    # A SKILL.md directly under skills/ (not in a named subdir) is NOT discovered
    # by the CC plugin loader. Every skill must live in skills/<dir>/SKILL.md.
    assert not (SKILLS_DIR / "SKILL.md").exists(), (
        "skills/SKILL.md is not plugin-discoverable; move it into a named subdir "
        "(e.g. skills/uacp/SKILL.md)"
    )


@pytest.mark.parametrize("skill_md", _skill_md_files(), ids=lambda p: p.parent.name)
def test_skill_in_named_subdir(skill_md: Path) -> None:
    # SKILL.md must be exactly skills/<dir>/SKILL.md (one level under skills/).
    rel = skill_md.relative_to(SKILLS_DIR)
    assert len(rel.parts) == 2 and rel.parts[1] == "SKILL.md", (
        f"{skill_md.relative_to(REPO_ROOT)} is not at skills/<dir>/SKILL.md"
    )


@pytest.mark.parametrize("skill_md", _skill_md_files(), ids=lambda p: p.parent.name)
def test_description_present_and_within_budget(skill_md: Path) -> None:
    text = skill_md.read_text(encoding="utf-8")
    assert text.startswith("---"), f"{skill_md} missing YAML frontmatter"
    fm = text.split("---", 2)[1]
    assert "description:" in fm, f"{skill_md.relative_to(REPO_ROOT)} has no description"
    # crude length guard on the description block (multi-line allowed)
    for line in fm.splitlines():
        if line.strip().startswith("description:"):
            inline = line.split("description:", 1)[1].strip()
            if inline and len(inline) > DESCRIPTION_BUDGET:
                pytest.fail(
                    f"{skill_md.relative_to(REPO_ROOT)} description exceeds "
                    f"{DESCRIPTION_BUDGET} chars"
                )
```

**Step 2: Run** — `python3 -m pytest tests/unit/skills/test_plugin_readiness.py -q`. If Task 1 & 2 are done, all pass. If you run this BEFORE Task 1/2, `test_plugin_manifest_present` and `test_no_bare_skills_root_skill` fail (expected — confirms the lint bites). Order: write the lint, confirm it would have caught the pre-move state (note it), then ensure green post-move.

**Step 3: Lint + commit**
```bash
/Users/mike/.local/bin/ruff check tests/unit/skills/test_plugin_readiness.py
git add tests/unit/skills/test_plugin_readiness.py
git commit -m "test(skills): plugin-readiness lint — manifest present, skills in named subdirs, description budget"
```

---

## Task 6: Full-suite regression + final verification

**Step 1:** `python3 -m pytest -q` → 0 failures (baseline 633/2 + the new readiness tests).
**Step 2:** `/Users/mike/.local/bin/ruff check tests/unit/skills/` → clean.
**Step 3:** Confirm: `.claude-plugin/plugin.json` valid; `skills/uacp/SKILL.md` exists; no bare `skills/SKILL.md`; `git status` clean; `git log --oneline main..HEAD`.
**Step 4:** Do NOT merge — council gate first.

---

## After this plan
1. **Council** (skill-library/governance change): architecture/governance lens + devil's-advocate lens over the diff (focus: is the convention now faithful to the real CC spec? does the move break any live pointer? is the readiness lint correct and non-overreaching?). Resolve material findings.
2. **Merge** `--no-ff` to `main`, delete branch.
3. Next slices: **2 — bridge collapse** (maps ready), **3 — references relocation/merge** (abolish `skills/references/`, finalize the router's `../references/` pointers, create `docs/knowledge/`), **4 — frontmatter slim + `kind` rollout** (drop vestigial mirrors, roll `kind:` to all, kill the `context:` footgun, add reserved-key enforcement to the readiness lint).

## Out of scope (later slices / deferred)
- Bridge collapse; references relocation; frontmatter slim + `kind` rollout.
- Hermes sync mechanism; marketplace publication; CC Guardian-enforcement hooks.
- Per-skill frontmatter normalization beyond the `uacp-skills` example fix.
