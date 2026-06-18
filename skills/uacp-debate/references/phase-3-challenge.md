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

## Challenge Loop (file-pointer model)

Phase 3 runs on persisted round state (`standard`/`thorough` only) — see
`references/round-state-manifest.md`. The coordinator hands out file POINTERS,
NOT embedded payloads: each round's inventory and challenges live on disk, and
sub-agents READ them. This survives crashes, keeps prompts small, and keeps the
run auditable.

Repeat for each round `k` (starting at `k = 2`, since Phase 1 was round 1), up to
`max_rounds` or until convergence (no new valid challenges, no state changes):

1. **Persist round k-1.** Confirm `round-{k-1}/inventory.json` reflects the
   latest states/maturity (it does, from the prior iteration / Phase 1).
2. **Write `round-{k}/challenges.json`** — the coordinator records the DA's (and
   any cross-) challenges, each entry referencing the prior finding/candidate id
   it targets.
3. **Spawn sub-agents with POINTERS.** Spawn the DA and each targeted participant
   with file paths, not payloads: "Read `round-{k-1}/inventory.json` for the
   current inventory, and read the challenges targeting you in
   `round-{k}/challenges.json`." Do NOT embed the inventory into the prompt.
4. **Sub-agents read and respond** (defense, withdrawal, corroboration,
   cross-challenge, discovery, merge-proposal).
5. **Collect** responses into `round-{k}/` and write the updated
   `round-{k}/inventory.json`.
6. **Update `manifest.json`** — append the `rounds[k-1]` entry, bump
   `current_round` to `k`, and update `items`: new states/maturity, any new items
   (a discovery gets `first_round: k` + `lineage.derived_from`), and merges
   (`merged_from` on the survivor, `state: merged` on the absorbed).

If a shared live session is used (`mode: shared_session`), continuity may flow
through it live, but the per-round files + manifest are STILL written as the
durable audit record.
