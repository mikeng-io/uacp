# Fallback Mode

If TeamCreate fails (not available in context):
- Spawn independent Task sub-agents
- Run a cross-visibility challenge round (Phase 3) explicitly: each reviewer receives the other reviewers' Phase 2 findings and issues challenges through a second Task invocation. Challenges and responses must flow through real agent messages — the coordinator must NOT synthesize them.
- Phases 4 and 5 proceed as normal.
- Emit the JSON log with `"mode": "adversarial_subagents"` and NO `team_session_id` field (or `team_session_id: null`).

Do NOT emit `"mode": "debate"` for a fallback run. When consumed by `record_gate_1_result`, the `adversarial_subagents` mode is tagged `confidence_class: "reduced"`; a mislabelled log is fabrication.
