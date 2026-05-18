# Semantic Event Fabric — Design Capture Index

Date: 2026-05-17
Status: exploratory architecture capture
Owner context: Nortrix agent substrate discussion

## Purpose

Capture the current consensus around a neutral, generic Semantic Event Fabric (SEF) and adjacent Query Mediation Daemon/Service (QMD) before implementation decisions drift.

## Documents

1. `01-problem-statement.md` — why SEF/QMD are needed.
2. `02-module-boundaries.md` — boundaries between SEF, UACP MEMEX/BES, QMD, Norty, Nora, Cortex, and Trustless.
3. `03-semantic-event-fabric.md` — SEF core abstraction and lifecycle.
4. `04-semantic-graph-registry-node.md` — graph-native registry node design.
5. `05-event-taxonomy-and-authority-proof.md` — event classes and authority proof shape.
6. `06-qmd-hybrid-search-protocol.md` — QMD role and retrieval protocol.
7. `07-storage-and-model-options.md` — DB/model choices, including Kuzu correction.
8. `08-mvp-nora-dispatch.md` — first concrete use case.
9. `09-open-questions.md` — decisions still needed.

## Locked corrections from discussion

- SEF should be neutral and generic, not Norty-owned.
- A Hermes-based lite MVP is acceptable, but the abstraction should survive outside Hermes.
- MEMEX is a UACP module, not a component nested under SEF or Norty.
- SEF may integrate with UACP MEMEX/BES; it does not own them.
- The registry node should be graph-native, not a normal entity table.
- Kuzu is not the selected DB because Mike flagged it as deprecated.

## Core invariant

```text
Semantic retrieval proposes.
Hard graph proves.
Policy decides.
Dispatch executes.
Receipts record.
MEMEX recalls.
BES ranks.
```
