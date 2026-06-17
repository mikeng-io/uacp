---
type: pattern
title: Semantic Package and Operator Return Lessons
description: Lessons for work touching adaptive packages, Markdown semantic substrate, validator gates, and operator-channel returns
tags: [semantic, packages, operator, lessons]
timestamp: 2026-06-17
---

# Semantic Package and Operator Return Lessons

Reference for UACP work touching adaptive PROPOSE/PLAN packages, Markdown semantic substrate, validator gates, operator-channel returns, or council verification loops.

---

## Three-surface model

Separate three surfaces — do not conflate them:

- **Machine lifecycle envelope:** YAML files that carry structured lifecycle state and validator/Heartgate fields. These are for machines.
- **Semantic package substrate:** Markdown package directories that explain why the work exists, how it works, intention, rationale, decision, authority, scope, containment, risks, verification, rollback, and transition readiness. These are for humans and future agents. A YAML envelope is not enough for standard/full governance work when adaptive package selection applies.
- **Operator phase return:** short Telegram/Discord summary that gives conclusion, meaning, decision/status, invariants, material risks, next action, and evidence pointer. A Markdown package is not an excuse to spam the operator channel — operator chat receives the summary layer only.

Raw evidence stays in artifacts, logs, and commits.

---

## Semantic recovery test

For every selected PROPOSE/PLAN package, ask:

> If Mike or a future agent returns one month later with no chat history, can they recover why we did this, how it works, the rational intent, and the decision boundary from the package Markdown?

If not, the package is incomplete — even if YAML validates.

---

## Fix the system, not the instance

When a council or operator flags missing package semantics, fix the governing skills, validators, and schema behavior first. Proposal-level backfills may repair an individual run, but they do not prevent recurrence.

Markdown semantic packages are not optional presentation artifacts. If a task treats them as optional and creates only YAML envelopes, that is insufficient for future semantic recovery.

---

## Markdown-not-optional for STANDARD/FULL governance work

When adaptive package selection applies, the validator must enforce recoverability — not merely check that referenced files exist:

- Require canonical package directories:
  - `proposals/{run_id}/` for proposal packages.
  - `plans/{run_id}/` for plan packages.
- Require `00-index.md` inside each package directory.
- Require universal-core artifacts to point to readable Markdown inside that package directory.
- Require selected-module artifacts to point to readable Markdown inside that package directory.
- Treat empty `selected_modules` as BLOCK for package-selection artifacts, not WARN.
- Block non-Markdown, unreadable, placeholder-thin, heading-less, or semantically deficient artifacts.

---

## Council loop: four named roles and 5-step sequence

### Council roles

1. **Governance reviewer** — verifies intent, authority, and scope alignment with UACP policy.
2. **Validator/schema auditor** — checks machine-enforceability and schema compatibility.
3. **Devil's advocate / adversarial reviewer** — finds failure modes, false passes, and edge cases.
4. **Synthesis/debate lead** — reconciles findings, classifies severity, and drafts the council conclusion.

### 5-step sequence

1. Dispatch a role-diverse council after the first implementation, not only after final polish.
2. Classify findings as BLOCK / CONCERNS / PASS with explicit severity.
3. Patch systemic HIGH/MEDIUM issues before reporting success.
4. Rerun a focused council over the patch delta until PASS or acceptable residual risk is explicit.
5. Record a compact synthesis artifact under `verification/` so future agents can recover the debate outcome without reading raw transcripts.

---

## Validator recoverability enforcement checklist

The validator should enforce recoverability, not merely check file existence:

- [ ] Canonical package directory present (`proposals/{run_id}/` or `plans/{run_id}/`).
- [ ] `00-index.md` present and non-empty inside the directory.
- [ ] Universal-core artifacts point to readable Markdown inside the directory.
- [ ] Selected-module artifacts point to readable Markdown inside the directory.
- [ ] `selected_modules` non-empty (BLOCK, not WARN, if empty).
- [ ] Artifacts are not non-Markdown, unreadable, placeholder-thin, heading-less, or semantically deficient.

---

## Operator return: presentation rules

Default phase returns must suppress:

- Full edited-file/new-file lists.
- Raw diff stats.
- Raw validator logs.
- Raw council transcripts.
- Full artifact inventories.

Include paths only when needed for a blocker, rollback, explicit decision, or requested audit detail.

Report the outcome as an information summary, not a raw inventory:

- Conclusion first: initial result → patch → focused rerun result.
- Meaning-level changes.
- Why it matters.
- Remaining residuals.
- Compact evidence pointer: commit(s), validator command(s), synthesis artifact.

---

## Acceptable residuals caveat

Shallow keyword/term matching and arbitrary minimum length thresholds are acceptable as minimum recoverability checks, but they are not semantic-quality proof. If future work depends on deeper assurance, add package-level coherence checks rather than treating character counts as proof of understanding.
