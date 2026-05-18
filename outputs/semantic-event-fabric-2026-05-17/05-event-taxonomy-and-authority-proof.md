# Event Taxonomy and Authority Proof

## Initial event taxonomy

Event classes should remain typed and semantically meaningful.

### Intent / meaning

- `intent.requested`
- `semantic_intent.detected`
- `intent.normalized`

### Entity resolution

- `entity.resolution.requested`
- `entity.resolved`
- `entity.ambiguous`
- `clarification.required`

### Authority / policy

- `authority.path.requested`
- `authority.path.proven`
- `authority.path.failed`
- `policy.decision.made`
- `action.blocked`

### Dispatch

- `dispatch.requested`
- `dispatch.accepted`
- `dispatch.rejected`
- `dispatch.executed`

### Messaging / channels

- `message.sent`
- `message.failed`
- `reply.received`
- `delivery.receipt.received`

### Audit / learning

- `receipt.recorded`
- `pattern.observed`
- `bes.update.proposed`

## Event envelope sketch

```yaml
event_id: evt_...
event_type: intent.requested
created_at: 2026-05-17T...
source:
  actor: person:mike
  agent: agent:norty
  surface: channel:telegram:mike_norty
privacy:
  class: private_to_public_minimized
  allowed_views:
    - norty_private
    - dispatch_proof
payload:
  action: notify
  target_ref: phrase:"飯局 group"
  message: 星期三 8 點去尖沙咀 XX 食飯
links:
  concerns:
    - plan:wednesday_dinner
status:
  state: pending
```

## Authority proof

Every outward action should carry a proof object.

```yaml
authority_proof:
  proof_id: proof_...
  event_id: evt_...
  actor: person:mike
  via: agent:norty
  executor: agent:nora
  capability: capability:send_whatsapp_message
  target: group:wednesday_dinner
  channel: channel:whatsapp:dinner_group
  path:
    - person:mike
    - agent:norty
    - agent:nora
    - capability:send_whatsapp_message
    - group:wednesday_dinner
    - channel:whatsapp:dinner_group
  decision: allowed
  risk_class: low
  confirmation_required: false
  policy_refs:
    - policy:personal_social_low_risk
  graph_snapshot_ref: graph_snapshot:...
```

## Rule

No outward dispatch should rely only on an LLM or semantic score. It needs a graph-derived authority proof plus policy decision.
