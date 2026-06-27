# Codex runtime adapter

Codex **reuses** the shared logic — it ships no Codex-specific code:

- the **MCP governed-tools server** `runtime-adapters/mcp/uacp_mcp_server.py`
  (one server, all runtimes), registered through Codex's MCP configuration, and
- the **shared PreToolUse Guardian shim**
  `runtime-adapters/shared/guardian_pretooluse.py` *if and only if* Codex exposes a
  PreToolUse hook surface to invoke it.

## MCP-governed-only (honest degrade)

If Codex has **no** PreToolUse hook surface, it runs **MCP-governed-only**: the
MCP server's governed handlers (`uacp_state_write`, `uacp_doc_write`, …) remain the
authoritative containment for all governed writes, and the defense-in-depth
PreToolUse shim is simply absent. This is an honest degrade, not a gap in
governance — the shim was always defense-in-depth atop the authoritative MCP
handlers (see [`../shared/README.md`](../shared/README.md) and ADR-0019), so a
runtime without a hook surface loses only the extra accidental-corruption boundary,
not the authoritative one.

This file does **not** invent a Codex hook mechanism. If/when Codex gains a
PreToolUse surface, wiring it is the same pattern as Kimi: point it at
`runtime-adapters/shared/guardian_pretooluse.py` (see
[`../kimi/README.md`](../kimi/README.md) for the shape of a manual hook
registration).
