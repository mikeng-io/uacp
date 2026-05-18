# QMD Hybrid Search Protocol

## Definition

**QMD** is the retrieval/query plane: Query Mediation Daemon or Query Mediation Service.

It should own a generic hybrid search protocol across existing and future retrieval stores.

## Why QMD exists

There are already multiple retrieval/evidence systems:

- Hermes memory/session search.
- UACP MEMEX/BES.
- Cortex recall/editorial evidence.
- Trustless evidence/registry/BES.
- Future SEF graph/events.
- Nora/public profile context.

Without QMD, every system develops a separate query protocol and ranking logic.

## QMD owns

- Source registry.
- Query planning across sources.
- Keyword/full-text search.
- Vector search.
- Graph-aware retrieval hooks.
- Recency/source/authority weighting.
- Reranking.
- Recall packet assembly.

## QMD does not own

- Authority to act.
- UACP lifecycle authority.
- SEF dispatch decisions.
- Nora/Norty identity policy.
- Canonical graph relationships.

## Protocol sketch

```yaml
query:
  text: 飯局 group Wednesday dinner
  scopes:
    - sef.graph
    - sef.events
    - uacp.memex
    - cortex.recall
  modes:
    - keyword
    - dense_vector
    - sparse_vector
    - graph_neighbors
    - recency
  filters:
    privacy_view: norty_private
    actor: person:mike
    freshness: 30d
  output:
    format: recall_packet
    max_results: 10
```

## Response sketch

```yaml
recall_packet:
  query_id: q_...
  results:
    - source: sef.graph
      type: entity
      id: group:wednesday_dinner
      score: 0.91
      reason: semantic_alias_match + recent_event_link
    - source: sef.events
      type: event
      id: evt_dinner_plan_created
      score: 0.84
      reason: recent related dinner event
    - source: uacp.memex
      type: pattern
      id: pattern_alias_resolution_confirmed
      score: 0.77
      reason: prior successful alias resolution
```

## Relationship to SEF

SEF calls QMD when semantic resolution needs retrieval. QMD may index SEF graph snapshots/events as sources. QMD returns candidates/evidence; SEF still performs graph proof and policy decision.

## Relationship to UACP MEMEX

UACP MEMEX may be a QMD source and may consume QMD recall packets, but QMD does not replace MEMEX governance semantics.
