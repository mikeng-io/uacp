# Phase 0 — UACP Router Explore

Status: Explore only. No determination, decision, audit, or implementation is made in this artifact.

## Scope

Active target:

```text
/home/norty/.hermes/skills/devops/uacp/SKILL.md
```

Narrow inspection scope:

```text
/home/norty/.hermes/skills/devops/uacp/SKILL.md
/home/norty/.hermes/skills/devops/uacp/references/
/home/norty/.hermes/skills/devops/uacp/uacp-*/
```

This phase does not patch files.

## Recalled constraints used for this explore

- Current UACP artifacts are considered unreliable for this refactor and must be ground-truthed.
- Do not use UACP protected lifecycle/write path to govern UACP self-repair.
- Refactor one skill at a time.
- Required loop per skill: Explore → Determine → Decision → Review → Audit → Implement.
- Do not centralize into a single mega-SOP.
- Do not inflate SKILL.md into a giant all-purpose document.
- Serious skills should be ACP/Anthropic-style modular directories: concise `SKILL.md` conductor plus local references/scripts/schemas/templates as needed.

## Ground-truth snapshot

Working directory inspected:

```text
/home/norty/.hermes/skills/devops/uacp
```

Top level currently contains:

```text
SKILL.md
references/
scripts/
uacp-execute/
uacp-plan/
uacp-propose/
uacp-resolve/
uacp-state/
uacp-triage/
uacp-verify/
```

Umbrella `SKILL.md` measurement:

```text
lines: 306
bytes: 33642
```

This is too large for a router and is currently functioning as a doctrine bundle plus reference registry plus operational reminders.

## Current umbrella SKILL.md sections

Observed headings:

```text
# Universal Agent Control Plane
## Drift guard
## Lifecycle
## Mike-specific UACP doctrine preferences
## Context rehydration before UACP execution
## Skill family
## Read first
## Core rules
## Checkpoints
## Planning package shape
## Planning artifact coverage check
## Phase-specific coordination rule
## Coordination adapter boundary
## Kanban binding
## Prototype/doc-drift sync
## Use this registry when
## LCP (Liaison Control Plane) — UACP-governed sibling
## Containment and runtime trust boundary
## Containment design direction
## Kanban completion guard boundary
## Emergency stop
## Agent Council follow-through wiring
## Skill composition rule from Trustless ACP
```

## Initial observations, not decisions

The umbrella file currently mixes at least five roles:

1. Router for lifecycle skill family.
2. Doctrine summary for UACP.
3. Historical/session reference index.
4. Runtime enforcement reminder list.
5. Detailed operational policy for Kanban, Guardian, Heartgate, containment, planning packages, and Agent Council follow-through.

This violates the intended router role. A router should select the relevant phase skill and point to small shared primitives only.

## Current phase skill file counts

```text
uacp-execute: 1 files
uacp-plan: 1 files
uacp-propose: 1 files
uacp-resolve: 2 files
uacp-state: 4 files
uacp-triage: 1 files
uacp-verify: 6 files
```

Observation: most phase skills are still thin or minimally modular. Router bloat is partly compensating for missing phase-local modules.

## Current shared references snapshot

Shared `references/` contains 38 files:

```text
adaptive-gate-selection.md
adversarial-runtime-review.md
agent-council-followthrough.md
agent-council-integration-lessons.md
branch-porting-ground-truthing.md
codebase-verification-review-pattern.md
codex-handoff-for-uacp.md
contained-shell-execution-seam-20260514.md
containment-design-direction-20260514.md
current-semi-auto-orchestration.md
delegate-task-model-selection.md
governed-canonical-writers.md
governian-neutral-kernel-adapter.md
guardian-branch-review-pattern-20260514.md
guardian-hook-audit-pattern.md
guardian-neutral-kernel-adapter.md
heartgate-council-artifact-management.md
lcp-integration.md
lifecycle-skill-contract.md
operational-dashboard-and-live-proof.md
phase-end-council-hardening.md
phase-transition-finalization-and-validation.md
phase4-filesystem-containment-start-pattern-20260513.md
phase4b-resolve-lessons-20260514.md
phase5-kanban-completion-guard-20260514.md
phase5-kanban-guard-start-pattern-20260514.md
phase6-agent-council-operationalization-lessons-20260515.md
proposal-council-concerns-pattern-20260515.md
read-only-containment-validation.md
retrieval-led-phase-verify.md
round3-runtime-construction-lessons.md
runtime-porting-execution-runbook.md
runtime-porting-live-binding-cleanup.md
runtime-porting-version-control.md
runtime-trust-boundary-correction-20260514.md
skills-validator-alignment.md
state-mutation-protocol.md
trustless-acp-source-analysis.md
```

Observation: the shared reference directory is currently a flat mixed collection of primitives, phase-specific methods, historical lessons, runtime implementation notes, and source analyses. This supports Mike's criticism that the system saves too much into centralized piles.

## Router-specific facts discovered

- The current umbrella `SKILL.md` contains useful routing information under `Skill family`.
- The current umbrella `SKILL.md` also contains many operational rules that likely belong in phase-local modules, shared primitives, or archive.
- The current `Read first` section is extremely broad and forces excessive context rehydration. It is not appropriate for a lightweight router.
- The file already contains the correct "Skill composition rule from Trustless ACP", but it violates that rule by being a large central policy bundle.
- The phase directories exist, so router can become a loader/router without creating new phase dirs.

## Open questions for Determine phase

The Determine phase must classify umbrella content into:

- keep in router
- move to phase-local skill later
- move to shared primitive later
- archive later
- delete candidate later

Specific questions for Determine:

1. What is the minimum router content needed for correct skill selection?
2. Which current sections are safe to remove from router now versus defer until phase modules exist?
3. Which shared primitives should the router point to, if any, before shared cleanup happens?
4. How should the router warn against UACP self-governance without embedding the whole rationale?
5. What exact line/size target should the router obey?
6. Should the router keep a temporary legacy pointer to current broad references until phase modules are rebuilt?

## Non-actions in this Explore phase

- Did not patch `SKILL.md`.
- Did not move references.
- Did not edit phase skills.
- Did not run UACP lifecycle/Heartgate.
- Did not create implementation branch or commit.
- Did not decide final router content.
