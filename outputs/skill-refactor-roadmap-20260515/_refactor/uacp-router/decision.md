# Phase 0 — UACP Router Decision

Status: Draft decision only. No implementation authorized by this artifact.
Start gate: PASS/no concerns after follow-up Agent Council verification.

## Decision

Refactor the umbrella `uacp` skill into a **minimal provisional router**.

The router is not final UACP doctrine. It is a compatibility dispatcher that keeps the skill family usable while each phase skill is repaired one at a time.

## Why

Current `uacp/SKILL.md` is 308 lines / 34,198 bytes and mixes too many roles:

- router
- lifecycle doctrine
- context rehydration stack
- phase policy
- planning package rules
- Kanban/Guardian/Heartgate reminders
- containment design
- Agent Council wiring
- historical/shared-reference index
- LCP sibling notes

This centralizes behavior that should belong to phase skills or canonical UACP docs. The router must stop compensating for thin/broken phase skills.

## Universal UACP boundary

UACP is Universal ACP: generic, unified, and adaptive.

Trustless ACP is pattern evidence only. The router must not import Trustless-specific fixed gates, domains, worktree paths, proposal topology, reviewer lists, or verification sequences.

## Router ownership

The router owns only:

1. UACP skill-family identity.
2. When to use the UACP skill family.
3. Lifecycle phase names and order.
4. Intent-to-phase-skill routing.
5. A minimal bootstrap/self-repair warning.
6. A minimal composition rule: phase skills own execution details.
7. A minimal emergency stop if canonical UACP docs/config/state disagree.


## Phase skill existence baseline

The router may dispatch to the existing phase skill names because all target phase directories exist now:

- `uacp-triage` — `SKILL.md`
- `uacp-propose` — `SKILL.md`
- `uacp-plan` — `SKILL.md`
- `uacp-execute` — `SKILL.md`
- `uacp-verify` — `SKILL.md` plus five local `references/` files
- `uacp-resolve` — `SKILL.md` plus one local `references/` file
- `uacp-state` — `SKILL.md` plus three local `references/` files

This baseline does not certify the phase skills as complete or correct. It only proves the router is not dispatching to missing names. Each phase skill still requires its own refactor loop and councils. File-count detail is informational; implementation audit should verify directory existence and phase names, not depend on counts.

## Router non-ownership

The router must not own:

- TRIAGE/PROPOSE/PLAN/EXECUTE/VERIFY/RESOLVE/STATE execution procedures
- adaptive verification details
- fixed council gates or reviewer domains
- Heartgate/Guardian operational semantics
- Kanban binding details
- containment design procedures
- planning package shape/checklists
- LCP behavior
- historical lesson indexes
- the 38-file shared reference library
- phase skill target file trees

## Chosen variant

Chosen: **Variant B — minimal router with legacy warning**.

Reason:

- Variant A strict router would remove too much discoverability before phase skills are repaired.
- Variant B keeps a short warning that legacy shared references exist but are not router-owned SOPs.
- No shared reference migration happens in Phase 0.

## Shared reference quarantine rule

The existing `references/` directory is legacy/quarantined.

Phase skills may not depend on `../references/` unless that dependency is explicitly justified in that skill's own Decision artifact.

Phase 0 does not classify or migrate all shared references. That happens only when relevant to a specific skill or a later shared-reference cleanup pass.


## Shared reference cleanup trigger

The legacy `references/` quarantine must not persist forever. Cleanup is deferred until after the seven phase skills have each completed their own refactor loop, or earlier only if a phase Decision explicitly needs a shared reference. Owner: the later shared-reference cleanup pass in the existing roadmap. Trigger: completion of `uacp-state` refactor, because state is the last phase skill and can reveal remaining authority primitives. Enforcement: the `uacp-state` closure/handoff must include an explicit next-step item for shared-reference cleanup before the refactor can be called complete. The cleanup pass will classify remaining references as primitive, phase-owned, archive, or delete-candidate. Until then, quarantine prevents new unapproved dependencies.

## Determine artifact status

`determine.md` is raw input only.

Its section classifications are not requirements, not a migration map, and not approval to move content into future files. Implementation must be derived from this Decision's router ownership boundaries. Implementation prompts must not quote or load `determine.md` except to verify that no implementation claim is being inherited from it.

## Target implementation shape

Target `SKILL.md` should be concise. Target: under 120 lines. There is no separate preferred threshold. The implementation audit should enforce the hard maximum and the allowed-section list, not optimize for artificial compression.

Allowed sections:

1. Frontmatter
2. Title / identity
3. When to use
4. Lifecycle phase order
5. Routing table
6. Bootstrap/self-repair warning
7. Legacy reference quarantine warning
8. Emergency stop

No additional files are required for the router at this phase.

## Draft target content outline

```markdown
---
name: uacp
description: Router for Universal Agent Control Plane governance, lifecycle, and state work.
---

# Universal Agent Control Plane — Router

UACP is the generic/adaptive control-plane doctrine for governed agent work. This skill routes requests into the correct UACP lifecycle skill.

## When to use

Use when the request explicitly names UACP, a UACP lifecycle phase/skill, UACP state, or asks to change UACP governance/routing behavior. The router does not define Guardian, Heartgate, or review policy semantics; it only routes to the appropriate owner skill or canonical UACP docs.

## Lifecycle

TRIAGE -> PROPOSE -> PLAN -> EXECUTE -> VERIFY -> RESOLVE

Use `uacp-state` only for governed state mutation and state authority questions.

## Route

- unclear scope / granularity / admission -> `uacp-triage`
- proposal / authority / side effects / viability -> `uacp-propose`
- execution graph / artifacts / verification plan -> `uacp-plan`
- dispatch / Kanban / worker execution -> `uacp-execute`
- adaptive verification / council / evidence -> `uacp-verify`
- closure / lessons / memory / skill updates -> `uacp-resolve`
- governed state mutation -> `uacp-state`

## Composition rule

The router does not contain phase SOPs. Load the phase skill and let that skill own its checklist, adaptive gates, support files, and handoff rules.

## Self-repair warning

When repairing UACP skills, use normal file/git workflow. Do not use broken UACP protected writers or Heartgate as self-approval authority.

## Legacy reference warning

`references/` is legacy/quarantined until phase skills reclaim or retire content. Do not depend on shared references unless the active skill Decision justifies it.

## Emergency stop

If UACP docs, config, or state disagree, stop. Route to `uacp-state` only when the question is specifically about governed state mutation, state authority, or state consistency. If the conflict is doctrinal/configural or the authority owner is unclear, escalate to the operator/canonical UACP docs. If the operator is unavailable, stop rather than inventing authority. The router does not resolve conflicts itself.
```

## Implementation constraints

Implementation may only edit:

- `/home/norty/.hermes/skills/devops/uacp/SKILL.md`

Implementation may not edit:

- phase skill directories
- shared references
- UACP runtime state
- UACP docs/config outside this skill refactor target


## Self-repair fallback

During this refactor, `uacp-verify` is not used as the authority for UACP self-repair. Verification councils are run through Hermes delegation as an external-to-UACP review surface and recorded in these refactor artifacts. Phase 0 implementation audit must not invoke `uacp-verify` as authority. The rebuilt `uacp-verify` skill may later reclaim this role only after its own refactor passes.

## Compatibility and rollback

Implementation must preserve a rollback path: before patching `SKILL.md`, capture the current file content into the Phase 0 refactor artifact area. Do not rely on git tracking for this skill directory unless verified live during implementation.

Compatibility check after implementation:

1. `SKILL.md` exists and parses as a skill file.
2. All seven phase skill names remain discoverable in the router.
3. No phase skill directory is modified.
4. No shared reference is moved or deleted.
5. The router includes a legacy warning so callers know old references exist but are quarantined.

If any check fails, revert only `uacp/SKILL.md` and reopen this Decision rather than editing other skills.

## Verification requirements before implementation

Before patching the actual router skill, end-of-Decision verification must return PASS/no concerns from Agent Council.

Implementation is not authorized if council returns CONCERNS or BLOCK.

## Automation note

Proceed automatically through drafting/review/audit when non-destructive. Stop only for destructive side effects, hard blockers, repeated council concerns after resolution, or ambiguity that changes implementation scope.


## End-of-Decision council patch

A Devil's Advocate reviewer returned CONCERNS on the first end-of-Decision check. This artifact was patched to resolve them:

1. Tightened `When to use` so the router does not appear to define Guardian/Heartgate/review semantics.
2. Clarified emergency stop routing: the router stops and routes/escalates; it does not resolve canonical conflicts itself.
3. Added a shared-reference cleanup trigger so quarantine does not become permanent.
4. Relaxed the preferred line target to under 100 while preserving a hard maximum under 120.

A follow-up end-of-Decision council must return PASS/no concerns before implementation.


## Second end-of-Decision council patch

A follow-up Devil's Advocate reviewer returned CONCERNS. This artifact was patched to resolve them:

1. Added concrete shared-reference cleanup owner/trigger: after all seven phase skill refactors, triggered by completion of `uacp-state`, unless a phase Decision justifies earlier local handling.
2. Clarified `uacp-state` routing: only state mutation/authority/consistency questions go there; doctrinal/config conflicts escalate to operator/canonical docs.
3. Added self-repair fallback: current verification councils are Hermes delegation review surfaces, not broken `uacp-verify` authority.
4. Added phase skill existence baseline proving router targets exist without certifying them as correct.
5. Added rollback and compatibility checks for safe one-file implementation.
6. Simplified line target to one hard maximum under 120 lines.
7. Added preventive instruction that implementation must not load/quote `determine.md` as authority.

A further follow-up end-of-Decision council must return PASS/no concerns before implementation.


## Third end-of-Decision council patch

A further Devil's Advocate reviewer returned CONCERNS. This artifact was patched to resolve them:

1. Replaced ambiguous phase-skill file counts with explicit file-list descriptions and stated counts are informational only.
2. Added cleanup enforcement: `uacp-state` closure/handoff must explicitly trigger shared-reference cleanup before the full refactor can be called complete.
3. Clarified that if operator/canonical authority is unavailable during an emergency stop, the router stops rather than inventing authority.
4. Clarified that Phase 0 implementation audit must not invoke `uacp-verify` as authority; Hermes delegation councils remain the temporary external review surface.
5. Replaced git-dependent rollback language with mandatory exact-content capture before patching `SKILL.md`.
6. Prior council outputs are recorded in this same Decision artifact as patch ledgers; the next follow-up council must independently verify this current artifact rather than trusting the drafter's self-report.

A final follow-up end-of-Decision council must return PASS/no concerns before implementation.


## Final end-of-Decision council verification — PASS

Two independent follow-up reviewers returned PASS/no concerns after the third patch.

Result:

```text
Decision gate passed.
Implementation may proceed as a single-file provisional router patch to /home/norty/.hermes/skills/devops/uacp/SKILL.md only.
Backup and compatibility checks are mandatory.
```


## Implementation and deterministic audit result

Implementation completed as the authorized one-file patch:

- patched: `/home/norty/.hermes/skills/devops/uacp/SKILL.md`
- backup: `_refactor/uacp-router/backup-SKILL-before-router-implementation.md`
- old router: 308 lines / 34,198 bytes
- new router: 64 lines / 2,672 bytes

Deterministic compatibility audit: **PASS**

Checks passed:

- `SKILL.md` exists
- line count is under 120
- all seven phase skill names remain discoverable
- all seven phase skill directories exist
- all seven phase skill `SKILL.md` files exist
- old bloated router sections are absent from the new router
- backup exists and preserves the old 308-line router
- no phase skill directories were intentionally modified
- no shared references were moved or deleted

End-of-implementation Agent Council verification is still required before Phase 0 can close.


## End-of-implementation council discrepancy resolution

First end-of-implementation council returned one BLOCK based on a path error: it searched for phase skill directories as siblings of `/home/norty/.hermes/skills/devops/uacp` instead of children inside that directory.

Correct phase skill root:

```text
/home/norty/.hermes/skills/devops/uacp/
```

Verified child phase skill directories:

```text
/home/norty/.hermes/skills/devops/uacp/uacp-triage/SKILL.md
/home/norty/.hermes/skills/devops/uacp/uacp-propose/SKILL.md
/home/norty/.hermes/skills/devops/uacp/uacp-plan/SKILL.md
/home/norty/.hermes/skills/devops/uacp/uacp-execute/SKILL.md
/home/norty/.hermes/skills/devops/uacp/uacp-verify/SKILL.md
/home/norty/.hermes/skills/devops/uacp/uacp-resolve/SKILL.md
/home/norty/.hermes/skills/devops/uacp/uacp-state/SKILL.md
```

Two other council reviewers returned PASS. Because one reviewer returned BLOCK, a focused follow-up verification is required. The follow-up must verify the correct child-directory path and return PASS/no concerns before Phase 0 can close.


## Final end-of-implementation verification — PASS

Focused follow-up council verified the previous BLOCK was caused by checking the wrong directory level.

Correct phase skill root:

```text
/home/norty/.hermes/skills/devops/uacp/
```

Result: **PASS / no concerns**

Additional local verification:

- backup exists at `_refactor/uacp-router/backup-SKILL-before-router-implementation.md`
- backup preserves old router: 308 lines / 34,198 bytes
- current router: 64 lines / 2,672 bytes

Phase 0 router implementation is closed as PASS. Next phase should begin with Agent Council brainstorming before touching the next skill.
