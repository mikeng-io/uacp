# Semantic Graph Registry Node

## Definition

The **Semantic Graph Registry Node (SGRN)** is a graph-native operational ontology for entities, aliases, capabilities, policies, channels, authority edges, privacy boundaries, and event links.

It is not a normal DB table of contacts.

## Why graph-native

The important information is in relationships and paths:

```text
Mike ─AUTHORIZES→ Norty
Norty ─MAY_REQUEST→ Nora
Nora ─HAS_CAPABILITY→ send_whatsapp_message
Nora ─MAY_MESSAGE→ Dinner Group
Dinner Group ─REACHABLE_VIA→ WhatsApp Group
```

Dispatch requires path validation, not a simple lookup.

## Node types

Initial node vocabulary:

- Person
- Agent
- Group
- Channel
- Device
- Service
- Workflow
- Capability
- Policy
- Event
- Intent
- Command
- Artifact
- Place
- Plan
- CalendarEvent
- Conversation
- CredentialRef
- Boundary

## Edge types

Initial edge vocabulary:

- ALIASES / RESOLVES_TO
- MEMBER_OF
- OWNS / OPERATES
- AUTHORIZES
- MAY_REQUEST
- MAY_EXECUTE
- MAY_MESSAGE
- REACHABLE_VIA
- PREFERS_CHANNEL
- HAS_CAPABILITY
- CONSTRAINED_BY
- VISIBLE_TO
- REDACTS_FOR
- DERIVED_FROM
- CONCERNS
- PART_OF
- RESPONDED_TO
- SCHEDULED_FOR

## Hard graph vs semantic index

The registry has two layers:

```text
Hard graph:
  deterministic, canonical, policy-relevant nodes and edges.

Semantic index:
  fuzzy/contextual aliases, embeddings, text references, recent context.
```

Invariant:

```text
Semantic index proposes.
Hard graph disposes.
```

High semantic similarity may propose an entity. It must not authorize action without graph proof.

## Scoped views

The graph must expose scoped views:

- Norty private view: full private/operator graph.
- Nora liaison view: allowed public/social targets and safe labels only.
- Dispatch proof view: minimal nodes/edges needed for one action.
- Audit view: event/proof/receipt, possibly redacted.

## Example traversal

```text
phrase:"飯局 group"
  → RESOLVES_TO group:wednesday_dinner
  → REACHABLE_VIA channel:whatsapp:dinner_group
  → MAY_MESSAGE from agent:nora
  → authority path from person:mike via agent:norty
```
