---
type: pattern
title: Guardian Hook Audit Pattern
description: "7-step hook-audit procedure, single-fire contract (`skip_pre_tool_call_hook` semantics), `_AGENT_LOOP_TOOLS` bypass risk, 4-level risk classification, known safe patterns and pitfalls."
tags: [guardian, hooks, audit, security]
timestamp: 2026-06-17
---

# Guardian Hook Audit Pattern

Reusable methodology for auditing whether the Guardian `pre_tool_call` hook (or any plugin hook) is correctly fired across all execution paths — sequential, concurrent, and subagent/delegation.

## When to Use

- After adding a new plugin hook, verify it fires everywhere it should.
- When a security or governance hook appears to be silently bypassed.
- Before declaring a hook "production ready" for UACP Guardian/Heartgate enforcement.
- When refactoring tool dispatch (e.g., adding concurrent execution, changing `invoke_tool`, or modifying `execute_tool_calls_concurrent`).

## Audit Procedure

### 1. Locate the Hook Entry Point

Find where the hook is invoked:
```python
search_files("get_pre_tool_call_block_message", path=".", file_glob="*.py")
search_files("invoke_hook.*pre_tool_call", path=".", file_glob="*.py")
```

Also find the `skip_pre_tool_call_hook` flag:
```python
search_files("skip_pre_tool_call_hook", path=".", file_glob="*.py")
```

### 2. Map All Call Sites

Trace every path that calls `handle_function_call()` or `invoke_tool()`. For each path record: file, hook-fired-by, whether skip flag is set, and risk level.

Key structural locations to check (refer to current Hermes source for line numbers — do not rely on stale references):

- `handle_function_call()` — main dispatcher, optional `skip_pre_tool_call_hook`
- `_AGENT_LOOP_TOOLS` constant — tools handled inline, not via `handle_function_call`
- `invoke_tool()` — checks hook before dispatch, passes `skip=True` to `handle_function_call`
- `execute_tool_calls_sequential()` — inline hook check per tool
- `execute_tool_calls_concurrent()` — batch pre-flight hook check before threading

### 3. Verify the Single-Fire Contract

The `skip_pre_tool_call_hook=True` parameter exists to prevent **double-firing** the hook:
- Caller checks the hook (via `get_pre_tool_call_block_message()`)
- Caller then calls `handle_function_call(skip_pre_tool_call_hook=True)`
- `handle_function_call` skips its own hook check because the caller already did it

**Danger sign:** A caller passes `skip=True` without having first called `get_pre_tool_call_block_message()`.

**Verification:** Search for every `skip_pre_tool_call_hook=True` occurrence and confirm the same function/scope has a preceding `get_pre_tool_call_block_message` call.

### 4. Check Agent-Loop Tools

Tools in `_AGENT_LOOP_TOOLS` — typically `todo`, `memory`, `session_search`, `delegate_task` — are **never routed through `handle_function_call`**. They are handled inline by `invoke_tool()`.

**Implication:** The hook must be checked **in `invoke_tool()`** (or the sequential/concurrent inline paths) for these tools, not in `handle_function_call`.

Verify `invoke_tool()` checks the hook for all `_AGENT_LOOP_TOOLS` before dispatching.

### 5. Check Subagent/Delegation Path

`delegate_task` spawns child `AIAgent` instances. Each child runs its own `run_conversation()` loop, which uses the same `execute_tool_calls_sequential()` and `execute_tool_calls_concurrent()` paths.

**Key question:** Does the child agent load the same plugins as the parent?
- If plugins are loaded globally (e.g., via `PluginManager` singleton), the child sees the same hooks.
- If plugins are loaded per-agent-instance, verify the child's initialization path includes plugin loading.

### 6. Assess Risk

| Risk Level | Condition |
|------------|-----------|
| **Critical** | Hook is skipped entirely for a tool class with no fallback check |
| **High** | `skip=True` passed without preceding hook check |
| **Medium** | Hook fires but with wrong `tool_provider` classification, causing Guardian misclassification |
| **Low** | Hook fires exactly once via single-fire contract; all paths covered |

### 7. Report Format

Deliver evidence, not opinions:
- Exact file paths and structural function names for every call site
- What checks the hook vs what skips it
- Current risk classification per path
- Minimal patch direction (if any)

Do not apply fixes during an audit unless explicitly instructed.

## Known Safe Patterns

- `invoke_tool()` checks the hook, then passes `skip=True` to `handle_function_call` → safe
- `execute_tool_calls_concurrent()` checks the hook in batch pre-flight, then passes `pre_tool_block_checked=True` to `invoke_tool()` → safe
- Child agents use the same loop paths as parents → safe (assuming global plugin state)

## Known Pitfalls

- **Double-fire bug:** If both caller and `handle_function_call` check the hook, observer plugins log every tool call twice. The `skip` flag prevents this.
- **Agent-loop tool bypass:** If `invoke_tool()` forgets to check the hook for `_AGENT_LOOP_TOOLS`, those tools silently bypass Guardian.
- **Wrong `tool_provider`:** Runtime code may hardcode provider labels (e.g., `"inline_agent_loop"` for agent-loop tools, `"core"` for registry tools). Guardian policy classifies by provider — a misclassification here changes the policy decision.
- **Subagent plugin isolation:** If a future refactor makes plugins per-agent instead of global, child agents could lose hook coverage.

## Communication Note

When explaining `skip_pre_tool_call_hook=True`, do not imply it automatically disables Guardian or makes delegated work unenforced. State the single-fire contract first: the flag is safe only when the caller already invoked `get_pre_tool_call_block_message()`. Then distinguish the real risk: missing/disabled Guardian or missing hook coverage is a runtime-boundary problem; the skip flag itself is plumbing to avoid double-firing.
