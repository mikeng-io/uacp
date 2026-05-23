# Guardian Hook Audit Pattern

## Purpose

Reusable methodology for auditing whether the Guardian `pre_tool_call` hook (or any plugin hook) is correctly fired across all execution paths in the Hermes Agent runtime — sequential, concurrent, and subagent/delegation.

## When to Use

- After adding a new plugin hook, verify it fires everywhere it should.
- When a security or governance hook appears to be silently bypassed.
- Before declaring a hook "production ready" for UACP Guardian/Heartgate enforcement.
- When refactoring tool dispatch (e.g., adding concurrent execution, changing `_invoke_tool`, or modifying `delegate_task`).

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

Trace every path that calls `handle_function_call()` or `_invoke_tool()`:

| Path | File | Lines | Hook Fired By | Skip Flag? | Risk |
|------|------|-------|---------------|------------|------|
| Sequential (normal) | `run_agent.py` | ~11256 | Inline `get_pre_tool_call_block_message` at ~10991, then `handle_function_call(skip=True)` | Yes (intentional double-fire prevention) | Low |
| Sequential (quiet mode) | `run_agent.py` | ~11227 | Same as above | Yes | Low |
| Concurrent worker | `run_agent.py` | ~10728 | `_invoke_tool(pre_tool_block_checked=True)` which skips its own check because batch pre-flight at ~10614 already checked | N/A (pre-check path) | Low |
| `_invoke_tool` → registry | `run_agent.py` | ~10517 | `_invoke_tool` checks hook first, then passes `skip=True` to `handle_function_call` | Yes | Low |
| Child agent (delegate_task) | `tools/delegate_tool.py` | ~1491 | Child is a full `AIAgent`; uses same `_execute_tool_calls_*` paths as parent | No | Low |

### 3. Verify the Single-Fire Contract

The `skip_pre_tool_call_hook=True` parameter exists to prevent **double-firing** the hook:
- Caller checks the hook (via `get_pre_tool_call_block_message()`)
- Caller then calls `handle_function_call(skip_pre_tool_call_hook=True)`
- `handle_function_call` skips its own hook check because the caller already did it

**Danger sign:** A caller passes `skip=True` without having first called `get_pre_tool_call_block_message()`.

**Verification:** Search for every `skip_pre_tool_call_hook=True` occurrence and confirm the same function/scope has a preceding `get_pre_tool_call_block_message` call.

### 4. Check Agent-Loop Tools

Tools in `_AGENT_LOOP_TOOLS` (`model_tools.py:493`) — `todo`, `memory`, `session_search`, `delegate_task` — are **never routed through `handle_function_call`**. They return an error if called via `handle_function_call` and are handled inline by `_invoke_tool()`.

**Implication:** The hook must be checked **in `_invoke_tool`** (or the sequential/concurrent inline paths) for these tools, not in `handle_function_call`.

Verify `_invoke_tool` checks the hook for all `_AGENT_LOOP_TOOLS` before dispatching.

### 5. Check Subagent/Delegation Path

`delegate_task` spawns child `AIAgent` instances. Each child runs its own `run_conversation()` loop, which uses the same `_execute_tool_calls_sequential()` and `_execute_tool_calls_concurrent()` paths.

**Key question:** Does the child agent load the same plugins as the parent?
- If plugins are loaded globally (e.g., via `PluginManager` singleton), the child sees the same hooks.
- If plugins are loaded per-agent-instance, verify the child's initialization path includes plugin loading.

**Current Hermes behavior:** The `pre_tool_call` hook is global via `PluginManager` — child agents inherit it.

### 6. Assess Risk

| Risk Level | Condition |
|------------|-----------|
| **Critical** | Hook is skipped entirely for a tool class with no fallback check |
| **High** | `skip=True` passed without preceding hook check |
| **Medium** | Hook fires but with wrong `tool_provider` classification, causing Guardian misclassification |
| **Low** | Hook fires exactly once via single-fire contract; all paths covered |

### 7. Report Format

Deliver evidence, not opinions:
- Exact file paths and line numbers for every call site
- What checks the hook vs what skips it
- Current risk classification per path
- Minimal patch direction (if any)

Do not apply fixes during an audit unless explicitly instructed.

## Key Code Locations (Hermes Agent)

| Location | Purpose |
|----------|---------|
| `model_tools.py:697` | `handle_function_call()` — main dispatcher, optional `skip_pre_tool_call_hook` |
| `model_tools.py:493` | `_AGENT_LOOP_TOOLS` — tools handled inline, not via `handle_function_call` |
| `run_agent.py:10433` | `_invoke_tool()` — checks hook before dispatch, passes `skip=True` to `handle_function_call` |
| `run_agent.py:10956` | `_execute_tool_calls_sequential()` — inline hook check per tool |
| `run_agent.py:10550` | `_execute_tool_calls_concurrent()` — batch pre-flight hook check before threading |
| `run_agent.py:10414` | `_dispatch_delegate_task()` — delegates to `tools/delegate_tool.py` |
| `tools/delegate_tool.py:1305` | `_run_single_child()` — child agent execution |
| `hermes_cli/plugins.py` | `get_pre_tool_call_block_message()` — hook invocation helper |

## Known Safe Patterns

- `_invoke_tool` checks the hook, then passes `skip=True` to `handle_function_call` → safe
- `_execute_tool_calls_concurrent` checks the hook in batch pre-flight, then passes `pre_tool_block_checked=True` to `_invoke_tool` → safe
- Child agents use the same loop paths as parents → safe (assuming global plugin state)

## Known Pitfalls

- **Double-fire bug:** If both caller and `handle_function_call` check the hook, observer plugins log every tool call twice. The `skip` flag prevents this.
- **Agent-loop tool bypass:** If `_invoke_tool` forgets to check the hook for `_AGENT_LOOP_TOOLS`, those tools silently bypass Guardian.
- **Wrong `tool_provider`:** `_invoke_tool` hardcodes `"inline_agent_loop"` for agent-loop tools and `"core"` for registry tools. Guardian policy classifies by provider — a misclassification here changes the policy decision.
- **Subagent plugin isolation:** If a future refactor makes plugins per-agent instead of global, child agents could lose hook coverage.

## Communication Note

When explaining `skip_pre_tool_call_hook=True` to Mike, do not imply it automatically disables Guardian or makes delegated work unenforced. State the single-fire contract first: the flag is safe only when the caller already invoked `get_pre_tool_call_block_message()`. Then distinguish the real risk: missing/disabled Guardian or missing hook coverage is a runtime-boundary problem; the skip flag itself is plumbing to avoid double-firing.

## References

- `tests/test_model_tools.py` — `test_skip_flag_prevents_double_fire`, `test_run_agent_pattern_fires_pre_tool_call_exactly_once`
- `tests/run_agent/test_run_agent.py` — `test_invoke_tool_blocked_returns_error_and_skips_execution`, `test_sequential_blocked_tool_skips_checkpoints_and_callbacks`
- `tests/plugins/test_uacp_guardian_plugin.py` — Guardian policy classification and plugin hook integration tests
