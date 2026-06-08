# Packetized Exchange Contract

Councils exchange information through immutable packets and message envelopes when auditability matters, especially in nested Deep Council runs.

## CouncilTaskPacket

```json
{
  "packet_type": "discovery | challenge | reconciliation | final-position",
  "schema_version": "1.0",
  "review_id": "...",
  "mode": "review | audit | brainstorm | design | research | synthesis",
  "artifact": {"scope": "..."},
  "objective": "...",
  "domains": [],
  "constraints": {
    "mutation": "forbidden | allowed",
    "evidence_required": true,
    "independent_discovery": true,
    "avoid_leading_context": true
  },
  "context": {
    "minimal_background": "...",
    "known_claims": [],
    "prior_findings": [],
    "prior_proposals": []
  },
  "output_contract": {
    "format": "json",
    "proposal_schema": "proposal-v1",
    "finding_schema": "finding-v1"
  }
}
```

Round 1 for discovery/brainstorm must use `context_policy: minimal-non-leading`: include scope, objective, hard constraints, and output contract; exclude expected findings, suspected root causes, coordinator-preferred design, prior participant outputs, and desired verdict.

## ExchangeEnvelope

```json
{
  "packet_type": "exchange_envelope",
  "schema_version": "1.0",
  "message_id": "MSG001",
  "session_id": "...",
  "round": 2,
  "exchange_mode": "coordinator-mediated | session-continuity | direct-async | stateless-replay",
  "from": {"participant_id": "coordinator", "council_id": "root"},
  "to": {"participant_id": "codex-local-council", "council_id": "child"},
  "message_kind": "prompt | context_packet | proposal_packet | challenge | response | synthesis | final_summary",
  "references": {"packet_ids": [], "proposal_ids": [], "finding_ids": [], "artifact_ids": []},
  "payload": {},
  "delivery": {"transport": "task-tool | codex-mcp-thread | cli-prompt | agent-team-sendmessage | file-drop"}
}
```

## Brainstorm Proposal Object

```json
{
  "id": "P001",
  "title": "...",
  "summary": "...",
  "rationale": "...",
  "proposal_type": "schema | protocol | lifecycle | policy | implementation",
  "maturity": "seed | sketched | refined | candidate | accepted | rejected | parked",
  "tradeoffs": [],
  "dependencies": [],
  "open_questions": [],
  "risks": [],
  "lineage": {"derived_from": [], "supersedes": [], "merged_from": []},
  "status": "proposed"
}
```
