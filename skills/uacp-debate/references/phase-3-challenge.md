# Phase 3: Challenge Round (standard + thorough only)

**Rationale:** Domain experts are motivated to defend their findings — they found them, they believe them. DA's adversarial role exists precisely because no expert naturally looks for reasons their own finding is wrong. The challenge round is the mechanism that separates real findings (survive attack) from inflated or pattern-matched ones (fail under scrutiny). Multi-round structure catches second-order effects: a DA challenge may spawn a discovery, which then needs its own challenge.

Run challenge rounds up to `max_rounds`. Each round:

## Devil's Advocate Obligations

**MUST challenge** every CRITICAL/HIGH finding not originated by DA.
**SHOULD challenge** MEDIUM findings when pattern detected.
**Cross-domain synthesis** — DA discovers new findings from cross-domain patterns.

## Challenge Message Format

Send via sub-agent communication (embed in follow-up sub-agent prompts):

```json
{
  "type": "challenge",
  "from": "devil-advocate",
  "to": "target-reviewer",
  "finding_id": "F002",
  "challenge": "This assumes X, but what if Y?",
  "severity_challenge": "MEDIUM not HIGH because..."
}
```

## Response Types

- **defense**: Reviewer defends finding with additional evidence
- **withdrawal**: Reviewer withdraws finding (insufficient evidence)
- **corroboration**: Another reviewer confirms the finding
- **cross-challenge**: Reviewer challenges a different finding
- **discovery**: New finding discovered during debate
- **merge-proposal**: Two similar findings proposed for merging

## Challenge Loop

Repeat for up to `max_rounds` rounds:
1. Spawn DA sub-agent with all current findings + challenge obligations
2. Spawn all other participants with challenges directed at them
3. Collect responses
4. Update finding states
