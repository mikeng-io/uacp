# Artifact Output

Save **two** artifacts per run.

## 1. JSON log — conforms to Gate 1 schema

Path: `.uacp/debate/{YYYYMMDD-HHMMSS}-debate-{review_id}.json`

This file is the authoritative proof-of-execution artifact and MUST conform to `.agents/skills/state/schemas/gate_1_debate_log.schema.json` (v1.0). It is consumed by `record_gate_1_result`, which parses it and derives `challenge_stats` / `finding_summary` from its message counts — downstream callers do not recompute these.

Required top-level fields:
- `schema_version: "1.0"`
- `review_id` (string)
- `mode`: `"debate"` when orchestrated through TeamCreate with a real team session; `"adversarial_subagents"` when orchestrated through parallel Task sub-agents (Fallback Mode above).
- `team_session_id`: non-null string matching the TeamCreate session when `mode: "debate"`; `null` or absent when `mode: "adversarial_subagents"`.
- `reviewers`: array of at least 3 items, each `{participant_id, role, model}` with non-empty strings.
- `messages`: every reviewer message recorded as a separate entry. Fields: `participant_id`, `message_type` ∈ {`finding, challenge, defense, concession, corroboration, cross_challenge, discovery, merge_proposal, final_position`}, `timestamp` (ISO-8601), `content`, optional `finding_id`, optional `in_reply_to`. `challenge`, `defense`, and `concession` messages REQUIRE `in_reply_to` (typically a `finding_id`).
- `final_verdict`: one of `"PASS"`, `"CONCERNS"`, `"FAIL"`.

**Do not fabricate participant voices.** Every entry in `messages[]` must correspond to a real Task-agent (fallback) or TeamCreate-session message that actually happened.

## 2. Markdown summary (optional, human-readable)

Path: `.uacp/debate/{YYYYMMDD-HHMMSS}-debate-{review_id}.md`

YAML frontmatter:
```yaml
---
skill: uacp-debate
timestamp: {ISO-8601}
artifact_type: debate
domains: [{domain1}, {domain2}]
verdict: PASS | FAIL | CONCERNS
intensity: quick | standard | thorough
review_id: "{unique id}"
mode: debate | adversarial_subagents
context_summary: "{brief description of the task}"
---
```

The Markdown is for human readers; the JSON is load-bearing for state.py.

**No symlinks.** To find the latest artifact:
```bash
ls -t .uacp/debate/ | head -1
```
