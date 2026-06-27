# Kimi Code runtime adapter

Kimi Code **reuses** the shared logic — it ships no Kimi-specific code:

- the **MCP governed-tools server** `runtime-adapters/mcp/uacp_mcp_server.py`
  (one server, all runtimes), and
- the **shared PreToolUse Guardian shim**
  `runtime-adapters/shared/guardian_pretooluse.py --profile kimi`
  (documented in [`../shared/README.md`](../shared/README.md); the `--profile`
  value does not change the predicate — host tool names are identical across
  Claude Code and Kimi Code).

## Install (skills + MCP server, native from GitHub)

Kimi Code installs the plugin **natively from GitHub** — this wires up the skills
+ the MCP governed-tools server. (It does *not* carry the enforcement hook: Kimi's
plugin manifest ignores a `hooks` field — that is the one-time config edit below.)
In the Kimi Code TUI, use a full HTTPS GitHub URL (shorthand like `owner/repo` is
not accepted):

```text
# Install the plugin from GitHub (latest release, else default branch):
/plugins install https://github.com/mikeng-io/uacp

# A plugin's MCP servers start only in a NEW session — enable + restart.
# Enable BOTH the governance server (uacp) and the Serena LSP server (serena):
/plugins mcp enable uacp uacp
/plugins mcp enable uacp serena
/new
```

The MCP server needs the `[mcp]` extra installed in the clone Kimi created
(`pip install -e ".[mcp]"` in the plugin directory).

## Enforcement (one-time manual hook paste)

The Guardian PreToolUse gate **cannot ride in the Kimi plugin** — Kimi's plugin
manifest ignores a `hooks` field — so it is a one-time edit to
`~/.kimi-code/config.toml`. Add this `[[hooks]]` block, replacing `<abs>` with the
absolute path to your clone:

```toml
[[hooks]]
event = "PreToolUse"
matcher = "*"
command = "python3 <abs>/runtime-adapters/shared/guardian_pretooluse.py --profile kimi"
timeout = 10
```

Then start a new session (`/new`). There is no install script — this is a single
documented paste, by design (the gate can't ride in the plugin).

> SessionStart cognition injection (the `UACP.md` preamble) is **Claude-Code-only
> today** — Kimi would need its own session-start hook to inject it (a follow-up,
> analogous to this paste). See [`../claude/README.md`](../claude/README.md).
