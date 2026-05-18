# Semantic Event Fabric

## Definition

**Semantic Event Fabric (SEF)** is a neutral event/entity substrate for agents, channels, tools, workflows, and services.

It combines:

- semantic event bus;
- graph-native registry node;
- policy/authority proof;
- dispatch routing;
- receipts/audit trail.

## Design goal

Allow humans and agents to express intent once, resolve it against canonical graph entities, prove authority, dispatch through the correct adapter, and record receipts.

## Not a normal event bus

A normal event bus moves messages.

SEF moves typed, semantically meaningful, policy-aware events that reference canonical graph IDs and authority proofs.

Example:

```yaml
event_type: intent.requested
actor: person:mike
via: agent:norty
meaning:
  domain: personal_social_logistics
  action: notify_group
  subject: dinner_plan
target_ref: phrase:"飯局 group"
privacy_class: private_to_public_minimized
```

## Core invariant

```text
Semantic retrieval proposes.
Hard graph proves.
Policy decides.
Dispatch executes.
Receipts record.
```

## Lifecycle sketch

```text
CAPTURE
  Mike/agent/channel emits intent or observation.

NORMALIZE
  Event is typed and minimally structured.

RESOLVE
  Semantic phrase/context resolves to graph candidates.

PROVE
  Authority path is traversed in the graph.

DECIDE
  Policy returns allow / confirm / block.

DISPATCH
  Adapter command is emitted.

RECEIPT
  Outcome event is appended.
```

## Privacy invariant

The bus is not a shared memory dump. Events are scoped by views and minimization rules. Public agents such as Nora receive only the resolved, public-safe dispatch command/proof, not Norty private context.
