# Addendum: LEXA Instrumentation Wrapper and Agenda Mediation Boundary

Date: 2026-05-17
Status: architectural refinement

## Clarification

Mike does not mean agents merely call LEXA as a normal client library. He means LEXA may be instrumented as a wrapper/interceptor around an agent SDK/runtime so conversation turns, tool context, or workflow events can be delivered to LEXA for agenda reasoning and context completion.

This is a valid direction, but it requires a stricter boundary than simple retrieval.

## Correct model

LEXA can provide an **instrumentation layer**:

```text
Agent Runtime / SDK
  -> LEXA Instrumentation Middleware
  -> LEXA Agenda Mediation API
  -> Context Packet / Agenda Completion
  -> Agent Runtime continues reasoning/action
```

LEXA receives structured observations about the conversation or workflow and produces an agenda-completed context packet.

## What LEXA may do in instrumentation mode

- observe conversation turns or workflow state through explicit hooks;
- classify the agenda type;
- derive retrieval objectives;
- select sources based on workspace/service/source policy;
- retrieve/fuse/rerank context;
- add provenance, warnings, missing-context notes;
- produce context packet sections;
- suggest context-completion prompts or tool-context hints;
- optionally summarize context for the consuming agent.

## What LEXA must not do by default

- replace the agent runtime's final reasoning loop;
- decide external actions;
- mutate canonical source state;
- bypass UACP/SEF/policy authority;
- auto-send messages or perform side effects;
- ingest all raw conversations without workspace/privacy policy;
- become a hidden all-seeing memory brain.

## Boundary rule

```text
LEXA mediates context.
The agent/runtime reasons and acts.
Governance/policy authorizes.
```

If LEXA is later allowed to perform completion or model reasoning, it should be explicitly scoped as **context completion**, not task completion.

## Instrumentation surfaces

Potential SDK hooks:

```text
before_turn(input, session_metadata)
after_turn(output, tool_calls, observations)
before_tool_call(tool_name, args, agenda)
after_tool_result(tool_name, result, agenda)
before_model_call(messages, agenda)
after_model_call(response, agenda)
workflow_phase_started(phase, state)
workflow_phase_completed(phase, outputs)
```

## Privacy and volume controls

Instrumentation mode is more sensitive than query mode. It needs:

- opt-in per workspace/service/client;
- redaction before sending raw turns;
- policy for what turn fields are stored/indexed;
- sampling or selective capture;
- separation of observe-only vs index vs retrieve;
- public/private profile isolation;
- audit logs for captured context;
- TTL and retention controls;
- explicit source ownership for conversation/session streams.

## API distinction

LEXA should expose separate APIs:

### Query API

For direct agenda/context retrieval:

```text
POST /v1/agendas/query
```

### Instrumentation API

For runtime wrappers:

```text
POST /v1/instrument/turn
POST /v1/instrument/tool-call
POST /v1/instrument/workflow-event
POST /v1/agendas/complete
```

## Agenda completion

`agenda completion` means turning raw runtime context into a retrieval-ready agenda and context packet.

It does not mean completing the user's final task.

Example:

```text
Conversation turn -> agenda inferred as uacp.plan -> sources selected -> context packet returned -> agent writes plan
```

## Design risk

The main flaw risk is boundary collapse. If every conversation is delivered wholesale to LEXA and LEXA stores/reasons over it without strict policy, LEXA becomes a central private memory system, violating source-owned state and profile separation.

The fix is to model conversation streams as sources owned by the client service/workspace, with explicit privacy views and retention.

## Canonical phrase

```text
LEXA can be instrumented as middleware around agent SDKs/runtimes. In this mode it observes scoped runtime context, performs agenda reasoning and context completion, and returns context packets. It does not replace the agent's final reasoning/action loop or governance authority unless a separate explicitly governed execution role is created.
```
