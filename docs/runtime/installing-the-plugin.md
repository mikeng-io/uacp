---
type: guide
title: Installing the UACP Plugin in Claude Code
description: Step-by-step guide to installing UACP as a Claude Code plugin via the marketplace, including MCP server setup and enforcement notes.
tags: [install, plugin, claude-code, marketplace, mcp, guardian]
timestamp: 2026-06-18
---

# Installing the UACP Plugin in Claude Code

UACP ships as a first-class Claude Code plugin. Installing it wires up 17 skills,
the MCP governed-handler server, and the Guardian PreToolUse hook in one step.

## Prerequisites

- Claude Code installed and on `PATH` (`claude --version`).
- Python 3.11+ available as `python3`.
- The UACP repository cloned or the GitHub repo URL to hand.

## Install from the GitHub marketplace

```bash
# 1. Register the UACP marketplace (do this once per machine).
claude plugin marketplace add nortrix-labs/uacp

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

For Kimi Code, use the Kimi installer documented in
[cc-kimi-pretooluse-hook.md](cc-kimi-pretooluse-hook.md).

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
