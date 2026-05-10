# UACP Runtime Guardian Implementation Plan

Goal: implement mechanical UACP runtime enforcement through Guardian and Heartgate without hardcoding fixed gates or software-only assumptions.

## Scope

This plan covers the implementation after the design checkpoint is accepted. It does not implement the full Knowledge Bank service.

Primary artifacts:

- `docs/runtime-enforcement.md`
- `config/guardian-policy.yaml`
- `HERMES_ROOT/hermes-agent/plugins/uacp_guardian/`
- Hermes hook coverage changes where needed
- Guardian tests under Hermes test tree
- UACP verification artifacts under `verification/`

## Phase 1 — Policy And Schema Foundation

1. Confirm `docs/runtime-enforcement.md` is registered in `docs/index.md`.
2. Confirm `config/guardian-policy.yaml` parses and is registered.
3. Define normalized Guardian event schema in code.
4. Define Guardian decision schema in code.
5. Define conditional required fields for UACP-bound and protected actions.
6. Define tool provenance classification for core, plugin, MCP, inline-agent-loop, and control-plane tools.
7. Define Guardian evidence schema used by Kanban completion metadata and VERIFY.
8. Define audit record schema with commit/provenance fields.
9. Add tests for schema validation and fail-closed behavior.

Acceptance:

- malformed policy blocks protected actions;
- missing UACP root blocks UACP-bound protected actions;
- missing run/phase/policy/authority/side-effect context blocks UACP-bound protected actions;
- missing tool provenance defaults non-core tools to protected `runtime.extension`;
- non-UACP ordinary reads are not blocked.

## Phase 2 — Guardian Core

1. Implement runtime-neutral Guardian core.
2. Load `config/guardian-policy.yaml`.
3. Resolve symbolic roots.
4. Classify tool calls by category.
5. Enforce direct UACP state-write blocking.
6. Enforce protected path containment.
7. Classify dynamic MCP/plugin tools by wildcard rules until explicitly classified.
8. Require filesystem-level protected-write enforcement for shell/code/subagent/future automation actions.
9. Return deterministic decisions.

Acceptance:

- direct `write_file` or `patch` into `state/` is blocked;
- terminal attempts to mutate `state/` through redirect, `tee`, interpreter code, generated scripts, or symlink traversal are blocked by containment, not by command-string matching alone;
- dynamic unknown mutator defaults to block when UACP-bound;
- `delegate_task` is classified as `runtime.subagent`;
- Home Assistant mutating tools and browser interaction tools are classified by exact Hermes tool names;
- allowed local reads still execute.

## Phase 3 — Heartgate Core

1. Implement transition artifact loader.
2. Validate phase transition against `config/phase-transitions.yaml`.
3. Validate invariant status values.
4. Validate required artifacts exist and parse.
5. Validate blockers, warnings, deferred items, side effects, and containment.
6. Return `pass`, `warn`, or `block` with reasons.

Acceptance:

- blocking invariant blocks transition;
- missing required artifact blocks transition;
- invalid phase edge blocks transition;
- accepted warn requires owner/risk evidence;
- valid transition passes.

## Phase 4 — Hermes Plugin Adapter

1. Add `plugins/uacp_guardian/plugin.yaml`.
2. Add plugin `register(ctx)`.
3. Register `pre_tool_call`.
4. Register `post_tool_call` for audit.
5. Resolve UACP root from config/env.
6. Convert Hermes payloads into normalized Guardian events.
7. Include tool provider/provenance in normalized events.
8. Return Hermes block directives for Guardian block decisions.

Acceptance:

- plugin is disabled unless enabled by Hermes config;
- enabling plugin activates pre-tool blocking;
- block messages include category and reason;
- audit events are written outside `docs/`.

## Phase 5 — State Mutation Tool

1. Add guarded `uacp_state_write` tool or equivalent plugin tool.
2. Require authority artifact, reason, and target path.
3. Validate target path under allowed state scope.
4. Validate YAML parse and required fields.
5. Append or reference provenance.
6. Reject canonical doc/config mutation through this tool.

Acceptance:

- authorized state mutation succeeds;
- missing authority blocks;
- invalid YAML blocks;
- canonical docs/config target blocks.

## Phase 6 — Hermes Hook Coverage Hardening

1. Pass `session_id` and `tool_call_id` into all `run_agent` pre-tool checks.
2. Add shared guarded dispatch path for `PluginContext.dispatch_tool()`.
3. Add post-tool audit events for inline agent-loop tools where feasible.
4. Guard `delegate_task` as `runtime.subagent`.
5. Inject UACP context into child agent prompts/environment where Hermes supports it.
6. Add protected filesystem containment for terminal/code execution touching UACP protected paths.
7. Define fail-closed behavior for Guardian hook errors on protected actions.

Acceptance:

- blocked sequential tool call does not execute;
- blocked concurrent tool call does not execute;
- plugin internal dispatch cannot bypass Guardian;
- child agents receive UACP run/phase/policy context for UACP-bound delegated work;
- shell/code execution cannot mutate UACP `state/` except through the guarded state mutation path;
- inline agent-loop tool coverage is audited or explicitly documented as deferred.

## Phase 7 — Kanban Control-Plane Enforcement

1. Add a durable UACP task context storage path for Kanban:
   - preferred: `task_uacp_context` table keyed by task id;
   - fallback during migration only: `task_events.kind = uacp_context`.
2. Implement the authoritative UACP-bound task detector:
   - explicit UACP task context;
   - configured UACP board plus active root task from UACP state;
   - configured UACP board plus descendant of active root task;
   - creation by UACP lifecycle/state tool;
   - explicit guarded UACP-bound marker.
3. Treat ambiguous mutations on the configured UACP board as UACP-bound until proven otherwise.
4. Extend Kanban task creation paths to accept or derive UACP context for UACP-bound work.
5. Add UACP metadata requirements for UACP-bound Kanban tasks.
6. Propagate Guardian context to worker processes through:
   - `UACP_ROOT`
   - `UACP_RUN_ID`
   - `UACP_PHASE`
   - `UACP_GUARDIAN_POLICY_VERSION`
   - `UACP_WORKSPACE_POLICY`
   - `UACP_GUARDIAN_MODE`
7. Add dispatcher preflight for UACP-bound tasks.
8. Guard Kanban task mutations that affect UACP-bound work.
9. Add VERIFY-time detector for missing Guardian verdicts.

Acceptance:

- UACP-bound worker without Guardian metadata is refused or warned by policy;
- CLI/dashboard/API task creation cannot create UACP-bound tasks without UACP context;
- UACP-bound classification is consistent across board slug, parent graph, state/kanban roots, CLI, dashboard, and API;
- worker receives UACP root/run/phase/policy context;
- completion metadata carries Guardian evidence;
- VERIFY flags missing Guardian evidence.

## Phase 8 — Deployment And Live Proof

1. Enable plugin in Hermes config.
2. Restart relevant Hermes gateway/service.
3. Run unit tests.
4. Run integration proof commands.
5. Run live negative tests:
   - direct `state/` write blocked;
   - terminal redirect into `state/` blocked;
   - invalid transition blocked;
   - authorized state tool succeeds;
   - Kanban worker context is present.
6. Run control-plane negative tests:
   - UACP-bound Kanban task creation without context is blocked;
   - dashboard/API mutation of UACP-bound task without Guardian context is blocked;
   - delegated child agent without injected UACP context is blocked.
7. Run shell containment negative tests:
   - redirect into UACP `state/` blocked;
   - `tee` into UACP `state/` blocked;
   - interpreter write into UACP `state/` blocked;
   - symlink traversal into UACP `state/` blocked.
8. Write UACP verification artifact.
9. Commit Hermes and UACP roots separately.

Activation preconditions:

- Guardian hook errors fail closed for protected actions.
- `PluginContext.dispatch_tool()` and other plugin/internal dispatch paths use the guarded dispatch path.
- Tool provenance is present for core, plugin, MCP, inline-agent-loop, and control-plane actions.
- Protected filesystem containment is active for shell/code execution or enforce mode blocks those categories.
- Kanban UACP-bound detector works across CLI, dashboard, API, dispatcher, and worker paths.
- Negative proof tests pass and are recorded in UACP verification artifacts.

Provenance requirements:

- Verification artifact records `policy_version`, UACP commit, Hermes runtime commit, plugin commit or tree state, test command results, audit artifact paths, and rollback/breakglass artifact paths if used.
- UACP and Hermes commits are separate when both roots change.
- Runtime state commits are not required for every transient audit event, but checkpoint artifacts that justify activation, rollback, or phase transition must carry commit pointers.

## Test Commands

Initial proof set:

```bash
cd HERMES_ROOT/hermes-agent
uv run pytest tests/test_model_tools.py::TestPreToolCallBlocking
uv run pytest tests/run_agent/test_tool_call_guardrail_runtime.py
uv run pytest tests/plugins/test_uacp_guardian_plugin.py
uv run pytest tests/tools/test_terminal_output_transform_hook.py::test_terminal_output_transform_integration_with_real_plugin
```

Optional packaging proof:

```bash
cd HERMES_ROOT/hermes-agent
nix flake check .#bundled-plugins
```

## Rollback

Rollback is a breakglass action, not an ordinary operational toggle.

1. Record explicit operator authority, reason, affected scope, expiry or one-shot scope, and audit artifact path.
2. Disable `uacp_guardian` in Hermes `plugins.enabled` only for the affected runtime/scope.
3. Restart Hermes gateway/service for that affected scope.
4. Keep audit logs and verification artifacts.
5. Record rollback reason under `verification/`.
6. Run follow-up verification that confirms the recovery scope, remaining risk, and re-enable plan.

Rollback must not delete UACP docs/config. It only disables runtime enforcement while preserving evidence.
