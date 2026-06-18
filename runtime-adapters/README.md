# Installing the UACP Plugin

UACP ships as a plugin for both **Claude Code** and **Kimi Code** — skills + an
MCP governed-tools server. Claude Code additionally bundles the Guardian
PreToolUse hook automatically; on Kimi the hook is a one-time config edit. The
Claude Code steps are first; for Kimi see [Kimi Code](#kimi-code).

## Prerequisites

- Claude Code (`claude --version`) and/or Kimi Code installed.
- Python 3.11+ available as `python3`.
- The UACP repository cloned or the GitHub repo URL to hand.

## Claude Code — install from the marketplace

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
claude plugin details uacp   # lists all 17 skills + hook + MCP server
```

## MCP server setup

The bundled MCP server (`runtime-adapters/mcp/uacp_mcp_server.py`) requires the
`[mcp]` extra. Install it once inside the plugin directory:

```bash
cd /path/to/uacp
pip install -e ".[mcp]"
```

Claude Code passes `CLAUDE_PLUGIN_ROOT` to the server at runtime, so no additional
path configuration is needed after installation.

## Enforcement

Two enforcement layers activate automatically once the plugin is installed:

| Layer | Mechanism | What it does |
|---|---|---|
| Guardian (primary) | MCP governed handlers (`uacp_state_write`, `uacp_doc_write`, …) | Path-bounded, authoritative containment for all governed writes |
| PreToolUse hook (defense-in-depth) | `hooks/hooks.json` → `runtime-adapters/hooks/guardian_pretooluse.py` | Stops raw host `Write`/`Bash` calls before dispatch |

The hook is registered by `plugin.json → "hooks": "./hooks/hooks.json"` and
executes on every tool call (`matcher: "*"`). It fails open: if the hook crashes,
the call proceeds, because the MCP governed handlers provide the authoritative
containment.

(That auto-bundling is Claude-Code-specific. On Kimi the hook is installed
manually — see [Kimi Code](#kimi-code).)

## Verifying the install

```bash
# Run the static readiness smoke test (no claude CLI required).
pytest tests/unit/skills/test_cc_install_readiness.py -q
```

All static checks should pass. If `claude` is on `PATH`, the real CLI tests also
run and perform an actual `marketplace add` + `plugin install` + cleanup cycle.

## Updating

```bash
claude plugin update uacp
```

## Uninstalling

```bash
claude plugin uninstall uacp
claude plugin marketplace remove uacp   # if you no longer need the marketplace entry
```

## Kimi Code

Kimi Code installs the plugin **natively from GitHub** — this wires up the 17
skills + the MCP governed-tools server. (It does *not* carry the enforcement
hook: Kimi's plugin manifest ignores a `hooks` field — that's a one-time config
edit, below.) In the Kimi Code TUI, use a full HTTPS GitHub URL (shorthand like
`owner/repo` is not accepted):

```text
# Install the plugin from GitHub (latest release, else default branch):
/plugins install https://github.com/mikeng-io/uacp

# A plugin's MCP servers start only in a NEW session — enable + restart:
/plugins mcp enable uacp uacp
/new
```

The MCP server needs the `[mcp]` extra installed in the clone Kimi created
(`pip install -e ".[mcp]"` in the plugin directory).

**Enforcement (one-time manual step).** The Guardian PreToolUse gate cannot ride
in the Kimi plugin, so add it to `~/.kimi-code/config.toml` yourself — see
[hooks/README.md → Kimi Code](hooks/README.md#kimi-code) for the `[[hooks]]`
block. There is no install script, by design.
