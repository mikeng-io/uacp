# UACP Runtime Enforcement

This document defines how UACP becomes mechanically enforced at runtime. It is the canonical design for Guardian and Heartgate. It does not replace the constitution, lifecycle reference, or config files; it explains how runtime adapters must implement them.

## Purpose

UACP cannot rely on prompt discipline, skill instructions, or after-the-fact review alone. Runtime enforcement must block unsafe or invalid actions before they execute, especially when actions mutate UACP state, write outside declared containment, trigger external side effects, or advance lifecycle phases.

The production design has two enforcement planes:

- Guardian: runtime tool and side-effect enforcement.
- Heartgate: lifecycle transition enforcement.

Both derive authority from the UACP document chain. Neither may invent policy in code.

## Authority Boundary

Runtime enforcement follows the document authority order in `docs/index.md`:

1. `docs/index.md`
2. canonical prose docs
3. YAML config
4. runtime state pointers
5. skills and runtime implementation
6. execution artifacts

If docs, config, and state conflict, Guardian and Heartgate fail closed for protected actions until the conflict is resolved or an explicit recovery authority is recorded.

## Runtime Trust Boundary

UACP governs actions inside a declared runtime boundary. It does not claim to prevent arbitrary human or host-side mutation outside that boundary, such as editing files in VS Code, changing repository contents manually, or running an external runtime without UACP integration enabled.

Out-of-band mutation is treated as untrusted input until revalidated. When a file, config, plugin binding, or artifact may have changed outside a governed runtime path, the correct response is to re-run the relevant verification and update evidence before relying on it. UACP records whether the current runtime posture is verified; it does not pretend that mutable user files are impossible to change.

Containment is a host/runtime property, not a self-declared UACP permission. UACP may declare that a phase or action requires contained execution; Guardian may verify that the runtime has provided that containment before allowing protected shell/code execution. If the runtime cannot provide or prove the required posture, UACP-bound execution remains fail-closed.

## Runtime Components

| Component | Responsibility | Authority |
|---|---|---|
| Guardian core | Runtime-neutral policy engine for tool calls, paths, state mutation, side effects, and audit decisions. | Implements docs/config/state. |
| Heartgate core | Runtime-neutral phase transition validator. | Implements lifecycle and transition config. |
| Policy packs | Runtime-neutral policy bundles for UACP, Trustless ACP compatibility, or future project/domain-specific governance. | Derived from canonical docs/config; selected by declared governance context. |
| Hermes adapter | Hermes plugin and runtime integration using `pre_tool_call`, `post_tool_call`, and any required control-plane hooks. | Thin adapter only. |
| State mutation tool | The only approved runtime path for UACP runtime-state writes after bootstrap closure. | Implements `uacp-state` policy. |
| Kanban control-plane guard | Protects UACP-bound Kanban task creation, worker spawning, metadata propagation, and completion evidence. | Keeps Kanban as task substrate only. |
| Audit writer | Writes runtime enforcement events to logs and durable UACP artifacts when needed. | Observational, not policy authority. |

## Policy Packs And Runtime Adapters

Guardian is a runtime-neutral enforcement kernel plus policy packs and runtime adapters.

Policy packs encode which governance doctrine applies to a normalized runtime event. The primary policy pack is UACP. Trustless ACP is source material for compatibility where useful, but UACP must not inherit fixed Trustless gate numbers, software-only assumptions, or project-specific path schemas as universal doctrine.

Runtime adapters are UACP-facing downstream implementation components. They translate runtime-specific payloads into normalized Guardian and Heartgate events, pass authority and side-effect metadata, and return decisions/audit evidence to the host runtime. Adapters may include Hermes, Claude Code, OpenCode, Codex, Kimi, Gemini, or future runtimes.

Hermes is the first host/runtime, not the conceptual boundary. Adapter code must stay thin: it may translate, enforce, and audit, but it must not own policy that belongs in UACP docs/config.


## Cognitive Boundary Enforcement

Guardian and Heartgate enforce boundaries between UACP's cognitive/control planes:

- UACP owns governance authority, phase transitions, side-effect permission, human-involvement thresholds, and evidence obligations.
- Agent Council owns deliberative orchestration when selected: role topology, challenge, synthesis, and execution strategy.
- Hermes Kanban owns durable coordination state: task graph, dependencies, status, ownership, and handoffs.
- Agent runtimes, tool adapters, and evidence services perform bounded work or observation under declared authority.

Runtime enforcement must not let one plane silently impersonate another. Kanban mutations must not change UACP phase state. Tool/evidence adapters must not create authority. Worker runtimes must not broaden side effects beyond the plan. Council outputs are evidence and recommendations until accepted by the relevant UACP phase transition.

## Guardian Core

Guardian evaluates normalized runtime events, not raw runtime-specific payloads.

Required event fields for every Guardian event:

- `runtime`
- `adapter`
- `event_type`
- `tool_provider`
- `tool_name`
- `tool_args`
- `task_id`
- `session_id`
- `tool_call_id`

Additional required fields for UACP-bound events and all protected actions:

- `workspace`
- `uacp_run_id`
- `uacp_phase`
- `policy_version`
- `declared_authority`
- `declared_side_effects`

Decision values:

- `allow`
- `allow_with_audit`
- `require_approval`
- `block`
- `block_pending_heartgate`

Conservative failure rule: if a protected action lacks enough context to classify safely, Guardian returns `block` or `block_pending_heartgate`.

Tool classification must use provenance as well as name. Runtime core tools, plugin-registered tools, MCP tools, and inline agent-loop tools can share ordinary-looking tool names. If provenance is missing for a non-core tool, Guardian treats the action as `runtime.extension` until classified.

## Mutation Categories

Guardian classifies actions by side-effect category, not only by tool name.

| Category | Examples | Default handling |
|---|---|---|
| `read.local` | local file reads and searches | allow |
| `external.network_read` | web search and extraction | allow with privacy checks |
| `file.write` | `write_file`, `patch`, generated file writes | require declared path scope |
| `state.uacp` | writes under `state/` | only via state mutation tool |
| `state.kanban` | Kanban complete, block, create, link, comment | allowed only as task traceability |
| `memory.persistent` | memory writes, skill mutation | require storage-boundary decision |
| `exec.shell` | terminal commands | high risk; phase and containment gated |
| `exec.code_with_tool_proxy` | code execution that can call tools | deny unless tool subset is approved |
| `external.browser_interact` | browser click, type, submit, JS eval | require declared external side effect |
| `external.human_message` | sending messages or publishing | require explicit recipient/content authority |
| `external.physical_device` | Home Assistant or desktop/device control | strict approval and rollback/stop path |
| `runtime.subagent` | `delegate_task`, Kanban worker spawn, background agent review | require context propagation and bounded authority |
| `runtime.extension` | plugin install/update, MCP dynamic tools | default deny until classified |
| `automation.future` | cron jobs, background services | require owner, duration, stop path, and rollback |

Dynamic tools from plugins or MCP servers default to `runtime.extension` or `external.unknown_mutator` unless their manifest or policy classifies them as read-only.

Shell enforcement must not rely on command-string inspection alone. For UACP-bound execution, protected write paths such as `state/` must be enforced below the shell command by a filesystem guard, sandbox, read-only mount, or equivalent runtime containment. If that containment is unavailable, `exec.shell` actions that could reach protected UACP paths are blocked in enforce mode. Post-run diff detection is useful audit evidence, but it is not sufficient enforcement.

## Heartgate Core

Heartgate validates lifecycle movement:

```text
TRIAGE -> PROPOSE -> PLAN -> EXECUTE -> VERIFY -> RESOLVE
```

Each transition must satisfy:

- transition is allowed by `config/phase-transitions.yaml`;
- current pointer, run manifest, transition artifact, and phase fields agree;
- required transition inputs exist and parse;
- non-waivable invariants are pass/block only and all pass;
- required evidence clusters are pass or accepted warn;
- blockers are resolved;
- warnings have owners and residual risk;
- deferred items are explicitly accepted by the next phase;
- side effects are declared;
- write containment is recorded;
- state changes are traceable.

Heartgate is not a fixed gate checklist. It validates the selected adaptive evidence set plus invariant checks.

Heartgate also owns the **transition coherence check**. A phase-local council reviews the phase's own work; Heartgate decides whether the lifecycle boundary is truthful. For medium/high-risk transitions, Heartgate may invoke or require a Heartgate Council whose mandate is cross-artifact coherence and consistency, not duplicate implementation review.

Heartgate Council checks:

- phase objective satisfied against the proposal/plan;
- required artifacts and selected evidence clusters exist and parse;
- docs, config, state, runtime behavior, tests, and verification artifacts tell the same story;
- phase-local council findings are resolved, accepted with owners, or blocking;
- warnings/deferred items are honestly carried into the next phase;
- Kanban, Guardian, Heartgate, Agent Council, and runtime adapters have not drifted into each other's authority roles;
- the next phase has a coherent state and explicit obligations.

## Hermes Adapter Requirements

Hermes runtime enforcement starts with a plugin adapter, but the plugin alone is not the whole solution.

The adapter must:

- register `pre_tool_call` and block before execution;
- register `post_tool_call` for audit;
- pass `session_id` and `tool_call_id` into Guardian decisions;
- pass tool provenance into Guardian decisions;
- handle plugin-registered tools;
- avoid hidden policy inside adapter code;
- load policy from `config/guardian-policy.yaml`;
- resolve paths through symbolic roots;
- fail closed for protected actions when policy cannot be loaded.

Known Hermes gaps that must be closed during implementation:

- current hook errors are fail-open by default;
- some `run_agent` prechecks do not pass full session/tool identifiers;
- inline agent-loop tools do not all emit post-tool audit events;
- `PluginContext.dispatch_tool()` can bypass model tool hooks;
- slash commands and dashboard/control-plane actions are outside normal tool-call hooks.
- generic delegation currently starts child agents from prompt/context only, so UACP context must be explicitly injected and audited.

Guardian enforce mode cannot be activated until plugin/internal dispatch and hook-error fail-closed behavior are covered by the guarded dispatch path. Observe mode may record gaps, but it must not be represented as runtime enforcement.

## Kanban Enforcement

Kanban is a task substrate, not UACP phase state. Guardian must still cover UACP-bound Kanban work because workers are separate Hermes processes.

Requirements:

- UACP-bound Kanban tasks carry run id, phase, policy version, and workspace metadata.
- UACP-bound Kanban metadata is stored in a dedicated task-level context record, not only in worker prose or completion metadata.
- Dispatcher refuses UACP-bound tasks missing required Guardian metadata.
- Worker processes receive UACP context through environment or task metadata.
- Worker completion includes Guardian verdict evidence or an explicit missing-verdict warning.
- VERIFY detects UACP Kanban tasks without Guardian audit evidence.
- `/kanban`, CLI, dashboard, and API mutations that affect UACP-bound tasks are guarded by control-plane checks, not only model `pre_tool_call`.

A Kanban task is UACP-bound when any of these conditions are true:

- it has an explicit UACP task context record;
- it is on the configured UACP board and is the active root task recorded in UACP state;
- it is on the configured UACP board and is a descendant of an active UACP root task;
- it is created by a UACP lifecycle/state tool;
- it is explicitly marked UACP-bound by a guarded control-plane request.

If the detector cannot decide safely for a mutation on the configured UACP board, the control-plane guard treats the task as UACP-bound until proven otherwise.

Required worker environment names:

- `UACP_ROOT`
- `UACP_RUN_ID`
- `UACP_PHASE`
- `UACP_GUARDIAN_POLICY_VERSION`
- `UACP_WORKSPACE_POLICY`
- `UACP_GUARDIAN_MODE`

Required Guardian evidence shape in Kanban completion metadata:

```yaml
guardian:
  policy_version: ""
  mode: "enforce"
  verdicts:
    - decision: "allow | allow_with_audit | require_approval | block | block_pending_heartgate"
      category: ""
      audit_artifact: ""
  missing_verdicts: []
```

## State Mutation

After bootstrap closure, runtime state mutation must go through a guarded state mutation path. Direct writes to `state/` are blocked unless explicitly authorized for recovery.

The state mutation path must validate:

- target path is UACP-root-relative;
- target path is within allowed state scope;
- YAML parses;
- required state fields exist;
- authority artifact exists;
- mutation reason is recorded;
- provenance is appended or referenced;
- canonical docs/config are not mutated through the state path.

## Audit

Runtime audit has two layers:

- ephemeral runtime logs under `HERMES_ROOT/logs/uacp/`;
- durable UACP artifacts under `verification/`, `executions/`, `state/runs/`, `outputs/`, or `knowledge/` when a checkpoint or phase decision needs evidence.

Audit records are evidence, not authority. They must not create unmanaged canonical documents.

Minimum audit record fields:

- `policy_version`
- `uacp_run_id`
- `uacp_phase`
- `runtime`
- `adapter`
- `tool_provider`
- `tool_name`
- `category`
- `decision`
- `reason`
- `workspace`
- `authority_artifact`
- `side_effects`
- `audit_artifact`
- `runtime_commit`
- `uacp_commit`

## Breakglass

Breakglass exists for recovery only.

Breakglass requirements:

- explicit operator authority;
- reason;
- affected paths or side effects;
- expiry or one-shot scope;
- audit record;
- follow-up verification.

Breakglass must not silently disable Guardian for an entire runtime.

Disabling the Guardian plugin is a breakglass action. It requires explicit operator authority, affected scope, expiry or one-shot recovery scope, an audit artifact, and follow-up verification. A permanent or unscoped disable is blocked by policy.

## Adapter Compatibility

Future Codex, OpenCode, and Claude adapters must call the same Guardian and Heartgate cores through normalized events. Runtime-specific adapters may translate payloads but must not own policy.

Trustless ACP is source material for this split of core and adapter. UACP must not port fixed Trustless gate numbers, software-only proposal assumptions, or Trustless-specific path/state schemas.

## Implementation Order

1. Guardian policy config.
2. Normalized event and decision schemas.
3. Guardian core.
4. Heartgate core.
5. Hermes `pre_tool_call` adapter.
6. Audit logging.
7. State mutation tool.
8. Hook coverage fixes.
9. Plugin dispatch guard.
10. Kanban control-plane guard.
11. VERIFY detector for missing Guardian evidence.
12. Live activation and proof tests.

Runtime enforcement is not complete until both tool-call enforcement and Kanban/control-plane enforcement are active.
