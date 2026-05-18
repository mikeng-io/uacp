# MVP: Nora Dispatch

## First use case

```text
Mike tells Norty:
  幫我通知飯局 group，星期三 8 點去尖沙咀 XX 食飯。

System outcome:
  Nora sends the message through her WhatsApp account/group.
  Norty reports delivery status back to Mike.
```

## Flow

```text
1. CAPTURE
   Mike sends natural language instruction to Norty.

2. NORMALIZE
   Norty emits `intent.requested` with action=notify and target_ref="飯局 group".

3. RESOLVE
   SEF/QMD resolves phrase to candidate graph entity `group:wednesday_dinner`.

4. PROVE
   Semantic Graph Registry Node proves authority path:
   Mike → Norty → Nora → send_whatsapp_message → Dinner Group → WhatsApp Channel.

5. DECIDE
   Policy classifies the request as low-risk social logistics.
   confirmation_required=false if target is allowlisted and content is non-sensitive.

6. DISPATCH
   SEF emits bounded dispatch command for Nora.

7. SEND
   Nora WhatsApp adapter sends public-safe message.

8. RECEIPT
   Message sent/failed receipt is emitted and recorded.

9. REPORT
   Norty tells Mike the result.
```

## Example normalized event

```yaml
event_type: intent.requested
actor: person:mike
via: agent:norty
payload:
  action: notify
  target_ref: phrase:"飯局 group"
  message: 星期三 8 點去尖沙咀 XX 食飯
routing_hint:
  executor: agent:nora
  channel: whatsapp
privacy:
  class: private_to_public_minimized
```

## Example Nora dispatch command

```yaml
command_type: liaison.dispatch.send_message
executor: agent:nora
channel: channel:whatsapp:dinner_group
target: group:wednesday_dinner
message: Mike 話星期三 8 點去尖沙咀 XX 食飯，大家 mark 低先。
authority_proof_id: proof_...
```

## MVP limits

- One target group.
- One outbound channel first: WhatsApp or Discord, whichever is easier to verify.
- No global contact import.
- No autonomous cold outreach.
- No public profile access to private graph.
- No BES auto-mutation in MVP.
