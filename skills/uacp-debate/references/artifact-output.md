# Artifact Output

Save **two** artifacts per run.

## 1. JSON log

Path: `.uacp/debate/{YYYYMMDD-HHMMSS}-debate-{review_id}.json`

This file is the authoritative proof-of-execution artifact for a debate run; the required-fields list below **is** its contract. (A formal JSON-Schema file and an automated consumer are not built today — if added later, they belong under this skill's own `references/`/`schemas/`, not a centralized state location.)

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
