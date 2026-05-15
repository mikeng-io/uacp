# Phase 0 — UACP Router Determine

Status: Determine only. This artifact classifies current router content and possible destinations. It does not decide the final patch and does not implement anything.

## Inputs

- `explore.md` from this router phase.
- Ground-truth section inventory from `/home/norty/.hermes/skills/devops/uacp/SKILL.md`.
- Recalled Mike constraints: modular ACP-style skill packages, no mega-SOP, one-skill-at-a-time loop, current UACP docs not trusted as complete reflection of the last week.

## Determine objective

Classify current umbrella router content into candidate destinations:

- keep in router
- move to phase-local skill later
- move to shared primitive later
- archive later
- delete candidate later
- defer classification until the relevant skill phase

This is not a final decision. The Decision phase will select the exact router patch.

## Router role candidate

Candidate future router responsibilities:

1. Identify UACP skill family purpose at a high level.
2. Route user work to one of:
   - `uacp-triage`
   - `uacp-propose`
   - `uacp-plan`
   - `uacp-execute`
   - `uacp-verify`
   - `uacp-resolve`
   - `uacp-state`
3. State the bootstrap warning: do not use broken UACP protected lifecycle/runtime machinery to refactor UACP itself.
4. Point to a small set of shared primitives only when needed.
5. Remind future agents that phase skills own execution details.

Candidate router non-responsibilities:

- detailed lifecycle execution SOPs
- comprehensive doctrine
- all read-first references
- historical lesson index
- containment design procedure
- Kanban implementation rules
- phase-specific Agent Council handling
- full planning artifact coverage checklist

## Section classification table

### `# Universal Agent Control Plane`

Candidate classification: keep shortened in router.

Reason: the router needs a one-paragraph identity statement, but not doctrine-level detail.

Possible action later: reduce to concise description and route immediately to skill selection.

### `## Drift guard`

Candidate classification: move to shared primitive or archive; keep only one short warning if needed.

Reason: drift guard is useful but too doctrinal for router. The router can say phase skills derive from UACP and must not redefine it, but details belong elsewhere.

### `## Lifecycle`

Candidate classification: keep shortened in router.

Reason: the routing table depends on lifecycle names.

Possible action later: keep the phase sequence and point to phase skills. Do not include lifecycle semantics here.

### `## Mike-specific UACP doctrine preferences`

Candidate classification: move out of router.

Possible destinations:

- durable memory already holds many of these preferences
- phase-local skills where operational
- shared primitive if truly cross-phase

Reason: router should not be a Mike preference registry. Keeping this here creates bloat and stale preference risk.

### `## Context rehydration before UACP execution`

Candidate classification: move/defer.

Possible destinations:

- phase-local skills for context-loading rules
- `uacp-plan/references/context-loading.md` for planning
- shared primitive only for minimal recall rule

Reason: broad read-first behavior is expensive and contradicts context hygiene. Router can remind to load the appropriate phase skill, not force a large artifact stack.

### `## Skill family`

Candidate classification: keep, rewrite as core router table.

Reason: this is the section closest to actual router responsibility.

Potential issue: current section includes many reference/script entries beyond phase skill routing. Those should not stay in router unless classified as shared primitives.

### `## Read first`

Candidate classification: move out of router; likely split later.

Possible destinations:

- phase-local `references/context-loading.md`
- shared `references/shared/` if primitive
- archive if historical/session-specific

Reason: this section is a major context-bloat source. It makes every UACP invocation act like a large doctrine rehydration, which is exactly the failure being corrected.

### `## Core rules`

Candidate classification: split.

Candidates:

- router keeps only meta-rules: load phase skill; do not self-govern refactor; no mega-SOP
- phase-local rules move to relevant phase modules
- state mutation rules move to `uacp-state`
- Kanban rules move to `uacp-execute` or shared adapter primitive later

Reason: core rules mix global invariants with phase/runtime-specific instructions.

### `## Checkpoints`

Candidate classification: move to shared primitive and phase-local verify/transition docs.

Reason: this is about Agent Council and Heartgate behavior, not router behavior.

Possible destinations:

- shared primitive: council-vs-heartgate distinction
- `uacp-verify/references/followthrough-loop.md`
- phase transition contracts per phase later

### `## Planning package shape`

Candidate classification: move to `uacp-plan` later.

Reason: planning package shape is PLAN-owned, not router-owned.

### `## Planning artifact coverage check`

Candidate classification: move to `uacp-plan` or archive/decompose later.

Reason: it is detailed planning quality checklist, not router behavior. Some items may become plan references; some are historical UACP doctrine checks.

### `## Phase-specific coordination rule`

Candidate classification: move to shared primitive or phase-local execution topology docs.

Reason: useful cross-phase concept, but not router-level. Candidate shared primitive: coordination-adapter-boundary.

### `## Coordination adapter boundary`

Candidate classification: move to shared primitive later.

Reason: cross-phase primitive about Kanban not being doctrine. Should not be embedded in router.

### `## Kanban binding`

Candidate classification: move to `uacp-execute` and/or shared adapter primitive later.

Reason: Kanban is execution/coordination adapter behavior, not router behavior.

### `## Prototype/doc-drift sync`

Candidate classification: move to archive or resolve/state later.

Reason: this is historical/prototype maintenance guidance. It is not router content.

### `## Use this registry when`

Candidate classification: remove or rewrite into router usage trigger.

Reason: useful intent can be reduced to a short trigger section. Current section is redundant if router description/frontmatter is good.

### `## LCP (Liaison Control Plane) — UACP-governed sibling`

Candidate classification: move out of router; likely shared reference or separate `lcp` skill.

Reason: LCP relationship is not needed to route UACP lifecycle skills for this refactor.

### `## Containment and runtime trust boundary`

Candidate classification: move to shared primitive/runtime reference later.

Reason: important but highly detailed runtime policy. Not router responsibility.

### `## Containment design direction`

Candidate classification: archive or move to execution/runtime reference later.

Reason: specific implementation direction and evidence requirements do not belong in router.

### `## Kanban completion guard boundary`

Candidate classification: move to `uacp-execute`/adapter primitive later.

Reason: specific adapter boundary, not router.

### `## Emergency stop`

Candidate classification: keep shortened in router or shared primitive.

Reason: a short stop rule is useful, but detailed resolution belongs in phase/state skills.

### `## Agent Council follow-through wiring`

Candidate classification: move out of router.

Possible destinations:

- shared primitive: council-followthrough-core
- `uacp-verify/references/followthrough-loop.md`
- phase-local transition contracts

Reason: router should not prescribe the whole follow-through workflow.

### `## Skill composition rule from Trustless ACP`

Candidate classification: keep shortened in router for this refactor, then maybe move to shared primitive.

Reason: this is directly relevant to UACP skill loading/refactor behavior. However, full examples should live in a reference, not router.

## Shared reference classification candidates

This is preliminary and should not trigger moves until shared cleanup phase, except router may point to a minimal subset.

### Candidate shared primitives

These may eventually live under `references/shared/`:

```text
agent-council-followthrough.md
heartgate-council-artifact-management.md
state-mutation-protocol.md
adaptive-gate-selection.md
runtime-trust-boundary-correction-20260514.md
```

Caution: even these may need trimming or splitting because current versions may contain phase-specific or historical detail.

### Candidate phase-local references

Likely phase ownership:

```text
retrieval-led-phase-verify.md -> uacp-verify
read-only-containment-validation.md -> uacp-verify or uacp-execute depending final scope
codebase-verification-review-pattern.md -> uacp-verify
phase-end-council-hardening.md -> uacp-verify / transition contracts
proposal-council-concerns-pattern-20260515.md -> uacp-propose or uacp-verify follow-through
phase-transition-finalization-and-validation.md -> per-phase transition contracts
state-mutation-protocol.md -> uacp-state, possibly shared primitive summary
```

### Candidate archive/session notes

Likely historical or run-specific:

```text
phase4-filesystem-containment-start-pattern-20260513.md
phase4b-resolve-lessons-20260514.md
phase5-kanban-completion-guard-20260514.md
phase5-kanban-guard-start-pattern-20260514.md
phase6-agent-council-operationalization-lessons-20260515.md
round3-runtime-construction-lessons.md
runtime-porting-execution-runbook.md
runtime-porting-live-binding-cleanup.md
runtime-porting-version-control.md
trustless-acp-source-analysis.md
```

Caution: archive does not mean delete. Some content may be mined later during the relevant phase.

### Candidate typo/cleanup items

Observed possible typo/inconsistency:

```text
governian-neutral-kernel-adapter.md
guardian-neutral-kernel-adapter.md
```

Determine phase does not resolve this. It should be noted for later shared cleanup.

## Temporary compatibility question

Because phase skills are not yet modular, the router may need a temporary compatibility pointer. Two candidate variants:

### Variant A — strict router now

Immediately shrink router to only routing and bootstrap warnings.

Risk: useful operational rules may become harder to find before phase skills are rebuilt.

### Variant B — router plus legacy-reference warning

Shrink router but include a temporary section:

```text
Legacy references remain in `references/` until phase modules are rebuilt. Do not treat them as router-owned SOPs.
```

Risk: still points to junk drawer, but honestly labels it as legacy.

This should be decided in Decision phase.

## Candidate size targets

Potential targets for future router:

- strict: under 80 lines
- acceptable transition: under 120 lines
- hard fail: over 180 lines

Reason: current 306 lines is far above router responsibility.


## Correction from Mike — no premature file-tree decisions

After this Determine artifact was drafted, Mike clarified that each refactor phase is about one skill and must not start by assuming the final directory/file count. Any candidate file trees or destination lists in this document are therefore non-binding exploration aids only.

For each skill, Determine must answer conceptually before structurally:

1. What was the original intent of this skill?
2. What concept does it represent in UACP?
3. Is a multi-file module actually needed, and if so why?
4. What variants exist, including minimal/small/structured forms?
5. Should Agent Council brainstorm and challenge variants before the Decision phase normalizes and serializes files?

Decision must choose the smallest sufficient structure after this analysis. Do not treat prewritten trees as targets.

## Candidate output of Decision phase

Decision should produce:

1. final router target file tree impact
2. exact sections to keep/rewrite/remove from `SKILL.md`
3. whether to use strict router or temporary legacy pointer variant
4. router line-count target
5. review question for router design
6. audit checks before implementation

## Non-actions in this Determine phase

- Did not patch `SKILL.md`.
- Did not move or archive references.
- Did not create shared/reference directories.
- Did not edit phase skills.
- Did not select final router content.
- Did not run UACP lifecycle or Heartgate.
