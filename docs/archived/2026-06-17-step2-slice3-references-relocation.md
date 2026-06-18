# Step 2 · Slice 3 — References relocation (abolish `skills/references/`)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Empty and remove the top-level `skills/references/` shared dump (52 files), relocating each to its correct home, with zero information loss and every citer repointed. After this slice the dump no longer exists.

**Routing rule (operator-decided):** a doc **cited by ANY skill (incl. the `uacp` router) → `uacp-core/references/`** (or, if cited by exactly one lifecycle skill, that skill's own `references/`); a doc **cited by NO skill → `docs/knowledge/`** (history/lessons, human/agent reading + provenance, NOT skill-citable). This keeps every skill self-contained automatically. It overrides the eval map where the eval tentatively sent router-cited docs to `docs/knowledge/`.

**Architecture:** Pure relocation + merge/distill + repoint. No behavioral change. Merges and distills must preserve the load-bearing content (specs below). Branch `skills/step2-slice3-references-relocation`. Baseline suite 676/2.

**Spec source:** `docs/plans/2026-06-16-step2-eval-maps.md` §B (reference map: per-doc destinations, the 7 merge-groups, delete candidates). This plan embeds the resolved destinations under the operator rule + the merge preserve-specs.

## Hard rules
- **No information loss.** Moves are verbatim; merges/distills keep the listed content; only delete byte-identical dupes / empty placeholders / superseded docs (with preconditions met).
- `docs/knowledge/` is NOT skill-citable. No skill may cite a `docs/knowledge/` path. (That's why cited docs go to `uacp-core/references/`.)
- Drop `-YYYYMMDD` date suffixes when moving to `uacp-core/references/` (session markers, not expiries). KEEP dates on `docs/knowledge/` filenames (provenance).
- Repoint every citer (the `uacp` router cites 14 via `../references/`; uacp-verify/execute/propose/state/resolve/triage also cite the dump). After repointing, `skills/references/` must be empty and removed.

---

## The 52-file destination table

### DELETE (8) — Task 7
| File | Why |
|---|---|
| codebase-verification-review-pattern.md | byte-identical dupe of `uacp-verify/references/` copy (confirmed) |
| phase-end-council-hardening.md | byte-identical dupe (uacp-verify) |
| read-only-containment-validation.md | byte-identical dupe (uacp-verify) |
| retrieval-led-phase-verify.md | byte-identical dupe (uacp-verify) |
| delegate-task-model-selection.md | 3-line empty placeholder, zero knowledge |
| governian-neutral-kernel-adapter.md | 3-line empty placeholder (typo-name twin of guardian-…) |
| lifecycle-skill-contract.md | superseded by `docs/lifecycle/lifecycle-reference.md` §Lifecycle Skill Contracts — **PRECONDITION:** confirm `phase_local_granularity` + `human_involvement` YAML templates are reachable from uacp-plan/uacp-execute SKILL.md; if absent, surface them there first, else don't delete |
| codex-handoff-for-uacp.md | superseded by `uacp-bridge/references/codex.md` — **PRECONDITION:** confirm codex.md covers the staged-scope+non-goals+verification handoff requirement + the vague-handoff pitfall; if not, fold those 2-3 sentences into codex.md first |

### MOVE → owning skill's `references/` (single-skill-cited) — Task 2
| File | Destination |
|---|---|
| adversarial-runtime-review.md | `skills/uacp-verify/references/adversarial-runtime-review.md` |
| proposal-council-concerns-pattern-20260515.md | `skills/uacp-propose/references/proposal-council-concerns-pattern.md` (drop date) |
| current-semi-auto-orchestration.md | `skills/uacp-execute/references/current-semi-auto-orchestration.md` (cited by uacp-execute; move verbatim — Hermes-vocab cleanup deferred) |
| state-mutation-protocol.md | **RECONCILE** into existing `skills/uacp-state/references/state-mutation-protocol.md` (the dump copy DIFFERS — merge any unique content, esp. the Artifact-routing table, into the landed copy, then delete the dump copy; report the diff) |

### MOVE → `uacp-core/references/` (cited; no merge) — Task 3
agent-council-followthrough.md · operator-phase-return-presentation.md · external-audit-runtime-gate-remediation.md · adaptive-package-backfill-pattern.md · adaptive-package-gate-commit-pattern-20260519.md → drop date · kimi-codex-agent-council-audit-loop-20260520.md → drop date · architecture-packet-uacp-compatibility.md · lexa-first-principles-review-sliced-continuation.md
(all router/multi-skill-cited → shippable shared home; verbatim move + date-drop only)

### MERGE → `uacp-core/references/` (cited sources) — Tasks 4-5
- **lifecycle-semantic-gates.md** ← `lifecycle-semantic-gates-20260519.md` (base) + `lifecycle-semantic-gates.md` + `lifecycle-hardening-pattern.md`. PRESERVE: (base) PIV=Phase Intent Verification correction; gate-expectations-by-phase (all artifact names); the fixture-discipline section verbatim; external-audit retry/fallback lesson; the 8-step preferred workflow. (from base lifecycle-semantic-gates) VERIFY pitfall enumeration; RESOLVE pitfall; REPORTING DISCIPLINE section; phase-by-phase responsibility list. (from lifecycle-hardening) the multi-surface patch design principle + granularity principle + next-phase-boundary pitfall, as a "Hardening design principles" section. Reconcile the two 8-step sequences into one.
- **full-lineage-audit-and-remediation-lessons.md** ← `full-lineage-audit-and-docs-package-20260520.md` + `full-lineage-external-audit-remediation-loop-20260520.md`. PRESERVE: full-lifecycle audit prompt shape (10 surfaces); 7 council roles; systemic remediation classes verbatim; 8-surface remediation ordering; anti-fracture 5-file modular guide-package shape; canonical ownership pointers; verification-bundle bash; full-lineage scope rule; offline-validator/Heartgate parity. DROP the dead git-identity (norty-dev) section.
- **semantic-package-and-operator-return-lessons.md** ← `operator-phase-return-and-semantic-packages-20260519.md` + `semantic-package-council-patch-loop-20260519.md`. PRESERVE: three-surface model (machine envelope / semantic package / operator summary); the semantic-recovery test verbatim ("If Mike or a future agent returns one month later…"); fix-the-system-not-the-instance rule; Markdown-not-optional for STANDARD/FULL; the 4 council roles + 5-step sequence; validator recoverability-enforcement checklist; acceptable-residuals caveat.

### MERGE → `docs/knowledge/` (orphan sources) — Tasks 4-5
- **agent-council-integration-and-operationalization-lessons.md** ← `agent-council-integration-lessons.md` + `phase6-agent-council-operationalization-lessons-20260515.md`. PRESERVE: split-plan package shape (7-file list); cognitive-plane anti-patterns; granularity field names; execution-surface taxonomy; propagation+cleanup checklists; PYTHONDONTWRITEBYTECODE/ast.parse trick; surface-inventory classification; PLAN→EXECUTE checklist. Cross-ref orchestration-model.md (don't duplicate plane prose).
- **filesystem-containment-phase-lessons.md** ← `contained-shell-execution-seam-20260514.md` (anchor, preserve in full) + `containment-design-direction-20260514.md` + `phase4-filesystem-containment-start-pattern-20260513.md`. PRESERVE: the sandbox-check-vs-contained-shell distinction; bwrap ro-bind; write-probe-before-command; attestation lifecycle; boundary-correction principle verbatim; risk-table mitigations; the 10-step sequencing; Heartgate YAML shape; 7 pre-EXECUTE council constraints. DROP stale current-state narrative.
- **hermes-adapter-porting-and-cleanup-lessons.md** ← `runtime-porting-version-control.md` + `runtime-porting-execution-runbook.md` + `runtime-porting-live-binding-cleanup.md`. PRESERVE: symlink-probe invocation; planning checklist; dirty-state precheck+tarball; branch-verification checklist; deferred-action boundary list; stale-gate-task resolution principle; governed-writer surface-gap note. DROP completed Hermes-specific task lists.
- **kanban-guard-and-closure-lessons.md** ← `phase4b-resolve-lessons-20260514.md` + `phase5-kanban-completion-guard-20260514.md` + `phase5-kanban-guard-start-pattern-20260514.md`. PRESERVE: 7-step closure-evidence pattern; workspace-separation boundary; completion-metadata field list + validation logic; non-goals list; 5-case verification shape; low-confidence-delegate pitfall. DROP Hermes-internal file paths.

### DISTILL → `docs/knowledge/` (orphan singles, KEEP date in filename) — Task 6
adaptive-gate-selection.md · branch-porting-ground-truthing.md · guardian-branch-review-pattern-20260514.md · guardian-hook-audit-pattern.md · guardian-neutral-kernel-adapter.md · governed-canonical-writers.md · heartgate-council-artifact-management.md · lcp-integration.md (3-line CC print-mode extract only; drop stale LCP/model table) · operational-dashboard-and-live-proof.md · phase-transition-finalization-and-validation.md · round3-runtime-construction-lessons.md · runtime-trust-boundary-correction-20260514.md · skills-validator-alignment.md · trustless-acp-source-analysis.md (also add the missing kimi row to its bridge table; keep the 14-pattern "What's Universal" table; drop dead OpenClaw inventory)
(Per-doc distill specs in eval-maps §B / the eval output. Distill = keep the durable lesson/pattern, drop stale current-state/dead-environment narrative. When unsure, preserve more rather than less.)

---

## Tasks

### Task 1 — Create `docs/knowledge/` + register
- `mkdir -p docs/knowledge`. Create `docs/knowledge/README.md` (an index: "Durable run-lessons and history relocated from the former `skills/references/` dump. Not skill-citable (skills must cite only shipped files); these are for human/agent reading + provenance.") — it will list the knowledge docs as they're created (update at the end, Task 8).
- Register the directory in `docs/INDEX.md` (one row for the `knowledge/` dir, per the operator decision "create + index the dir only" — NOT one row per file). Match INDEX.md's existing format.
- Commit: `feat(docs): add docs/knowledge/ relocation sink + register in INDEX`.

### Task 2 — Single-skill moves + state reconcile
Move adversarial-runtime-review → uacp-verify/references/; proposal-council-concerns (drop date) → uacp-propose/references/; current-semi-auto-orchestration → uacp-execute/references/ (verbatim `git mv`). Reconcile state-mutation-protocol into uacp-state's existing copy (diff, fold unique content, delete dump copy). Repoint the citing skills' pointers to the new in-skill paths (e.g. uacp-propose's `../references/proposal-council-concerns-pattern-20260515.md` → `references/proposal-council-concerns-pattern.md`). Suite green. Commit.

### Task 3 — Move (no-merge) shared docs → uacp-core/references/
`git mv` the 8 listed files into `skills/uacp-core/references/` (drop dates where noted). Verbatim. Do NOT repoint citers yet (Task 8 does all repointing together) — but note each moved path. Suite green. Commit.

### Task 4 — Merges into uacp-core/references/ (3 docs)
Build lifecycle-semantic-gates.md, full-lineage-audit-and-remediation-lessons.md, semantic-package-and-operator-return-lessons.md per the PRESERVE specs above (read all source files, merge, honor preserve-lists, reconcile duplicate sequences). `git rm` the source files. Suite green. Commit each (or batch).

### Task 5 — Merges into docs/knowledge/ (4 docs)
Build agent-council-integration-and-operationalization-lessons.md, filesystem-containment-phase-lessons.md, hermes-adapter-porting-and-cleanup-lessons.md, kanban-guard-and-closure-lessons.md per PRESERVE specs. `git rm` sources. Suite green. Commit.

### Task 6 — Distill orphan singles → docs/knowledge/
Distill the 14 listed singles (keep durable lesson, drop stale/dead narrative; lcp-integration → 3-line extract; trustless-acp → add kimi row + keep universal-pattern table). `git mv`/rewrite, `git rm` originals. Suite green. Commit (batchable in 2-3 commits).

### Task 7 — Deletes (with preconditions)
The 4 byte-identical verify dupes + the 2 placeholders → `git rm`. For lifecycle-skill-contract + codex-handoff: CHECK the preconditions first (templates reachable / codex.md covers handoff); satisfy them if needed, then `git rm`; if a precondition can't be cleanly met, KEEP the file (move to docs/knowledge instead) and report. Commit.

### Task 8 — Repoint all citers + abolish the dump
- Repoint the `uacp` router's 14 `../references/X.md` pointers: cited→uacp-core become `../uacp-core/references/X.md` (or the merged-doc name, e.g. lifecycle-hardening-pattern + lifecycle-semantic-gates* all → `../uacp-core/references/lifecycle-semantic-gates.md`; the full-lineage pair → `../uacp-core/references/full-lineage-audit-and-remediation-lessons.md`; operator-phase-return-and-semantic-packages + semantic-package-council-patch-loop → `../uacp-core/references/semantic-package-and-operator-return-lessons.md`). Resolve the 2 dead-lexa TODOs (they reference non-existent docs — remove or point at a real doc; report).
- Repoint uacp-verify/execute/propose/state/resolve/triage `../references/` pointers to their new homes (in-skill `references/` or `uacp-core/references/`).
- `grep -rn "\.\./references/\|skills/references/" skills/ --include=*.md` → ZERO (no skill cites the abolished dump). Every repointed `../uacp-core/references/X.md` or in-skill `references/X.md` must resolve to an existing file.
- Confirm `skills/references/` is empty; `git rm -r` any remainder / remove the dir.
- Finish `docs/knowledge/README.md` index. Commit.

### Task 9 — Widen the self-containment lint + full verification
- Extend `tests/unit/skills/test_skill_self_containment.py` (or the readiness lint) with a guard: no `SKILL.md` (or instructing reference) cites the abolished `skills/references/` path. (Keep the ADR-class check; the broad docs/ class is still Slice 4.)
- `python3 -m pytest -q` → 0 failures. `ruff` clean. `claude plugin validate .` passes.
- Structural: `test ! -d skills/references` (or empty); every `uacp-core/references/` + in-skill reference cited resolves; `docs/knowledge/` populated + indexed.
- Do NOT merge — council gate.

---

## After this plan
1. **Council** (2-lens): completeness (all 52 accounted for, nothing lost in merges/distills, every citer resolves) + devil's-advocate (content lost in distillation? a docs/knowledge doc still cited by a skill? a merged doc missing a preserve-item?).
2. **Merge** `--no-ff` to main, delete branch.
3. Next: **Slice 4 — frontmatter slim + `kind` rollout** (drop vestigial tool mirrors, roll `kind:` to all, sweep remaining `context:` offenders [domain-registry, uacp-council-taxonomy], widen self-containment test to the full `docs/` class).

## Out of scope
- Frontmatter slim + kind rollout (Slice 4); the broad `docs/` citation-class lint widening (Slice 4).
- Any content rewrite beyond merge/distill; behavioral changes.
