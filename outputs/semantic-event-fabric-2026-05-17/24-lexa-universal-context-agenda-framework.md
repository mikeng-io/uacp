# Addendum: LEXA as Universal Context Agenda Framework

Date: 2026-05-17
Status: conceptual refinement

## Clarification

LEXA should not be framed as event-specific or human-specific.

It should be a more universal context framework for assembling, ranking, and delivering the right context for any actor, service, workflow, agent, or task.

## Better framing

LEXA is a **universal context agenda framework**.

It does not only answer:

```text
What documents match this query?
What did a human mean?
What events are relevant?
```

It answers:

```text
What context should be brought forward for this actor, operation, phase, decision, workflow, or retrieval objective?
```

## Why “agenda” matters

A query is not always a human search string. It can be an operational agenda:

- a UACP phase entering PLAN;
- a SEF authority proof request;
- a Cortex workflow rerun;
- a Nora outbound dispatch;
- a code review;
- a rollback decision;
- a scheduler/cron task;
- a monitoring alert;
- a model/council needing role-specific evidence;
- a service trying to rebuild a derived index.

LEXA should assemble context according to the agenda, not just the literal query text.

## Agenda object sketch

```yaml
agenda:
  id: agenda_...
  type: uacp.plan | sef.resolve_entity | cortex.verify_article | code.review | incident.triage
  actor:
    kind: agent | service | human | workflow
    id: agent:norty
  objective: retrieve context needed to plan this UACP proposal
  workspace: nortrix
  services:
    - uacp-memex
    - trustless-acp
  sources:
    - evidence
    - patterns
    - docs
  constraints:
    privacy_view: norty_private
    freshness: 90d
    max_latency_ms: 30000
    required_provenance: true
  retrieval_modes:
    - keyword
    - semantic
    - graph_context
    - rerank
    - bes_weight
  output:
    type: context_packet
    audience: agent_council
```

## Context packet, not search result

LEXA output should be a context packet shaped by agenda:

```yaml
context_packet:
  agenda_id: agenda_...
  audience: agent_council
  sections:
    - precedents
    - relevant_patterns
    - source_evidence
    - risks
    - open_questions
  results:
    - id: ...
      source: ...
      reason: ...
      score_features: ...
      provenance: ...
  warnings:
    - stale_index
    - partial_source_coverage
```

## Generalization

LEXA should support context assembly for:

- humans;
- agents;
- model councils;
- workflow phases;
- service automation;
- code analysis;
- governance validation;
- dispatch routing;
- incident response;
- editorial workflows;
- state migration.

## Relationship to SEF

SEF events can produce LEXA agendas, but LEXA is not event-specific.

```text
SEF emits events and needs entity/authority context.
LEXA accepts agenda/query requests and returns context packets.
```

## Relationship to MEMEX

MEMEX can use LEXA agendas for phase-aware recall. For example:

```text
agenda.type = uacp.verify
```

retrieves verification precedents, relevant patterns, prior failures, and evidence sources.

## Naming implication

`LEXA` still works if expanded loosely as:

```text
Lexical + Semantic Agenda
```

Do not over-constrain the acronym. Treat LEXA as the name of the context agenda layer.

## Canonical phrase

```text
LEXA is a source-owned universal context agenda framework: an API server and SDK that assembles agenda-shaped context packets across documents, evidence, events, graphs, code, workflows, conversations, and service state using hybrid retrieval, reranking, optional BES weighting, and scoped source adapters without centralizing canonical state.
```
