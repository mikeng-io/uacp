# Artifact Output

Save **two** artifacts per run.

For `standard`/`thorough` runs these two timestamped artifacts are a **roll-up of
`manifest.json`** and the per-round files written during the run — see
`references/round-state-manifest.md` for the durable round state. The manifest +
`round-k/` directories are the auditable source of truth; the artifacts below are
the closing summary derived from them. (`quick` runs have no manifest; the
artifacts are written directly from the single in-memory pass.)

## 1. JSON log

Path: `.uacp/debate/{YYYYMMDD-HHMMSS}-debate-{review_id}.json`

This file is the authoritative proof-of-execution artifact for a debate run; the required-fields list below **is** its contract. (A formal JSON-Schema file and an automated consumer are not built today — if added later, they belong under this skill's own `references/`/`schemas/`, not a centralized state location.)

Required top-level fields:
- `schema_version: "1.0"`
- `review_id` (string)
- `mode`: records WHICH dispatch mechanism actually ran — `"independent_subagents"` when orchestrated through the runtime's native sub-agent dispatch (the default path, see fallback-mode.md); `"shared_session"` when orchestrated through a shared live multi-agent session (Claude Code TeamCreate / Hermes·Kimi Swarm). Neither is "the real one"; the value must honestly reflect what happened.
- `session_id`: the shared-session id, present only when `mode: "shared_session"`; `null` or absent when `mode: "independent_subagents"`.
- `reviewers`: array of at least 3 items, each `{participant_id, role, model}` with non-empty strings.
- `messages`: every reviewer message recorded as a separate entry. Fields: `participant_id`, `message_type` ∈ {`finding, challenge, defense, concession, corroboration, cross_challenge, discovery, merge_proposal, final_position`}, `timestamp` (ISO-8601), `content`, optional `finding_id`, optional `in_reply_to`. `challenge`, `defense`, and `concession` messages REQUIRE `in_reply_to` (typically a `finding_id`).
- `final_verdict`: one of `"PASS"`, `"CONCERNS"`, `"FAIL"`.

**Do not fabricate participant voices.** Every entry in `messages[]` must correspond to a real sub-agent or shared-session message that actually happened.

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
mode: independent_subagents | shared_session
context_summary: "{brief description of the task}"
---
```

The Markdown is for human readers; the JSON is load-bearing for state.py.

**No symlinks.** To find the latest artifact:
```bash
ls -t .uacp/debate/ | head -1
```
