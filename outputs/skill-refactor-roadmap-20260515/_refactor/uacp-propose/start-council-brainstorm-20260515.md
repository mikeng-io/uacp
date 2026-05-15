# Phase 2 — uacp-propose START Agent Council

Status: START gate. No Explore/Determine/Decision/Implementation changes authorized by this artifact.

## Context

Previous phases:

- Phase 0 `uacp` router: CLOSED / PASS
- Phase 1 `uacp-triage`: CLOSED / PASS

Committed UACP artifact repo commit:

```text
6bdc9a9 record UACP skill refactor phase 0-1 artifacts
```

Target skill:

```text
/home/norty/.hermes/skills/devops/uacp/uacp-propose/SKILL.md
```

Inherited lessons:

```text
/home/norty/.hermes/uacp/outputs/skill-refactor-roadmap-20260515/17-phase1-triage-lessons-for-next-phases.md
```

## START council results

Three reviewers were dispatched.

Verdicts:

```text
Reviewer 1: PASS
Reviewer 2: CONCERNS
Reviewer 3: PASS
```

Because Mike requires PASS/no concerns, the START gate is not initially passed.

## Reviewer 2 concerns

The concerns are about likely Explore focus areas rather than unsafe read-only inspection:

1. Duplicate proposal-council remediation paragraphs.
2. Validator/Heartgate shape pitfalls are inlined and may belong in a shared/local reference after analysis.
3. Agent Council follow-through wiring is duplicated from the shared primitive.
4. Relative/shared reference strategy must be verified from the skill directory.
5. Check sibling skills for same duplication pattern later, but do not broaden implementation scope now.
6. Preserve UACP generic/adaptive behavior and do not import Trustless fixed gates.

## Resolution for START gate

The concerns are accepted as **Explore constraints**, not implementation decisions.

Allowed next action if follow-up council passes:

```text
Read-only Explore of uacp-propose only.
```

Explicitly not allowed at START/Explore:

- no implementation
- no creating or moving shared references
- no modifying sibling phase skills
- no deciding final file tree
- no UACP protected writers / Heartgate self-approval
- no proposal artifact adoption

Explore must inspect:

- section map and duplicates
- all shared/relative references from the target skill directory
- what belongs locally in PROPOSE vs shared primitive vs later phase
- whether validator/Heartgate shape guidance is PROPOSE-owned or shared
- whether PROPOSE has PLAN/EXECUTE/VERIFY logic leakage
- whether proposal schema fields match current config/docs ground truth
- Phase 1 lesson preservation: shorter is not automatically safer

Follow-up START council must return PASS/no concerns before Explore begins.


## Follow-up START gate verification — PASS

Two independent follow-up reviewers returned **PASS / no concerns** after the initial concerns were accepted as Explore constraints.

Result:

```text
START gate passed for uacp-propose Explore only.
No implementation is authorized by this pass.
```

Explore must remain read-only and focus on the accepted constraints above.
