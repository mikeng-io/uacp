# UACP Skills Convention — Step 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Author the `uacp-skills` convention meta-skill, mirror the goal-driven contract into `uacp-core` (a shipping skill), and repoint the five in-flight goal-driven SKILL.md edits to cite that mirror instead of the non-shipping `ADR-0016` — backed by a self-containment regression test.

**Architecture:** Documentation/structure only — zero runtime-behavior change. A new pytest tripwire forbids ADR citations in SKILL.md instruction bodies (the dangling-reference class the operator flagged). A new `skills/uacp-core/references/goal-driven-track.md` becomes the shipped, citable mirror of the goal-driven kernel contract; the five lifecycle skills cite it. A new `skills/uacp-skills/` skill codifies the library convention (UACP's analog of Anthropic `skill-creator`).

**Tech Stack:** Markdown skills; `pytest` (system `python3`, `testpaths=["tests"]`); `ruff` at `/Users/mike/.local/bin/ruff`. Baseline suite: 604 passed / 2 skipped (606 collected).

**Design source:** `docs/plans/2026-06-16-uacp-skill-convention-design.md` (approved).

**Branch:** `skills/uacp-skill-convention` (already created; carries the 5 uncommitted goal-driven SKILL.md edits + the committed design doc).

---

## Conventions for the implementer

- Run tests with `python3 -m pytest <path> -q` from the repo root (`/Users/mike/Workplace/uacp`). Do **not** use anaconda python 3.8.
- Lint Python with `/Users/mike/.local/bin/ruff check <path>`.
- The **self-containment rule** distinguishes *instruction prose* from *source provenance*: `SKILL.md` bodies must not cite `ADR-NNNN` (an installed agent can't read `docs/`). Source files (`*.py`) **may** cite ADRs in comments/docstrings — that is origin-of-record provenance and ships as code. The Step 1 test therefore scans `SKILL.md` files only, not `*.py`.
- `docs/` path references inside lifecycle SKILL.md bodies are **out of scope for Step 1** (they are pervasive and legitimate today; tightening them is Step 2). Do not touch them.

---

## Task 1: Self-containment regression test (TDD — write it failing first)

**Files:**
- Create: `tests/unit/skills/__init__.py` (empty, only if `tests/unit/skills/` does not already resolve as a package — check first; the repo uses plain dirs, so an empty `__init__.py` is harmless and matches sibling `tests/unit/uacp_core/` if it has one).
- Create: `tests/unit/skills/test_skill_self_containment.py`

**Step 1: Write the failing test**

```python
"""Self-containment tripwire for UACP skill instruction bodies (Step 1).

Convention (skills/uacp-skills): a SKILL.md body must reference only files that
ship with some skill. An installed coding agent receives the skill directory,
NOT the repo's docs/ tree, so an ADR citation in instruction prose dangles.

Scope (Step 1): forbid ``ADR-<number>`` citations in SKILL.md bodies. Source
files (*.py) may cite ADRs as origin-of-record provenance and are NOT scanned.
The broader docs/ self-containment sweep is Step 2.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = REPO_ROOT / "skills"
ADR_CITATION = re.compile(r"ADR-\d")


def _skill_md_files() -> list[Path]:
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


def test_skills_dir_resolved() -> None:
    # Guard the path math: if this fails, REPO_ROOT/parents is wrong.
    assert SKILLS_DIR.is_dir(), f"skills dir not found at {SKILLS_DIR}"
    assert _skill_md_files(), "no SKILL.md files discovered"


@pytest.mark.parametrize("skill_md", _skill_md_files(), ids=lambda p: p.parent.name)
def test_skill_md_body_cites_no_adr(skill_md: Path) -> None:
    text = skill_md.read_text(encoding="utf-8")
    offenders = [
        f"{i}: {line.strip()}"
        for i, line in enumerate(text.splitlines(), start=1)
        if ADR_CITATION.search(line)
    ]
    assert not offenders, (
        f"{skill_md.relative_to(REPO_ROOT)} cites an ADR in its instruction body "
        f"(cite skills/uacp-core/references/goal-driven-track.md instead). "
        f"Offending lines:\n" + "\n".join(offenders)
    )
```

**Step 2: Run it — expect FAIL on exactly 5 skills**

Run: `python3 -m pytest tests/unit/skills/test_skill_self_containment.py -q`
Expected: 5 parametrized failures — `uacp-execute`, `uacp-plan`, `uacp-propose`, `uacp-resolve`, `uacp-verify` (each cites `ADR-0016`). `test_skills_dir_resolved` passes.

**Step 3: Commit the failing test**

```bash
git add tests/unit/skills/
git commit -m "test(skills): self-containment tripwire — no ADR citations in SKILL.md bodies"
```

---

## Task 2: Mirror the goal-driven contract into `uacp-core` (shipping, citable)

**Files:**
- Create: `skills/uacp-core/references/goal-driven-track.md`

This is the shipped mirror the five lifecycle skills will cite. It digests the *kernel contract* (the code is the authority; this references it) so an installed agent never needs `docs/`. Keep it a contract digest, not a rationale essay — rationale stays in the ADR (origin of record).

**Step 1: Create the directory and file**

Create `skills/uacp-core/references/` if absent, then write `goal-driven-track.md`:

````markdown
# Goal-Driven Track — Kernel Contract (mirror)

> **Read when** a lifecycle skill is operating a run whose `track: goal-driven`.
> Origin of record: ADR-0016 (`docs/architecture/0016-goal-driven-track.md`) — not
> shipped with skills; this file is the shipped, citable mirror of the *enforced
> contract*. The authority is the code cited below, not this prose.

UACP has two lifecycle **tracks** under one phase graph: `standard` (default) and
`goal-driven` (semantic/exploratory work whose success criterion is not specifiable
as a verifiable artifact before EXECUTE). The five phases are reused unchanged;
per-run transitions are forward-only in both tracks (no back-edges).

## Where the contract lives in code (authority)

- `skills/uacp-core/scripts/engines/domain/checkpoint.py` — `CheckpointEntry`
  (the checkpoint manifest record schema, `extra="forbid"`).
- `skills/uacp-core/scripts/engines/domain/budget.py` — `ConvergenceBudget`
  (`max_checkpoints` required, int > 0).
- `skills/uacp-core/scripts/core.py` — Heartgate gates:
  `_validate_convergence_budget_gate` (PROPOSE→PLAN), `_triage_track` (track
  binding), `_validate_goal_driven_checkpoint_gate` (EXECUTE→VERIFY coherence),
  `_validate_goal_driven_closure_gate` (VERIFY→RESOLVE).
- `skills/uacp-state/scripts/state_machine.py` — `handle_init` (`track`,
  `goal_id`, `inherits_from`; `_VALID_TRACKS`), `list_runs_for_goal`.

## The persistent goal + run-chain

A goal-driven run anchors to a **persistent goal** (`goal_id` on the run manifest),
the invariant that does not move. Rollback is NOT an in-run rewind: it is a **new
forward run** under the held goal (`uacp_state_write` init with the same `goal_id`
and `inherits_from: <prior run_id>`), which inherits the parent's triage/proposal/
plan output references. A goal is realized as a *chain* of such runs.

## Convergence budget (PROPOSE→PLAN — BLOCKS without it)

PROPOSE must write `proposals/{run_id}-convergence-budget.yaml`:

```yaml
convergence_budget:
  max_checkpoints: 8     # REQUIRED, integer > 0 — the enforced cap
  max_spend: null        # optional, declare-only (not enforced)
  max_wall_clock: null   # optional, declare-only (not enforced)
```

Without it (or with non-positive `max_checkpoints`), Heartgate blocks PROPOSE→PLAN.
The cap counts `CHECKPOINT` entries across the goal's **whole run-chain**.

## Track binding (un-forgeable)

The run manifest `track` must equal the TRIAGE artifact's `track`
(`proposals/{run_id}-triage*.yaml`). A manifest claiming `goal-driven` over a TRIAGE
artifact that did not decide it fails closed — a worker may not self-select the
track to relax the PIV-artifact gate.

## Checkpoint manifest (EXECUTE)

Each EXECUTE probe is recorded as a `gate: CHECKPOINT` gate-ledger entry (via
`uacp_gate_ledger_append`) carrying a `CheckpointEntry`:

```yaml
checkpoint_id: "<unique within run>"
run_id: "<this run>"
goal_id: "<the held goal>"
phase: execute
what_changed: "what this probe produced/changed"
why: "why this probe, toward the goal"
evidence: "executions/{run_id}/cp-3-hero.png"   # REAL governed-root artifact; prose is rejected
verdict: keep | roll_back | restart
invariant: "the goal invariant this probe is judged against"
rolled_back_to: "<checkpoint_id>"               # only when verdict=roll_back
```

`evidence` must reference a real, governed-root-contained artifact — Heartgate runs
the same no-self-attestation / no-fabrication check it applies to all gate-ledger
evidence. Extra fields BLOCK (`extra="forbid"`).

## EXECUTE→VERIFY coherence (manifest substitutes for the PIV *artifact*)

For a goal-driven run, a COHERENT checkpoint manifest substitutes for the
PIV/execution-evidence *artifact* gate. "Coherent" =: non-empty; every entry
validates as `CheckpointEntry`; every `evidence` ref exists and is contained; total
count ≤ `max_checkpoints` (exactly the cap PASSES; cap+1 BLOCKS); the **final entry's
verdict is `keep`** (a dangling `roll_back`/`restart` has not converged). The PIV
*ledger* gate, authority/containment, and no-fabrication engines still fire.

## VERIFY→RESOLVE closure (coherence + goal binding)

At closure the manifest must be coherent AND the final (promoted) checkpoint's
`goal_id` must equal the run manifest's `goal_id` — a result must satisfy *this*
run's goal. The standard closure invariants (computed engines, Heartgate coherence,
no-fabrication, containment) fire unchanged. RESOLVE then closes the goal: records
the converged checkpoint + the run-chain, and releases the goal anchor
(deregisters the goal's runs).
````

**Step 2: Sanity-check it renders and is self-contained except the one provenance line**

Run: `grep -n "ADR-" skills/uacp-core/references/goal-driven-track.md`
Expected: exactly one line — the `> Origin of record: ADR-0016 …` provenance note. (This is a `references/` file, not a `SKILL.md` body, so the Task 1 test does not scan it; the provenance note is allowed.)

**Step 3: Commit**

```bash
git add skills/uacp-core/references/goal-driven-track.md
git commit -m "docs(uacp-core): mirror goal-driven track kernel contract as a shipped reference"
```

---

## Task 3: Repoint the 5 lifecycle SKILL.md goal-driven sections to the mirror

For each of the five files, replace the `ADR-0016` citation in the goal-driven section with a cite to the shipped mirror. The behavioral prose stays; only the reference changes.

**Files:** `skills/uacp-{execute,plan,propose,resolve,verify}/SKILL.md`

**Step 1: Find the exact citation in each**

Run: `grep -n "ADR-0016" skills/uacp-*/SKILL.md`
Each goal-driven section opens with a phrase like `When the run is `track: goal-driven` (ADR-0016), …`.

**Step 2: Edit each — replace `(ADR-0016)` with the mirror cite**

In each of the five files, change the opening reference from:

> `… (ADR-0016) …`

to:

> `… (see `uacp-core/references/goal-driven-track.md`) …`

Keep wording natural per file. Example for `uacp-execute/SKILL.md`:
`When the run is `track: goal-driven` (the goal-driven track — see `uacp-core/references/goal-driven-track.md`), EXECUTE is …`

Also add, where each goal-driven section already lists "Read additionally" pointers (execute/plan/verify/resolve), a line:
`- `UACP_ROOT/skills/uacp-core/references/goal-driven-track.md` — goal-driven kernel contract (shipped mirror of ADR-0016)`
— note: that "Read additionally" list line MAY name ADR-0016 as parenthetical provenance only if it does NOT match `ADR-\d`? It does match. So do **not** put `ADR-0016` on any SKILL.md line. Phrase it as: `… (shipped mirror of the goal-driven ADR)`. Verify with the Task 1 test.

**Step 3: Run the self-containment test — expect PASS**

Run: `python3 -m pytest tests/unit/skills/test_skill_self_containment.py -q`
Expected: all green (0 ADR citations in any SKILL.md body).

**Step 4: Confirm no goal-driven prose was lost**

Run: `git diff --stat skills/uacp-*/SKILL.md` and eyeball each goal-driven section still describes the checkpoint loop / budget / closure. Only the reference token should have changed versus the prior (uncommitted) state.

**Step 5: Commit**

```bash
git add skills/uacp-execute/SKILL.md skills/uacp-plan/SKILL.md skills/uacp-propose/SKILL.md skills/uacp-resolve/SKILL.md skills/uacp-verify/SKILL.md
git commit -m "docs(skills): goal-driven sections cite uacp-core mirror, not ADR-0016 (self-containment)

Also lands the goal-driven checkpoint-loop guidance for execute/plan/propose/
verify/resolve (triage already had track selection). Behavior unchanged; refs now
point only to shipped files."
```

---

## Task 4: Author the `uacp-skills` convention meta-skill

**Files:**
- Create: `skills/uacp-skills/SKILL.md`
- Create: `skills/uacp-skills/references/frontmatter-by-kind.md`

Keep `SKILL.md` well under 500 lines; push the per-kind frontmatter detail/examples to the reference.

**Step 1: Write `skills/uacp-skills/SKILL.md`**

```markdown
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
| `reference` | read via the Read tool; never invoked standalone | `uacp-bridge`, `domain-registry`, `uacp-skills` |
| `orchestration` | invocable helpers around the lifecycle | council, debate, parallel, context, web, brainstorm |

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
```

**Step 2: Write `skills/uacp-skills/references/frontmatter-by-kind.md`**

```markdown
# Frontmatter by skill `kind`

> **Read when** creating or refactoring a skill and you need the exact frontmatter
> fields for its `kind`. Companion to `../SKILL.md`.

`name` and `description` are required for every kind. `description` is the trigger:
state what the skill does AND when to use it.

## `kind: kernel`
```yaml
name: uacp-core
description: >
  Runtime-neutral UACP core — policy, Guardian evaluation, Heartgate transitions,
  audit, shared filesystem utilities. Imported by runtime adapters; not invoked.
kind: kernel
version: 1.0.0
```

## `kind: lifecycle`
```yaml
name: uacp-execute
description: Use when dispatching bounded UACP work through Hermes Kanban or delegated workers.
kind: lifecycle
phase: execute
authority_source: "engines/domain/{phase_graph,phase_transitions,gate_rules}.py (code-authoritative); config/uacp.toml [heartgate.*] (operator knobs); config/phase-transitions.yaml (LLM-read doctrine + artifact schemas only)"
```
No `allowed_tools` / `forbidden_tools` / `phase_exit_invariants` — codified grammar
is authoritative (see `../SKILL.md` → "no authority mirrors").

## `kind: reference`
```yaml
name: uacp-bridge
description: Reference adapter contract for dispatching to external runtimes. Read via the Read tool; not invocable standalone.
kind: reference
context: reference
```

## `kind: orchestration`
```yaml
name: uacp-council
description: Use when convening an Agent Council for multi-lens review during any phase.
kind: orchestration
```
```

**Step 3: Verify the new skill passes self-containment + has no syntax issues**

Run: `python3 -m pytest tests/unit/skills/ -q`
Expected: green (the new `uacp-skills/SKILL.md` cites no ADR; it references only `references/...`, `uacp-core/...`, `skills/references/...`, and the test path).

**Step 4: Commit**

```bash
git add skills/uacp-skills/
git commit -m "feat(skills): add uacp-skills convention meta-skill (UACP analog of skill-creator)"
```

---

## Task 5: Full-suite regression + lint + branch verification

**Step 1: Run the whole suite**

Run: `python3 -m pytest -q`
Expected: **605 passed / 2 skipped** (baseline 604/2 + the new self-containment module's passing tests; exact count may differ by the parametrization — the requirement is **0 failures** and no pre-existing test regressed).

**Step 2: Lint the new test**

Run: `/Users/mike/.local/bin/ruff check tests/unit/skills/test_skill_self_containment.py`
Expected: clean.

**Step 3: Confirm the branch state**

Run: `git log --oneline origin/main..HEAD` — expect the design-doc commit plus the four Step-1 commits. `git status` clean.

**Step 4: Do NOT merge yet.** Step 1 ends here; a council review precedes merge (see "After this plan").

---

## After this plan

1. **Council review** (project norm for skill-library changes): one architecture/governance lens + one devil's-advocate lens over the diff. Resolve material findings.
2. **Flip ADR-0017** (`docs/architecture/0017-skill-authoring-convention.md`) status `proposed` → `accepted` and update `docs/architecture/INDEX.md`.
3. **Merge** `--no-ff` to `main`, delete the branch.
3. **Step 2 plan** (separate): apply the convention library-wide — `bridge-*` → `uacp-bridge`, DRY the four boilerplate blocks into `skills/references/`, slim lifecycle frontmatter (drop the tool/invariant mirrors), roll out the `kind:` classifier, and extend the self-containment test to the `docs/` reference class.

## Out of scope (Step 2, do not do now)
- Collapsing `bridge-*`.
- Removing the vestigial frontmatter mirrors from lifecycle skills.
- Adding `kind:` to existing skills.
- Tightening `docs/` references in lifecycle SKILL.md bodies.
