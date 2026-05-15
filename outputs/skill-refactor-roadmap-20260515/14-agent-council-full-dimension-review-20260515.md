# Agent Council Full-Dimension Review — UACP Skill Revamp/Restructure

Date: 2026-05-15
Status: Council synthesis, review-only. No implementation decisions are adopted automatically.

## Council verdict

Overall verdict: **CONCERNS**

No reviewer returned PASS. No reviewer returned an unconditional hard BLOCK, but several findings are preconditions before continuing to Decision/Implement.

## Council roles

1. Skill Architecture / Modularity Reviewer
2. Governance Semantics / Lifecycle Integrity Reviewer
3. Context Hygiene / Memory / Maintainability Reviewer
4. Devil's Advocate
5. Implementation Practicality / Auditability Reviewer

## Shared conclusion

The roadmap is directionally correct but not yet safe to execute. It correctly diagnoses the broken UACP skill layer, rejects UACP self-governance, and captures Mike's corrections about one-skill-at-a-time modular refactoring. However, the process itself is already showing the same risks it is meant to eliminate: exploratory bloat, premature classification, weak measurement gates, unclear authority, and possible re-entrenchment of shared references.

## Critical findings

### C1 — Missing concrete tooling contract

Severity: Blocker before implementation

The roadmap says not to use broken UACP machinery, but does not explicitly forbid the concrete UACP writer/check tools during this refactor.

Required rule:

```text
For this refactor, use normal file/git workflow only. Do not use uacp_doc_write, uacp_config_write, uacp_state_write, uacp_artifact_write, uacp_heartgate_check, or UACP protected state mutation as authority for the refactor.
```

### C2 — Missing authority / approval rule

Severity: Blocker before implementation

The process does not declare who approves each Decision artifact. Since UACP is considered broken, the agent cannot self-approve structural decisions.

Required rule:

```text
Mike approves each skill's Decision artifact before Implement, unless he explicitly delegates that authority for a bounded step.
```

### C3 — Review independence is underspecified

Severity: High

The Review step exists but does not require independence.

Required rule:

```text
Review must be performed by a different agent/council instance, or explicitly by Mike. The same agent that authored Decision should not rubber-stamp Review.
```

### C4 — Audit has metrics but no enforceable gates

Severity: High

Measurement files list good concepts but lack concrete thresholds, baseline capture, or scripts/checklists.

Required additions:

- baseline snapshot before each skill phase
- line/context budgets
- scope boundary checks
- local-reference checks
- no unapproved shared-reference dependency check

### C5 — Roadmap artifacts are already growing into a decentralized mega-SOP

Severity: High

Split artifacts are better than one mega-doc, but the package is already large. Router Explore+Determine alone became larger than the intended target router.

Required addition:

```text
Roadmap hygiene rule: per-skill exploratory artifacts must have a size budget or checkpoint before continuing.
```

### C6 — Router-first implementation is questionable

Severity: High concern

One reviewer argued router should be last because it cannot know what to route to until phase skills are rebuilt. Another suggested a minimal temporary router variant now. Synthesis: router can be handled now only as **provisional/minimal**, not final.

Decision implication:

```text
Router Phase 0 should not perform a full content migration. It may only create a minimal compatibility router or defer implementation until after phase skills mature.
```

### C7 — Shared references cleanup cannot wait until the very end without quarantine

Severity: High

If the 38 shared references remain active throughout phase refactors, new skills may keep depending on the junk drawer.

Required rule:

```text
Before rebuilding phase skills, create a lightweight shared-reference quarantine/classification: Primitive / Phase-owned / Archive / Delete-candidate. New phase skills may not reference ../references unless the Decision artifact explicitly justifies it.
```

This does not mean fully migrating shared references first. It means classifying/quarantining them enough to prevent re-entrenchment.

### C8 — Premature structure still leaks into Determine artifacts

Severity: High

The correction file says not to predefine file trees, but router Determine still classifies many sections into future destinations. This is allowed only as raw input, not as Decision.

Required rule:

```text
Determine artifacts may list variants and candidate destinations, but Decision must explicitly re-justify structure from skill intent and smallest-sufficient design. Determine classification cannot be treated as requirements.
```

### C9 — Agent Council role is vague and could recentralize

Severity: Medium-High

Council can help brainstorm but may become a new central synthesis factory. Need hard triggers/exclusions.

Required rule:

```text
Agent Council is optional and bounded. Use for ambiguous, governance-critical, or cross-boundary skills. It provides brainstorm/challenge input, not authority. It must not create files inside skill dirs before Decision.
```

Council trigger should be recorded in Determine: not used / used, with reason.

### C10 — Bootstrap termination condition missing

Severity: Medium-High

The roadmap says UACP must not govern its repair, but not when it may govern again.

Required addition:

```text
Define bootstrap exit: after all selected skill modules pass independent review/audit and Mike accepts closure, future changes may re-enter rebuilt UACP flow. Until then, normal workflow remains authority.
```

### C11 — No rollback/recovery rule

Severity: Medium

If Implement fails, no rule says whether to revert, patch, re-explore, or stop.

Required addition:

```text
Each Implement must have rollback criteria. If audit/review fails after patch, either revert the skill directory to baseline or open a new Explore correction; do not patch ad hoc across phases.
```

### C12 — No inter-skill closure/handoff artifact

Severity: Medium

One skill can finish without preserving what the next skill needs.

Required addition:

```text
After each skill Implement, produce a closure/handoff note: changed files, deferred items, shared-reference claims, next-skill warnings, and whether baseline assumptions changed.
```

## Should-not-do list from council

1. Do not proceed to implementation from current router Determine.
2. Do not treat router Determine's section classification as a requirements document.
3. Do not pre-create `references/`, `templates/`, `schemas/`, or `scripts/` for every skill.
4. Do not use current UACP validator/Heartgate as approval for this refactor.
5. Do not create new shared references during phase skill implementation unless replacing/declaring a true primitive.
6. Do not allow Agent Council brainstorming to serialize files before Decision.
7. Do not let `_refactor/` become a permanent junk archive.
8. Do not let any new phase skill depend on `../references/` without explicit Decision justification.
9. Do not continue growing roadmap files without hygiene limits/checkpoints.
10. Do not claim implementation completeness without independent review and measurable audit.

## Recommended additions before next phase

### A1 — Bootstrap contract

Create a short artifact defining:

- authority: Mike approves Decision before Implement
- permitted tools: normal file/git only
- forbidden UACP writer/check tools for this refactor
- independent review requirement
- bootstrap exit condition
- rollback rule

### A2 — Roadmap hygiene rules

Create/update an artifact defining:

- artifact size budget/checkpoint
- no session transcript dumping
- baseline snapshots expire or must be regenerated before use
- `_refactor/<skill>` is temporary working evidence, not permanent doctrine

### A3 — Baseline/audit checklist template

Add a reusable checklist for every skill:

- current file list
- SKILL.md line count
- local references count
- shared references used
- duplicated concept checks
- default load size/context budget
- scope boundary check

### A4 — Shared reference quarantine pass

Before phase-skill implementation, classify shared references into:

```text
Primitive
Phase-owned
Archive
Delete-candidate
```

This is classification only, not migration.

### A5 — Council-use policy

Define when council is used:

- required for ambiguous governance-core concepts
- optional for simple/mechanical skills
- not authority by itself
- output captured as brainstorm/challenge input
- no file serialization before Decision

### A6 — Per-skill closure/handoff template

After each skill Implement, record:

- changed files
- verification/audit result
- decisions made
- deferred items
- shared-reference impact
- next skill warnings

## Sequencing recommendation

Before continuing Router Decision, insert a corrective meta-step:

1. Add bootstrap contract.
2. Add roadmap hygiene / artifact size rule.
3. Add baseline/audit checklist template.
4. Add shared-reference quarantine classification requirement.
5. Add council-use policy.

Then continue with Router Decision, but treat router implementation as minimal/provisional only.

## Notes on conflicting council advice

Some reviewers recommended collapsing the roadmap to fewer files or moving the refactor outside `UACP_ROOT`. These are valid concerns but not adopted as immediate blockers in this synthesis because Mike explicitly asked for detailed split artifacts saved under proper UACP artifact locations. Instead, the adopted mitigation is roadmap hygiene and size/checkpoint discipline, not deletion/collapse of existing captured detail.

## Final synthesis

Proceeding directly to router Decision would be premature. The roadmap needs a small correction layer first: authority, tooling, review independence, audit enforceability, shared-reference quarantine, and council-use policy. Once those are captured, the one-skill-at-a-time loop remains valid.
