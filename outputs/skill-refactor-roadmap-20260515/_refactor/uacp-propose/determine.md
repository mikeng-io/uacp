# Phase 2 — uacp-propose Determine

Status: Determine gate. No implementation authorized.
Previous: START (PASS/no concerns) → Explore (complete) → Determine.

## Source of truth

- Target skill: /home/norty/.hermes/skills/devops/uacp/uacp-propose/SKILL.md
- Current: 116 lines, 11,183 bytes, max line length 489
- Phase 1 lessons: /home/norty/.hermes/uacp/outputs/skill-refactor-roadmap-20260515/17-phase1-triage-lessons-for-next-phases.md
- Shared references available:
  - ../references/agent-council-followthrough.md (5.4K, 12-step procedure)
  - ../references/proposal-council-concerns-pattern-20260515.md (1.8K, 7-step pattern)

## Classification of every section

| Section | Lines | Classification | Rationale |
|---------|-------|----------------|-----------|
| Frontmatter (name/description) | 1-4 | Keep | Required skill metadata |
| Purpose | 8-9 | Keep | Phase identity — what PROPOSE does |
| Read first | 12-15 | Keep | Ground truth loading — adaptive config-driven |
| Rules | 17-36 | Keep + compress | Core safeguards; some are duplicated or over-long |
| Typical outputs | 38-41 | Keep | Default output contract |
| Updated doctrine alignment | 43-61 | Compress | Contains valuable routing nuance but is prose-heavy |
| Proposal-council remediation pattern | 64-78 | Deduplicate + compress | Same paragraph duplicated twice; belongs in shared reference |
| Validator and Heartgate artifact-shape pitfalls | 81-89 | Keep locally, compress | PROPOSE-specific artifact shape contract; needed for proposal/gate artifacts |
| Phase-specific operating contract — PROPOSE | 93-101 | Keep | Local boundary statement — anti-compression rule for this phase |
| Agent Council follow-through wiring | 104-117 | Replace with reference | Full 9-step body duplicates ../references/agent-council-followthrough.md |

## Specific decisions

### 1. Duplicate remediation paragraphs (lines 64-78)
- Decision: Remove the duplicate block. Keep one concise statement.
- Rationale: The shared proposal-council-concerns-pattern-20260515.md already covers this. PROPOSE only needs a local trigger.
- Risk mitigation: Keep the local trigger sentence.

### 2. Agent Council follow-through wiring (lines 104-117)
- Decision: Replace the 9-step inlined body with a compact local trigger + correct shared reference.
- Rationale: The shared reference at ../references/agent-council-followthrough.md is authoritative and more detailed (12 steps). Inlining creates drift risk.
- Risk mitigation: Keep a local statement of WHEN PROPOSE triggers follow-through and WHAT it must record, then delegate to shared reference.

### 3. Validator/Heartgate shape pitfalls (lines 81-89)
- Decision: Keep as compact PROPOSE-local shape contract.
- Rationale: These are proposal artifact shape requirements. PROPOSE must own its artifact contract. Moving to shared would obscure phase-local accountability.
- Compression: Convert 9 lines of prose bullets to 4-5 compact lines while preserving all required fields.

### 4. Relative reference path
- Decision: Use ../references/agent-council-followthrough.md and ../references/proposal-council-concerns-pattern-20260515.md.
- Rationale: From uacp-propose/SKILL.md, the parent references/ directory is at ../references/. Phase 1 proved references/... alone is wrong.

### 5. Updated doctrine alignment (lines 43-61)
- Decision: Compress to 3-4 lines.
- Rationale: Contains routing nuance but is advisory prose. Core rules already capture the constraints.
- Preservation: Keep the key points about external bridge selection, phase-local granularity, human involvement, and canonical writer obligations.

### 6. Rules section (lines 17-36)
- Decision: Keep all rules but compress long lines and remove redundancy.
- Rationale: These are the protective semantics. Do not equate shorter with safer.
- Specific: The gate-selection artifact requirement (lines 24-33) is long but must stay. Wrap for readability.

### 7. Phase-specific operating contract (lines 93-101)
- Decision: Keep intact. This is the anti-compression boundary statement.
- Rationale: Phase 1 lesson says each phase needs local rules preventing its own boundary failure. This section serves that purpose.

### 8. Proposal-council vs. PLAN/EXECUTE/VERIFY councils
- Decision: Add explicit one-line boundary: PROPOSE council reviews proposal authority, scope, and artifact viability. PLAN/VERIFY councils review implementation and evidence.
- Rationale: Prevents phase logic leakage.

## What PROPOSE will NOT own (reinforced)

- Implementation plan decomposition (PLAN)
- Execution scheduling (EXECUTE)
- Evidence collection beyond proposal/gate shape (VERIFY)
- Generic council procedure body (shared reference)
- State mutation authority (RESOLVE/STATE)
- Heartgate implementation mechanics (runtime)
- Trustless fixed gates/domains/classifications

## Target metrics

- Lines: 85-95 (from 116)
- Max line length: <=120 (from 489)
- Bytes: ~7,500-8,500 (from 11,183)
- All protective semantics preserved
- No duplicate paragraphs
- Correct relative references
- Local phase boundary intact

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Over-compression removes safeguards | Explicit anti-compression rule in operating contract; compare against backup |
| Shared reference breaks | Verify ../references/ exists from skill directory; tested in Phase 1 |
| Validator fields lost | Keep compact shape contract locally; do not move to shared |
| PLAN logic leaks in | Explicit boundary statement; check for plan/execution verbs |
| Trustless specificity | Keep config-driven, adaptive language; no fixed gate ontology |

## Determine conclusion

PROPOSE should be a clean conductor: compact frontmatter, clear purpose, adaptive rules, default outputs, compressed doctrine alignment, local artifact shape contract, local phase boundary, and shared reference for common procedures.

Next step: Decision gate. If Decision council passes, proceed to implementation.
