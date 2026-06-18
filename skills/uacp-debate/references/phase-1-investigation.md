# Phase 1: Independent Investigation (Parallel)

**Rationale:** Isolation prevents anchoring bias. If experts see each other's findings first, they pattern-match and corroborate rather than independently discover. Phase 1 ensures each participant forms their view from the evidence alone — not from social agreement with the first finding published.

Spawn all participants in parallel using the runtime's sub-agent dispatch (see `uacp-bridge`). Each receives the same `scope` and `context_summary` but NO communication with other participants.

## Round-1 State (standard/thorough)

For `standard`/`thorough` intensity, Phase 1 IS round 1 of the persisted round
state (see `references/round-state-manifest.md`). Sub-agents get **no priors**
(`context_policy: minimal-non-leading`) — independent discovery is preserved, so
no prior-round file pointers exist yet. Then:

1. Write each sub-agent's raw output to `round-1/participants/{participant_id}.json`.
2. Assemble the findings/candidates into `round-1/inventory.json`, assigning ids
   (F001… for findings; P001… for brainstorm/design candidates).
3. Write `manifest.json` — `current_round: 1`, `status: running`, the `rounds[0]`
   entry, and one `items` entry per assembled item (`state: discovered` for
   findings / starting `maturity` for candidates; `first_round: 1`; empty lineage).

`quick` intensity skips all of this — single in-memory pass, no files.

## Participant Roster

| Role | Count | Source |
|------|-------|--------|
| Domain expert | One per domain in `debate_input.domains` | domain registry Lookup Protocol (`uacp-core/references/domains/`) — exact match, adapted match, or session-based virtual expert |
| Devil's Advocate | 1 (always) | `uacp-debate/experts/devils-advocate.md` |
| Integration Checker | 1 (always) | `uacp-debate/experts/integration-checker.md` |

Domain experts are the primary roster. DA and Integration Checker are structural roles that always accompany them.

## Task Prompt Template

```
You are a {expert_role}.

Task: {context_summary}
Scope: {scope}
Domains in scope: {domains}

## Phase 1: Independent Investigation

Analyze independently. Do NOT coordinate with other participants.

Focus areas: {focus_areas}
Standards: {standards}

## Output Format (JSON)

{
  "participant": "{role-name}",
  "findings": [
    {
      "id": "F001",
      "severity": "CRITICAL | HIGH | MEDIUM | LOW | INFO",
      "title": "Short finding title",
      "description": "Detailed description",
      "evidence": "Specific evidence or reference",
      "recommendation": "What to do about it",
      "domains": ["{domain}"]
    }
  ],
  "phase": 1
}
```

For Devil's Advocate and Integration Checker: apply the role-specific instructions from their expert files.
