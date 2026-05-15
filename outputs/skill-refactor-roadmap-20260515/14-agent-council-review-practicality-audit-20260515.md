# Agent Council Review — Implementation Practicality & Auditability

**Reviewer:** subagent (practicality/auditability lens)
**Scope:** UACP skill refactor roadmap artifact set under outputs/skill-refactor-roadmap-20260515/
**Date:** 2026-05-15
**Verdict:** CONCERNS

---

## 1. What was reviewed

All 14 roadmap artifacts plus ground-truth inspection of the current skill tree.

Current state snapshot:
- uacp (router): 1 file + 38 shared refs, SKILL.md 306 lines
- uacp-triage: 1 file, SKILL.md 158 lines
- uacp-propose: 1 file, SKILL.md 116 lines
- uacp-plan: 1 file, SKILL.md 109 lines
- uacp-execute: 1 file, SKILL.md 128 lines
- uacp-verify: 6 files, SKILL.md 105 lines, 5 local refs
- uacp-resolve: 2 files, SKILL.md 104 lines, 1 local ref
- uacp-state: 4 files, SKILL.md 107 lines, 3 local refs

---

## 2. Strengths

1. Bootstrap discipline is explicit — broken UACP must not self-govern repair.
2. One-skill-at-a-time sequencing respects data dependencies.
3. Phase contract template (05) is strong and repeatable.
4. Correction in 13 is the most important file — prevents premature design.
5. Measurement framework asks the right questions.

---

## 3. Missing Audit Checks

### 3.1 No concrete thresholds for smallest sufficient
- Required gate: declare SKILL.md line target (suggest <=120 router, <=140 phase skills); every support file needs one-sentence justification tied to a failure mode in 02; >2 support files requires rationale.

### 3.2 No ground-truth baseline before first edit
- Required gate: commit refactor-baseline-20260515.md with exact counts and find listing of shared references.

### 3.3 No stop-and-review trigger between skills
- Required gate: transition checklist — Decision reviewed, Audit ticked, Implement committed, sanity check done.

### 3.4 Router Explore/Determine drift toward implementation
- Required gate: explicit Decision artifact (Variant B: strict router + legacy pointer) before any SKILL.md edit.

### 3.5 Shared reference cleanup is undifferentiated
- Required gate: four-bin classification (Primitive / Phase-owned / Archive / Delete) with a rule per file before any moves.

---

## 4. Overengineering Risks

| Risk | Suggested guard |
|---|---|
| Schemas for every phase | Justify with concrete validation failure it prevents |
| Scripts for every phase | Justify with deterministic check agents cannot do |
| Templates for every phase | Name artifact shape and why prose is insufficient |
| Council for every skill | Optional if reviewable by one agent in <10 min |
| Retrospective perfectionism | Only add constraints that block a known failure from 02 |

Overall risk: MODERATE.

---

## 5. Practical Sequencing Fixes

1. Router chooses Variant B now so it does not block on later skills.
2. Shared-reference pre-classification (read-only four-bin list) happens immediately after router, not at phase 8.
3. Use uacp-verify as first modularization pilot — it already has local references.
4. Add correction checkpoint after every two skills: file delta, line target check, cross-skill edit check, remaining correction.

---

## 6. Suggested Measurable Gates (per skill)

| Gate | Check |
|---|---|
| G1 | Frontmatter present |
| G2 | Line count <= target |
| G3 | Every support file justified in Decision |
| G4 | No cross-skill edits in git diff |
| G5 | Validation method stated (no broken UACP runtime dependency) |
| G6 | SKILL.md loads only local support files by default |
| G7 | Fresh-agent can answer 7 questions from 07 without opening other files |
| G8 | Baseline delta recorded |

---

## 7. Final Verdict

CONCERNS. Roadmap is directionally correct and well-motivated, but not yet ready for implementation because:
1. Missing concrete audit gates (thresholds, baselines, inter-skill stops).
2. Router phase lacks a formal Decision artifact before patching.
3. Shared reference cleanup is under-specified (38 files, no classification rules).
4. Overengineering risk is moderate — per-skill justification gates missing.

Recommended next actions:
1. Capture baseline snapshot and commit it.
2. Produce router Decision artifact (Variant B) and review.
3. Add G1-G8 to 05-phase-contract-template.md.
4. Run lightweight shared-reference pre-classification before skill 1.
5. Use uacp-verify as first modularization pilot.
