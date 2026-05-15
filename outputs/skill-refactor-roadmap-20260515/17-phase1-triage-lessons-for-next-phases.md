# Phase 1 Triage Lessons to Inherit

Status: durable handoff from Phase 1 `uacp-triage` to later skill refactor phases.

## Lessons that must carry forward

1. **Reference paths must be tested from the skill directory.**
   - `uacp-triage` initially referenced `references/...`; correct path was `../references/...` because shared primitives live under the parent `uacp/references/` directory.
   - Future phases must validate every relative reference by resolving it from the target skill directory.

2. **Do not equate shorter with safer.**
   - The first rewrite was coherent but over-compressed protective detail.
   - Future phases may shrink bloat, but must preserve safeguards that prevent phase compression, council bypass, schema regression, or authority drift.

3. **Anti-compression rules should stay phase-local.**
   - Shared references can hold common procedures, but each phase skill must retain compact local rules that prevent its own boundary failure.
   - For triage, the local rule was: record TRIAGE→PROPOSE obligations and do not adopt proposal artifacts early.

4. **Shared procedure references are not enough.**
   - Agent Council follow-through can be referenced, but each phase still needs a local statement of when it triggers and what it protects.

5. **Schema/default output contracts must remain adaptive but useful.**
   - Do not hard-code a closed universal schema.
   - Do preserve fields needed for auditability and downstream projection.
   - For triage this meant restoring `rationale`, `artifact_policy`, `notes`, explicit `downstream_projection`, and human authority owner fields.

6. **Council reviewers will check different roots.**
   - Some reviewers searched global backups or wrong skill roots. Instead of ignoring them, add compatibility evidence when cheap.
   - For triage, a compatibility backup under `/home/norty/.hermes/backups/` removed ambiguity.

7. **Line budgets are useful but not primary authority.**
   - Under 120 lines worked for triage only after compact safeguards were restored.
   - Future phases should target compactness, but PASS requires semantic preservation first.

8. **Every implementation closure needs final PASS/no concerns after corrections.**
   - Initial PASS is not enough when any reviewer raises material concerns.
   - Resolve, rerun focused council, and close only after PASS/no concerns.

## Checklist for future phase implementations

Before end-of-implementation council:

- resolve all relative references from target skill directory
- verify backup exists at the phase artifact path
- if reviewers may expect global backup, create compatibility backup
- run line count and max-line-length check
- compare against backup for removed protective semantics
- confirm phase-local boundary/anti-compression rule remains
- confirm any shared reference is evidence/procedure, not hidden authority
- confirm default output contract keeps audit-critical fields
- confirm no Trustless fixed gates/domains leaked into UACP generic/adaptive logic
- confirm no UACP protected writers/Heartgate/MEMEX/BES are used for self-repair approval

## Immediate inheritance to `uacp-propose`

For `uacp-propose`, specifically watch for:

- relative references to shared primitives
- over-compression of proposal authority/side-effect safeguards
- accidental migration of PLAN/EXECUTE logic into PROPOSE
- schema regression in proposal artifact fields
- missing local council trigger even if shared council reference exists
- unclear distinction between PROPOSE council and PLAN/VERIFY councils
