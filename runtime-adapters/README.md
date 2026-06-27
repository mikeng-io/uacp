# Runtime adapters

UACP is runtime-neutral; this directory is where it meets a concrete host. It is
organized **by runtime**, with a `shared/` layer for the logic that is identical
across runtimes (see [ADR-0020](../docs/architecture/0020-runtime-adapters-regroup-by-runtime.md)).

## Layout

| Directory | Axis | Contents |
|---|---|---|
| `shared/` | shared logic | The cross-runtime PreToolUse Guardian shim (`guardian_pretooluse.py`) — identical across runtimes; per-runtime wiring lives in each runtime dir. |
| `mcp/` | shared logic | The one MCP governed-tools server (`uacp_mcp_server.py`) — all runtimes register the same server. |
| `claude/` | per-runtime wiring | Claude Code wiring: the SessionStart `UACP.md` injector + the `hooks.json` manifest registering both hooks (loaded via plugin.json's explicit `hooks` pointer). |
| `kimi/` | per-runtime wiring | Kimi Code wiring: reuses `shared/` + `mcp/`; the PreToolUse shim is a manual `~/.kimi-code/config.toml` paste. |
| `codex/` | per-runtime wiring | Codex wiring: reuses `shared/` + `mcp/`; MCP-governed-only if it has no PreToolUse hook surface (honest degrade). |
| `hermes/` | per-runtime wiring | The existing Hermes plugins (`uacp_guardian`, `thread_title_sync`) — the native Hermes adapter path. |

**Shared logic vs per-runtime wiring.** The *behavior* (the `.uacp/` PreToolUse
predicate, the governed-tools server) is written once in `shared/` and `mcp/`. The
*wiring* — how a given host discovers and invokes that behavior — differs per host
(a plugin manifest, a `config.toml` paste, an MCP registration) and lives in the
runtime's own directory. Adding a runtime is therefore a thin per-runtime dir that
reuses `shared/` + `mcp/`; a runtime with no hook surface degrades to
MCP-governed-only. The runtime-neutral kernel
(`skills/uacp-core/scripts/hook_kernel.py`) stays neutral — no host names leak into
it.

Per-runtime install + enforcement detail lives in each runtime's README:
[`claude/`](claude/README.md) · [`kimi/`](kimi/README.md) ·
[`codex/`](codex/README.md) · [`shared/`](shared/README.md) (the shim).

The bundled **Serena** read-only LSP overlay (registered in each plugin manifest's
`mcpServers`) is documented in [`serena.md`](serena.md).

## Installing the UACP plugin

UACP ships as a plugin for both **Claude Code** and **Kimi Code** — skills + an
MCP governed-tools server. Claude Code additionally bundles the Guardian
PreToolUse hook automatically; on Kimi the hook is a one-time config edit.

### Prerequisites

- Claude Code (`claude --version`) and/or Kimi Code installed.
- Python 3.11+ available as `python3`.
- [`uv`](https://docs.astral.sh/uv/) on `PATH` — the MCP governed-tools server
  self-provisions its Python dependencies through `uv run` (see
  [MCP server setup](#mcp-server-setup)). This is the only host prerequisite for
  the MCP server; if `uv` is absent, skills and the Guardian hook still load — only
  the governed-tools server fails to start.
- The UACP repository cloned or the GitHub repo URL to hand.

### Claude Code — install from the marketplace

```bash
# 1. Register the UACP marketplace (do this once per machine).
claude plugin marketplace add mikeng-io/uacp

# 2. Install the uacp plugin from that marketplace.
claude plugin install uacp@uacp
```

You can also install from a local clone (useful during development):

```bash
claude plugin marketplace add /path/to/uacp   # add local clone as marketplace
claude plugin install uacp@uacp
```

Confirm the install:

```bash
claude plugin details uacp   # lists all skills + hooks + MCP server
```

Claude-Code-specific hook wiring (SessionStart injector + PreToolUse shim) is
documented in [`claude/README.md`](claude/README.md).

### MCP server setup

No manual step is required. The bundled MCP server
(`runtime-adapters/mcp/uacp_mcp_server.py`) is declared in
`.claude-plugin/plugin.json` under `mcpServers`, launched via:

```jsonc
"uacp": {
  "command": "uv",
  "args": ["run", "--no-project",
           "--with", "mcp", "--with", "pyyaml", "--with", "pydantic", "--with", "jsonschema",
           "python", "${CLAUDE_PLUGIN_ROOT}/runtime-adapters/mcp/uacp_mcp_server.py"]
}
```

`uv run --no-project --with …` provisions the server's dependencies (`mcp` plus
the kernel's core runtime deps — `pydantic`, `pyyaml`, `jsonschema`) into an
ephemeral, cached environment on launch — so a fresh plugin install needs only
`uv` on `PATH`, no `pip install`. Claude Code passes `CLAUDE_PLUGIN_ROOT` so the
server resolves its own path. (The `--with` set is kept in lockstep with
`pyproject.toml`'s core dependencies by a drift-guard test in
`tests/unit/skills/test_cc_install_readiness.py`.)

For a manual or dev run outside the plugin, install the extra instead:
`pip install -e ".[mcp]"`.

### Enforcement

Two enforcement layers activate automatically once the plugin is installed on
Claude Code:

| Layer | Mechanism | What it does |
|---|---|---|
| Guardian (primary) | MCP governed handlers (`uacp_state_write`, `uacp_doc_write`, …) | Path-bounded, authoritative containment for all governed writes |
| PreToolUse hook (defense-in-depth) | `runtime-adapters/claude/hooks.json` → `runtime-adapters/shared/guardian_pretooluse.py` | Stops raw host `Write`/`Edit` calls into `.uacp/` before dispatch |

The hook is registered by `plugin.json → "hooks": "./runtime-adapters/claude/hooks.json"`
(an explicit pointer; CC does not require hooks.json at the plugin root) and
executes on every tool call (`matcher: "*"`). It fails open: if the hook crashes,
the call proceeds, because the MCP governed handlers provide the authoritative
containment. (That pointer-based bundling is Claude-Code-specific. On Kimi the hook
is installed manually — see [`kimi/README.md`](kimi/README.md).)

### Verifying the install

```bash
# Run the static readiness smoke test (no claude CLI required).
pytest tests/unit/skills/test_cc_install_readiness.py -q
```

All static checks should pass. If `claude` is on `PATH`, the real CLI tests also
run and perform an actual `marketplace add` + `plugin install` + cleanup cycle.

### Updating / uninstalling (Claude Code)

```bash
claude plugin update uacp
claude plugin uninstall uacp
claude plugin marketplace remove uacp   # if you no longer need the marketplace entry
```

### Kimi Code

Kimi installs the skills + MCP server natively from GitHub, and the PreToolUse
gate is a one-time `~/.kimi-code/config.toml` paste. Full steps:
[`kimi/README.md`](kimi/README.md).
