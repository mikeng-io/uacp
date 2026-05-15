# Cortex x-draft revamp plan package

Run: `cortex-x-draft-revamp-20260514`  
Phase: `PLAN`  
Status: draft plan package initialized

## Purpose

Revamp Cortex `x-draft` / original-new tweet generation from a narrow `zh-hk` single-item reaction lane into a **diverse but coherent public thought stream**.

The revamp must support simple and deep content:

- Purpose Agent / Norty observations
- useful article shares
- useful repository shares
- scoped tool evaluations
- build notes
- governance notes
- simple reactions
- technical explainers
- Trustless / UACP / Cortex notes

It must also support context-selected language/register:

- Cantonese-English hybrid
- Traditional Chinese-English hybrid
- English-led hybrid
- Cantonese-led
- plain English

## UACP source artifacts

- Triage: `state/runs/cortex-x-draft-revamp-20260514-triage.yaml`
- Proposal: `proposals/cortex-x-draft-revamp-20260514.yaml`
- Gate selection: `proposals/cortex-x-draft-revamp-20260514-gate-selection.yaml`
- Proposal council: `verification/cortex-x-draft-revamp-propose-council-synthesis-20260514.yaml`

## Planning documents

Read in order:

1. `plans/cortex-x-draft-revamp/00-index.md` — this index
2. `plans/cortex-x-draft-revamp/01-ground-truth.md` — current workflow and inspected surfaces
3. `plans/cortex-x-draft-revamp/02-decisions.md` — accepted design decisions and deferred questions
4. `plans/cortex-x-draft-revamp/03-requirements.md` — functional, safety, language, and coherence requirements
5. `plans/cortex-x-draft-revamp/04-design.md` — target architecture and data contracts
6. `plans/cortex-x-draft-revamp/05-execution-plan.md` — bounded work packages, boundaries, rollback
7. `plans/cortex-x-draft-revamp/06-verification.md` — acceptance evidence and dry-run/test strategy

## Current phase decision

Proceeding from PROPOSE to PLAN is justified because:

- Authority is explicit from Mike.
- Current side effects are limited to UACP artifacts.
- The proposal council found concerns but no stop-level blocker against planning.
- Implementation is explicitly blocked until PLAN defines worktree, allowed files, verification, and rollback.

## Non-actions so far

No Cortex code, DB, Temporal schedule, Discord live behavior, or public posting behavior has been changed by the main orchestrator.

A delegate unexpectedly created `CORTEX_ROOT/docs/design/editorial-mass-restructure/x-draft-verification-review.md`. It is untracked and not canonical until explicitly adopted, moved, or removed.
