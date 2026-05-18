# Addendum: LEXA SDK and Reasoning Boundary

Date: 2026-05-17
Status: architectural refinement

## Python SDK correction

LEXA should ship Python SDK support early, not only Go SDK.

Rationale:

- Hermes is Python-based.
- Many Nortrix/UACP/Cortex integration surfaces use Python or Python-friendly tooling.
- Agent SDK integrations often expect Python clients.
- Early adoption will be blocked if Python has to wait too long.

Recommended initial language split:

```text
Server/control plane: Go
Primary SDKs at first glance: Go + Python
Generated/light clients later: TypeScript
```

## Reasoning boundary

LEXA may include **context-planning reasoning**, but should not own final agent reasoning or authority decisions.

Allowed inside LEXA:

- agenda interpretation;
- query planning;
- source selection;
- query expansion;
- candidate explanation;
- result fusion rationale;
- context packet sectioning;
- stale/insufficient context warnings;
- optional model-assisted reranking or summarization when configured.

Not owned by LEXA:

- final task reasoning;
- policy/authority decisions;
- UACP lifecycle decisions;
- SEF graph authority proof decisions;
- external side-effect execution;
- agent commitments.

## Correct integration model

Client agents can instrument LEXA through SDKs:

```text
Agent/Workflow -> LEXA agenda request -> LEXA context packet -> Agent/Workflow reasoning/action
```

LEXA can shape the context packet according to an agenda, but the consuming agent/runtime remains responsible for reasoning over it and acting under its own policy/governance layer.

## LEXA internal agenda planning

LEXA should support deterministic and optional model-assisted agenda planning.

Example:

```yaml
agenda:
  type: uacp.plan
  objective: retrieve context needed for implementation planning
  actor: agent:norty
  audience: agent_council
```

LEXA may transform this into retrieval plans:

```yaml
retrieval_plan:
  sources:
    - uacp.memex.patterns
    - uacp.docs.lifecycle
    - trustless.acp.references
  modes:
    - keyword
    - semantic
    - rerank
    - bes_weight
  sections:
    - precedents
    - risks
    - relevant_contracts
    - prior_failures
```

But LEXA should return the packet, not decide the plan itself.

## SDK responsibilities

Python SDK should include:

- typed client for query/agenda/context-packet APIs;
- source adapter base classes;
- helper for Hermes tool/plugin integration;
- local test fixtures;
- async support;
- Pydantic models generated or maintained from shared schemas.

Go SDK should include:

- typed client;
- adapterkit;
- server-internal shared public schema types where safe;
- conformance helpers.

## Flaw to avoid

Do not make LEXA a hidden agent brain.

If LEXA starts deciding what the agent should do, it collapses boundaries with Hermes, UACP, SEF, or Strands-like agent runtimes.

The safe rule:

```text
LEXA reasons about context assembly.
Agents reason about tasks.
Governance layers decide authority.
```

## Canonical phrase

```text
LEXA can be instrumented into any agent SDK through Go/Python SDKs. It accepts agendas, performs context-planning and hybrid retrieval, then returns provenance-preserving context packets. It does not replace the agent runtime, final reasoning loop, or authority layer.
```
