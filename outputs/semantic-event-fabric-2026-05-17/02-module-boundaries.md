# Module Boundaries

## Locked boundary correction

MEMEX is a **UACP module**. It is not nested under SEF and not under Norty.

SEF is a neutral/generic substrate candidate. Norty and Nora are initial clients/producers/consumers, not owners.

## Boundary map

```text
Nortrix / agent substrate
├── SEF — Semantic Event Fabric
│   ├── Semantic Event Bus
│   ├── Semantic Graph Registry Node
│   ├── Policy / Authority Proof
│   ├── Dispatch Router
│   └── Adapter bindings
│
├── QMD — Query Mediation Daemon/Service
│   ├── hybrid search protocol
│   ├── source routing
│   ├── graph/event/document retrieval
│   └── recall packet assembly
│
├── UACP
│   └── MEMEX + BES
│       ├── evidence index
│       ├── pattern registry
│       ├── recall packets
│       └── governed scoring
│
└── Agents / systems
    ├── Norty
    ├── Nora
    ├── Cortex
    └── Trustless
```

## SEF owns

- Typed semantic event format.
- Event append/receipt flow.
- Semantic Graph Registry Node interface.
- Entity/capability/channel/authority graph references.
- Authority proof format for dispatch.
- Dispatch router abstraction.
- Adapter binding contracts.

## SEF does not own

- UACP lifecycle authority.
- UACP MEMEX/BES.
- All agent memory.
- All search/retrieval.
- Public profile policy doctrine.
- Private Norty context.

## QMD owns

- Hybrid search/query protocol.
- Source adapters across SEF, UACP MEMEX, Cortex, Trustless, Hermes memory, etc.
- Retrieval/ranking/reranking/recall packet assembly.

QMD retrieves; it does not authorize actions.

## UACP MEMEX/BES owns

- Governed evidence and pattern recall for UACP lifecycle/governance work.
- BES scoring for governed patterns.
- Recall packets where UACP needs phase-aware context.

## Integration rule

```text
SEF may produce events/proofs that UACP MEMEX indexes.
SEF may query QMD for semantic resolution context.
QMD may expose UACP MEMEX as a source.
UACP remains governance authority where UACP is in scope.
```
