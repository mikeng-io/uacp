# Phase 2 — uacp-propose Explore

Status: Explore only. No implementation authorized.
START gate: PASS/no concerns after follow-up Agent Council verification.

## Ground truth inspected

Target skill:

```text
/home/norty/.hermes/skills/devops/uacp/uacp-propose/SKILL.md
```

Current size:

```text
116 lines
11,183 bytes
max line length: 489
```

## Current heading map

```text
# UACP Propose
## Purpose
## Read first
## Rules
## Typical outputs
## Updated doctrine alignment
## Proposal-council remediation pattern
### Validator and Heartgate artifact-shape pitfalls
## Phase-specific operating contract — PROPOSE
## Agent Council follow-through wiring
```

## START council constraints inherited into Explore

1. Do not implement during Explore.
2. Do not create or move shared references.
3. Do not modify sibling phase skills.
4. Do not decide final file tree yet.
5. Preserve UACP universal/adaptive semantics.
6. Treat duplicate/inlined material as evidence for Determine, not as automatic deletion.
7. Apply Phase 1 lesson: shorter is not safer if protective semantics are lost.

## Immediate observations

1. `uacp-propose` is significantly denser than triage: 116 lines but 11,183 bytes and max line length 489.
2. There is duplicated proposal-council remediation language:
   - `For UACP governance/runtime/council proposals` appears twice.
   - `proposal council findings` appears twice.
3. Agent Council follow-through wiring is inlined with a 9-step body.
4. Shared follow-through is referenced as `references/agent-council-followthrough.md`, which is likely wrong from the `uacp-propose/` child directory; Phase 1 corrected the equivalent path to `../references/...`.
5. Validator/Heartgate artifact-shape pitfalls are inlined and may be valuable, but their ownership needs classification.
6. The skill mentions real UACP runtime tools (`uacp_doc_write`, `uacp_config_write`, `uacp_heartgate_check`) as eventual runtime obligations. This is valid for normal UACP but must remain separated from this self-repair lane.

## Original intent inferred

PROPOSE is the UACP authority-framing phase.

It exists to answer:

- what work is being proposed?
- who/what authorized it?
- what is in scope and out of scope?
- what side effects are declared?
- what gate-selection/evidence obligations apply?
- what proposal council findings must be handled before PLAN?
- what must PLAN inherit without PROPOSE becoming PLAN?

## Universal UACP role

PROPOSE must remain generic/adaptive. It should not assume a fixed project type, fixed domain taxonomy, fixed reviewer list, or Trustless-style fixed gate topology.

It may require artifact shapes and transition evidence, but those shapes should support universal auditability rather than encode a single product workflow.

## What PROPOSE should own

- objective and rationale
- authority status/source
- in-scope and out-of-scope boundary
- declared side effects
- proposal artifact shape
- gate-selection artifact requirement
- proposal council trigger/handling when selected
- proposal adoption status after TRIAGE evidence is sufficient
- PROPOSE→PLAN transition obligations

## What PROPOSE should not own

- implementation plan decomposition
- execution scheduling
- verify-phase evidence collection beyond proposal/gate-shape requirements
- generic Agent Council follow-through procedure body
- state mutation authority
- Heartgate implementation mechanics
- Trustless fixed gates/domains/classifications
- changes to sibling skills during this phase

## Content likely to preserve locally

- Do not skip TRIAGE adoption.
- Every proposal must reference originating triage artifact.
- Gate-selection artifact required.
- Validator-required proposal fields.
- Council findings must be classified and handled before PROPOSE→PLAN.
- Proposal artifacts drafted early are provisional until TRIAGE→PROPOSE transition is complete.
- Model/provider names should not become canonical doctrine.
- PROPOSE council scope differs from PLAN/VERIFY council scope.

## Content likely to compress or reference later

- Duplicate proposal-council remediation blocks.
- Full 9-step Agent Council follow-through body should likely become a compact local trigger plus `../references/agent-council-followthrough.md`.
- Validator/Heartgate shape pitfalls may need to stay as compact PROPOSE-local shape contract or move to a shared primitive later; Determine must decide based on ownership, not bloat alone.
- Long bullet lines should be wrapped for audit readability.

## Risks to carry into Determine

1. Over-compressing PROPOSE could remove authority/side-effect safeguards.
2. Moving validator/Heartgate shape guidance too early could hide proposal artifact requirements.
3. Keeping all shape guidance inline may preserve bloat and duplicate future phase skills.
4. Wrong relative references can silently break shared primitive access.
5. PROPOSE can accidentally absorb PLAN logic if prior planning package handling is written too broadly.
6. PROPOSE may accidentally become Trustless-specific if gate-selection examples turn into fixed ontology.

## Explore conclusion

The current PROPOSE skill has valuable protective content but is not a clean conductor. Determine should classify each section into:

- keep in PROPOSE conductor
- summarize in PROPOSE conductor
- reference shared primitive
- defer to future shared-reference decision
- remove as duplicate
- mark as normal-UACP-runtime only, not self-repair authority

No implementation should happen until Determine, Decision, end-of-Decision council, implementation audit, and full Agent Council + Kimi end review all pass.
