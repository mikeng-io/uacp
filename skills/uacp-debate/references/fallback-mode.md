# Default Sub-Agent Path

This is the **primary, runtime-neutral** path: run the protocol on the runtime's native sub-agent dispatch (see `uacp-bridge` for the per-runtime primitive). A shared live multi-agent session, where the runtime offers one, is an optional enhancement — not a precondition.

- Spawn independent sub-agents (one per participant), each in isolation with no inter-agent communication.
- Run a cross-visibility challenge round (Phase 3) explicitly: each reviewer receives the other reviewers' Phase 2 findings and issues challenges through a second sub-agent dispatch. Challenges and responses must flow through real sub-agent messages — the coordinator must NOT synthesize them.
- Phases 4 and 5 proceed as normal.
- Emit the JSON log with `"mode": "independent_subagents"` and NO `session_id` field (or `session_id: null`).

`mode` records which mechanism actually ran. A run on independent sub-agents is labelled `independent_subagents`; a run that used a shared live session is labelled `shared_session`. Neither is "the real one" — but the label must honestly match what happened; a mislabelled log is fabrication.
