# Phase 1 — uacp-triage Determine

Status: Determine only. No implementation authorized.
Previous artifact: `explore.md`.
START gate: PASS/no concerns.

## Determination goal

Classify the current `uacp-triage/SKILL.md` content into what belongs in the triage conductor, what should be referenced, what should be removed as duplicate, and what must be treated as real-UACP-runtime-only rather than self-repair authority.

## Current section classification

### Frontmatter

Decision candidate: **keep and update minimally if needed**.

Rationale: skill name/description are valid. No new dependencies should be added at this phase.

### Purpose

Decision candidate: **keep, tighten**.

Rationale: captures triage as admission, scoring, routing, and governance-depth selection. Should explicitly frame scoring as adaptive/config-driven, not a fixed universal ontology.

### Read first

Decision candidate: **summarize / keep short**.

Rationale: triage needs canonical config awareness, but the conductor should not force large context hydration. Keep only essential docs/config or say "read when needed".

### Rules / duplicate Rules

Decision candidate: **merge and deduplicate**.

Rationale: duplicate heading is pure noise. Preserve core rules:

- TRIAGE is not PROPOSE.
- Do not compress TRIAGE into PROPOSE.
- Not every request needs full lifecycle.
- Record routing decision and score factors.
- Keep output compact and machine-readable.

### Sequential phase discipline

Decision candidate: **compress into one phase-boundary section**.

Rationale: current section is valuable but verbose. Preserve distinction between TRIAGE council and PROPOSE council. Remove historical/pitfall prose unless it directly changes behavior.

### Typical outputs

Decision candidate: **merge into output contract**.

Rationale: too small as standalone section.

### Execution Steps

Decision candidate: **keep as main conductor checklist**.

Rationale: this is the heart of the skill. It should remain concrete and executable:

1. read relevant config
2. score request
3. determine routing
4. decide council/human involvement
5. write/record triage artifact where appropriate
6. report next step

### Triage Artifact Schema

Decision candidate: **keep compact schema summary in SKILL.md; defer full schema file decision**.

Rationale: A schema is useful, but full schema expansion risks premature file-tree creation. In this pass, merge base schema with updated doctrine fields into a compact contract. Later Decision may create `schemas/` only if justified.

### Updated doctrine alignment

Decision candidate: **merge into output contract and execution checklist**.

Rationale: contains useful fields (`phase_local_granularity`, `human_involvement`) but duplicates schema and adds protected-writer language dangerous for this self-repair lane.

### TRIAGE council trigger and sequencing pitfall

Decision candidate: **keep as compact council-trigger section**.

Rationale: important UACP behavior. Compress and remove repeated examples. Must remain adaptive: council is selected by risk/granularity/authority ambiguity, not fixed domain gates.

### Phase-specific operating contract — TRIAGE

Decision candidate: **compress into ownership boundaries**.

Rationale: valuable but verbose. Keep "does / does not" boundaries. Avoid repeated generic tools language.

### Agent Council follow-through wiring

Decision candidate: **replace body with reference**.

Rationale: shared primitive exists at `references/agent-council-followthrough.md`. Triage should not inline the full procedure. Keep one line: when council output is used, follow the shared primitive and record material findings before advancing.

## Proposed triage conductor responsibilities

The future triage SKILL.md should own:

1. Admission/routing purpose.
2. Adaptive scoring/granularity checklist.
3. Routing outcomes.
4. Council/human-involvement trigger.
5. Compact artifact/output contract.
6. Phase boundary: TRIAGE does not design PROPOSE.
7. Reference to shared council follow-through primitive.
8. Self-repair caveat: this refactor does not use protected UACP writers/Heartgate as authority.

## Proposed non-ownership

The triage SKILL.md should not own:

- proposal artifact design
- final authority/side-effect review
- implementation planning
- state mutation mechanics
- full Agent Council follow-through SOP
- Heartgate implementation details
- MEMEX/BES retrieval
- Trustless fixed gates/domains/classifications

## Candidate target size

Target: under 120 lines.

Reason: current skill is 158 lines and can be reduced by removing duplication and inlined follow-through without losing behavior. Do not force under 80 if it harms clarity.

## Candidate support files

No new support files are justified yet.

Rationale: The only obvious extraction is Agent Council follow-through, and that already exists as a shared reference. Schema extraction might be useful later, but creating a `schemas/` file now would violate Mike's no-premature-file-tree correction.

## Implementation candidate

A targeted rewrite of `uacp-triage/SKILL.md` is likely cleaner than many micro-patches because the file has duplicated and overlapping sections. Scope remains one file only.

Allowed implementation target:

```text
/home/norty/.hermes/skills/devops/uacp/uacp-triage/SKILL.md
```

Required backup before patch:

```text
_refactor/uacp-triage/backup-SKILL-before-triage-implementation.md
```

## Decision prerequisites

Before implementation, the Decision artifact must state:

- exact target content/outline
- one-file scope
- rollback path
- deterministic audit checks
- end-of-Decision Agent Council PASS/no concerns

## Determine conclusion

Proceed to Decision drafting. The Decision should authorize a one-file conductor rewrite only if council review passes. Full implementation must wait for end-of-Decision PASS/no concerns.
