# Bridge: Codex

Reference adapter for Codex multi-agent review. Part of the Deep Skills Suite bridge layer.

## What is this?

A **reference document** read by any orchestrating skill via the `Read` tool. Instructions are embedded into Task agent prompts for bridge execution.

## Connection Methods

| Priority | Method | When Available |
|----------|--------|---------------|
| 1 (preferred) | MCP server (`mcp__codex__codex`) | `codex` entry in `.mcp.json` |
| 2 (fallback) | CLI (`codex exec`) | `which codex` + auth + feature flag |
| — | Advisory + setup | Neither configured |

## MCP Server Setup (Auto or Manual)

The Codex MCP server exposes `codex` and `codex-reply` tools. The orchestrator can set it up automatically by writing to `.mcp.json`:

```json
{
  "mcpServers": {
    "codex": {
      "command": "npx",
      "args": ["-y", "codex", "mcp-server"]
    }
  }
}
```

Requires: Node.js 18+ and npx. No separate CLI install needed.

## Pre-Flight Checks

The bridge runs checks in this order and **halts with an interactive advisory** if any fail — it does not silently skip:

1. **MCP configured?** → use MCP path (no further checks needed)
2. **CLI installed?** (`which codex`)
3. **Authenticated?** (`codex login status`)
4. **Multi-agent enabled?** (`codex features list`)

If the user is not configured, options presented:
- **Set up MCP server automatically** (orchestrator writes `.mcp.json`)
- **Install CLI** (shown command)
- **Skip this bridge**
- **Abort the entire review**

## Multi-Agent Feature

Codex's native multi-agent capability spawns one sub-agent per domain in parallel. This requires:

```toml
# ~/.codex/config.toml
[features]
multi_agent = true
```

Enable via: `codex features enable multi_agent`

## Key CLI Flags (for reference)

| Flag | Value | Purpose |
|------|-------|---------|
| `codex exec` | — | Non-interactive mode (not bare `codex`) |
| `--sandbox` | `read-only` | Analysis only — no file writes |
| `--ask-for-approval` | `never` | No interactive prompts |
| `--json` | — | JSON event stream output |
| `--output-last-message` | path | Capture final response |
| `--ephemeral` | — | No session persistence |

## Status Values

Unlike other bridges, Codex uses four statuses: `COMPLETED`, `SKIPPED`, `HALTED` (needs user input), `ABORTED` (user stopped review).

## Consumed by

Any orchestrating skill (e.g., `deep-council`, `deep-review`, `deep-audit`, or custom skills)
