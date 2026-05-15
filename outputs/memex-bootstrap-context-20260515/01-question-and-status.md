# 01 — Question and Current Status

## Initial question

Mike asked whether current UACP has a Trustless ACP-style “knowledge base”:

- BES score for retrieval
- hybrid search + reranking
- knowledge-base-like pattern/lesson retrieval

## Answer captured

Current UACP has **some of the governance skeleton**, but not the same live retrieval/scoring system as Trustless ACP.

### Current UACP has

- Canonical artifact base:
  - `docs/`
  - `config/`
  - `state/runs/`
  - `plans/`
  - `verification/`
  - `outputs/`
- Retrieval-led reasoning requirements in UACP skills/docs.
- Agent Council and Heartgate transition artifacts.
- References to evidence/domain registry concepts.
- Rich artifacts that could be indexed.

### Current UACP does not yet have

- Live MEMEX-style knowledge base.
- Formal BES scoring loop.
- Hybrid lexical/vector retrieval.
- Reranking over prior governance artifacts.
- Runtime-active evidence/domain registry.
- Automated pattern selection based on prior effectiveness.

## Trustless ACP comparison

Trustless already contains substantially more in this area:

- `.trustless/knowledge/`
  - `ingest.py`
  - `rag.py`
  - `embeddings.py`
  - `reranker.py`
  - `storage.py`
- `.trustless/foresight/`
  - `recall_bridge.py`
  - `effectiveness.py`
  - `effectiveness_scores.json`
- `.agents/skills/lessons/`
  - extraction/reindex scripts
  - `pattern_select.py`
  - BES/domain relevance pattern selection
- Existing terms:
  - recall
  - foresight
  - knowledge
  - evidence
  - BES

## Trustless BES baseline

Trustless-style BES is roughly:

```text
BES = (successes + 1) / (eligible + 2) × recency_factor
```

Interpretation:

```text
How effective was this lesson/pattern at preventing recurrence when it was eligible?
```

## UACP gap statement

UACP currently depends on manual/session-level artifact recall. Each session has to rediscover:

- which prior Heartgate warning applies,
- which council concern recurred,
- which deferred item remains open,
- which runtime boundary was already decided,
- which verification pattern worked,
- which lesson was noise.

This makes MEMEX+BES a natural next capability.
