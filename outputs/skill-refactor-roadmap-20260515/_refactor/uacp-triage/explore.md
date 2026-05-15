# Phase 1 — uacp-triage Explore

Status: Explore only. No implementation authorized.
START gate: PASS/no concerns after follow-up Agent Council verification.

## Ground truth inspected

Target skill:

```text
/home/norty/.hermes/skills/devops/uacp/uacp-triage/SKILL.md
```

Current size:

```text
158 lines
8,956 bytes
```

Relevant shared references checked:

```text
references/agent-council-followthrough.md — exists, 86 lines / 5,505 bytes
references/lifecycle-skill-contract.md — exists, 58 lines / 1,993 bytes
references/adaptive-gate-selection.md — exists, 97 lines / 2,811 bytes
references/state-mutation-protocol.md — exists, 64 lines / 1,814 bytes
```

## Current heading map

```text
# UACP Triage
## Purpose
## Read first
## Rules
## Rules
## Sequential phase discipline
## Typical outputs
## Execution Steps
## Triage Artifact Schema
## Updated doctrine alignment
## TRIAGE council trigger and sequencing pitfall
## Phase-specific operating contract — TRIAGE
## Agent Council follow-through wiring
```

## Immediate structural observations

1. Duplicate `## Rules` heading exists.
2. Triage contains repeated anti-compression/sequencing doctrine across Rules, Sequential phase discipline, and TRIAGE council trigger.
3. Triage contains two schema blocks or schema-like areas:
   - base `Triage Artifact Schema`
   - `Updated doctrine alignment` additions
4. Triage includes detailed Agent Council follow-through wiring even though `references/agent-council-followthrough.md` exists.
5. Triage includes UACP protected writer / Heartgate instructions that are valid for real UACP runs but dangerous if interpreted as authority for this self-repair lane.
6. Triage mixes stable phase behavior with repair-history corrections.

## Original intent inferred

Triage is the UACP admission/routing phase.

It exists to answer:

- should this request enter UACP at all?
- if yes, at what governance depth?
- what is the initial granularity estimate?
- is triage-local Agent Council needed?
- is human involvement required before further lifecycle progression?
- what obligations must PROPOSE inherit without TRIAGE designing the proposal?

## Universal UACP role

For UACP, TRIAGE must remain generic/adaptive. It should not assume a fixed product domain, fixed Trustless gate sequence, fixed reviewer list, or fixed classification taxonomy.

It may use scoring factors, but those factors should remain configurable/adaptive rather than hard-coded as universal ontology.

## What triage should own

- admission decision
- scope/granularity estimate
- visible risk/hotspot note
- routing outcome
- whether triage-local council is required
- whether immediate human authority is required
- compact triage artifact shape
- transition obligations to PROPOSE when proceeding

## What triage should not own

- proposal design
- final authority/side-effect review
- implementation plan design
- verification/council follow-through procedure body
- state mutation authority
- Heartgate implementation mechanics
- MEMEX/BES integration in this refactor pass
- Trustless-specific fixed gates/domains/classifications

## Candidate smallest-sufficient shape, not a decision

A future Decision may consider reducing `SKILL.md` to a conductor with:

1. Purpose / when to use
2. Universal boundary
3. Triage checklist
4. Output contract summary
5. Council trigger rule
6. Non-ownership / stop rules
7. References to shared primitives instead of inlining them

This is not a file-tree decision. It is only an Explore finding.

## Content likely to keep in some form

- Purpose: admission/routing/granularity.
- Rule: TRIAGE must not compress into PROPOSE.
- Execution steps: read config, score request, determine routing, record artifact, report next step.
- Human involvement fields and reason.
- Council trigger concept for high-granularity governance-core work.
- Scope separation between TRIAGE council and PROPOSE council.

## Content likely to shrink or move/reference

- Duplicate `## Rules` header.
- Repeated anti-compression prose.
- Full YAML schema blocks may become compact output contract plus local/reference schema if justified later.
- Full Agent Council follow-through wiring should likely be replaced by reference to `references/agent-council-followthrough.md` or a phase-local summary.
- Tool language about `uacp_heartgate_check`, `uacp_doc_write`, and `uacp_config_write` must be carefully separated from this self-repair lane.

## Risks to carry into Determine

1. Over-trimming may remove the crucial TRIAGE-before-PROPOSE correction.
2. Leaving schema duplicated may preserve ambiguity.
3. Leaving council follow-through inlined may keep every phase skill bloated.
4. Removing all Heartgate/Guardian mentions may hide real lifecycle transition obligations.
5. Hard-coded scoring weights may make UACP less adaptive/universal.
6. Treating this self-repair lane like normal UACP runtime may recreate recursion.

## Explore conclusion

The current triage skill has valuable content but is not a clean conductor. The next Determine phase should classify each current section into:

- keep in triage conductor
- summarize in triage conductor
- reference shared primitive
- defer to future schema/support file decision
- remove as duplicate
- mark as real-UACP-run only, not self-repair lane

No implementation should happen until Determine, Decision, end-of-Decision council, Audit, and end-of-implementation council all pass.
