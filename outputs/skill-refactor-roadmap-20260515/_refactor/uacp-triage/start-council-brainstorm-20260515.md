# Phase 1 — uacp-triage START Agent Council Brainstorm

Status: START council completed; initial verdict CONCERNS, not passable yet under Mike's rule.

## User rule

Every phase start and end requires Agent Council verification. Proceed only on PASS/no concerns. Maximize automation and patch existing artifacts where possible.

## Correct target skill path

```text
/home/norty/.hermes/skills/devops/uacp/uacp-triage/SKILL.md
```

The skill exists. Some council findings looked at `/home/norty/.hermes/skills/uacp/` and reported no dedicated triage skill; that is a path/context error for this refactor lane.

## Initial council verdict

Overall: **CONCERNS**

No material blocker to Explore, but concerns must be resolved before START gate can pass.

## Useful findings

- Current triage skill is about 158 lines / ~9KB.
- It has duplicated `## Rules` header.
- It repeats "do not compress TRIAGE into PROPOSE" in multiple sections.
- It has overlapping triage artifact schema blocks.
- It inlines Agent Council follow-through wiring that already exists as a shared reference.
- It mixes triage-owned behavior with transition/Heartgate/protected-writer language.
- It must preserve UACP universal/adaptive behavior and not import Trustless fixed classifications.

## Triage should own

- admission/routing decision
- granularity/scoping estimate
- routing outcome selection
- whether triage-local council is needed
- compact triage artifact contract
- human-involvement flag when authority is unclear

## Triage should not own

- proposal design
- implementation planning
- final authority/side-effect proposal review
- fixed domain taxonomy copied from Trustless
- Heartgate implementation details
- state mutation authority
- MEMEX retrieval before MEMEX tooling is classified
- shared Agent Council follow-through procedure body

## Concerns to resolve before START gate PASS

1. **Path/context error:** council references to missing `uacp-triage` under `.hermes/skills/uacp/` are irrelevant to this refactor path. Correct path exists under `.hermes/skills/devops/uacp/uacp-triage/`.
2. **Guardian/tooling constraint:** current self-repair uses normal file/git/Hermes artifact workflow; do not invoke UACP protected writers/Heartgate as self-repair authority.
3. **Scope constraint:** Explore must inspect triage intent/structure only; no implementation and no PROPOSE design.
4. **MEMEX constraint:** do not add MEMEX retrieval to triage in this phase.
5. **Council follow-through constraint:** triage may reference the common follow-through primitive but should not inline the full procedure body.
6. **Universal boundary:** scoring/routing must remain adaptive/generic, not Trustless fixed gate/domain import.

## Resolution patch for follow-up council

The above concerns are resolved for START-gate purposes as constraints on Explore:

- Explore will use the correct existing skill path: `/home/norty/.hermes/skills/devops/uacp/uacp-triage/SKILL.md`.
- Explore will not modify skill files.
- Explore will not use UACP protected writers or Heartgate as self-repair authority.
- Explore will not design PROPOSE, PLAN, EXECUTE, VERIFY, RESOLVE, or STATE behavior.
- Explore will treat MEMEX/BES as out of scope for triage MVP unless only mentioned as future context.
- Explore will identify duplicated content, ownership boundaries, schema overlap, shared-reference dependencies, and smallest-sufficient triage structure.
- Explore will preserve UACP universal/adaptive semantics.

Follow-up council question: Do these constraints resolve the START gate enough to proceed to `uacp-triage` Explore only, with no implementation?


## Follow-up START gate verification — PASS

Two independent follow-up reviewers returned **PASS / no concerns**.

Result:

```text
START gate passed for uacp-triage Explore only.
No implementation is authorized by this pass.
```

Key pass rationale:

- correct skill path exists under `/home/norty/.hermes/skills/devops/uacp/uacp-triage/SKILL.md`
- previous missing-skill concern was a path error
- Explore constraints prevent UACP protected-writer recursion, MEMEX scope creep, PROPOSE compression, and Trustless fixed-taxonomy import
- next step is read-only Explore of current triage intent/structure
