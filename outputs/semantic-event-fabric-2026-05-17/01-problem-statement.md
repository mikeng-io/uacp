# Problem Statement

## Trigger

Mike wants one private control path for outward coordination. Example:

```text
Mike tells Norty: notify my friends that Wednesday dinner is at X.
Norty should route the request to the appropriate public/outbound identity, likely Nora, which sends through WhatsApp or another channel.
```

This cannot be modeled safely as “Norty controls Nora.” It needs a neutral event/entity substrate.

## Problem

Current systems already contain overlapping retrieval, registry, and evidence patterns:

- Hermes memory/session search.
- UACP MEMEX/BES.
- Cortex recall/editorial evidence.
- Trustless evidence/registry/BES lineage.
- Future Nora/public-profile communication context.

Without a shared abstraction, each system will invent its own names, routing rules, entity resolution, event format, and retrieval protocol.

## Needed capability

The system needs to answer:

- What did Mike intend?
- Which canonical entity does a phrase such as “飯局 group” refer to?
- Which agent/public identity should execute?
- Which channel reaches the target?
- Is there an authority path from Mike to the action?
- What context is safe to reveal to a public profile?
- What event, receipt, and proof should be recorded?
- What previous evidence/pattern should be recalled or ranked?

## Proposed direction

Create a neutral **Semantic Event Fabric (SEF)** and adjacent **Query Mediation Daemon/Service (QMD)**:

```text
SEF = semantic event/entity/authority/dispatch substrate.
QMD = retrieval/query plane across multiple evidence and memory stores.
UACP MEMEX/BES = governed memory/scoring module, integrated but not owned by SEF.
```

## Non-goals for this capture

- No runtime implementation yet.
- No protected UACP state mutation.
- No claim that SEF is UACP-core.
- No claim that SEF is Norty-owned.
- No final DB/model choice beyond recording current preferences and constraints.
