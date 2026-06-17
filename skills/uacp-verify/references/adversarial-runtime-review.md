# Adversarial Runtime Review Pattern

Use this pattern when reviewing UACP runtime enforcement for bypasses, authority-boundary leaks, and fail-open hazards. It complements deterministic verification by tracing the actual host-runtime dispatch path, not just the policy design.

## When to apply

- Before claiming Guardian/Heartgate is "live" or "production-complete."
- After any host-runtime upgrade that changes tool dispatch, hook invocation, or plugin loading.
- When a new bypass class is suspected (e.g., subagent spawning, parallel execution, plugin tool dispatch).
- As a mandatory phase-end council input for enforcement/containment phases.

## Review methodology

1. **Load the design docs** (`docs/runtime/runtime-enforcement.md`, `config/uacp.toml [guardian]`) and confirm stated invariants.
2. **Trace the host-runtime hook path** in the actual source (e.g., `run_agent.py`, `hermes_cli/plugins.py`). Look for:
   - `skip_pre_tool_call_hook=True` or equivalent bypass flags.
   - Direct registry dispatch that bypasses plugin hooks.
   - Exception handlers that swallow hook errors and proceed (fail-open).
   - Inline agent-loop tools with custom dispatch.
3. **Classify every bypass** by severity:
   - **Critical:** Protected actions can execute without ever touching the Guardian.
   - **High:** Hook errors or missing context cause silent allow instead of block.
   - **Medium:** Audit or context fields are lost, weakening traceability.
4. **Trace path resolution** for symlink/TOCTOU attacks:
   - Does `Path.resolve()` follow symlinks before containment checks?
   - Is there a race between path validation and file write?
   - Does the code use `Path.cwd()` for unqualified paths despite policy forbidding it?
5. **Check enforcement self-protection:**
   - Can the model disable the Guardian plugin via ordinary `file.write` or `terminal`?
   - Are the plugin config, symlink, and host-runtime source protected by a non-cooperative mechanism?
6. **Map verification gaps:**
   - Which bypasses are covered by existing proof artifacts?
   - Which are deferred or untested?
   - Does the proof test fresh-session behavior or only the current long-running session?

## Known bypass classes (Hermes runtime)

| Bypass | Location | Mechanism | Current mitigation |
|---|---|---|---|
| `skip_pre_tool_call_hook=True` | `run_agent.py` delegate/parallel paths | `handle_function_call` skips hook for subagents and parallel tools | None verified; must be patched in host runtime |
| Direct registry dispatch | `tools.registry.registry.dispatch()` | Any code can import and call registry dispatch directly, bypassing `PluginContext.dispatch_tool()` | Trust model only; no registry-level guard |
| Hook exception swallowing | `hermes_cli/plugins.py:get_pre_tool_call_block_message()` | `except Exception: hook_results = []` causes silent allow on plugin failure | None; host-runtime behavior |
| `PluginContext.dispatch_tool` gap | `hermes_cli/plugins.py:457` | Plugin slash commands use `dispatch_tool`, but not all plugin code uses `PluginContext` | Partial; depends on plugin author discipline |
| Non-UACP-bound shell/code | `kernel.py:is_uacp_bound()` | Paths just outside `UACP_ROOT` with no UACP context are `allow_with_audit`, not `block` | Policy default; observe mode |
| Model disables Guardian | `file.write` on `~/.hermes/config.yaml` or `rm` symlink | Ordinary tool calls can remove plugin from config or filesystem | None; no self-protection mechanism |

## Questions that must be answered before claiming enforcement is complete

1. **How is the `skip_pre_tool_call_hook` bypass closed?** If the host runtime skips the hook for subagents/parallel tools, is there a second enforcement layer, or is UACP-bound work forbidden from using those paths?
2. **What protects the enforcement mechanism from the model?** If the model can edit config or delete the plugin symlink, the enforcement is cooperative, not mandatory.
3. **What is the exact filesystem containment specification?** Before `exec.shell` or `exec.code_with_tool_proxy` are unblocked for UACP-bound work, the sandbox technology, initialization, verification, and subagent handling must be specified and proven.

## Output shape

Produce an adversarial review artifact with:

- **Objections:** numbered, severity-ranked, each with design claim vs. actual behavior.
- **Bypass table:** tool/classification, location, mechanism, mitigation status.
- **Top N questions:** the minimum questions that must be answered before implementation proceeds.
- **Verification gap analysis:** which bypasses are covered by existing proof artifacts and which are not.
- **Recommendation:** whether the system can be considered enforced, partially enforced, or design-only.

Store the artifact under `verification/` with kind `uacp.adversarial_runtime_review`.
