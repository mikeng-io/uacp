# Codex CLI Reference

Complete reference for Codex CLI and MCP server usage. Embedded here so orchestrators have an authoritative, offline source — no external lookups required.

---

## Invocation Modes

| Mode | Command | When to Use |
|------|---------|-------------|
| Non-interactive exec | `codex exec "prompt"` | Scripted/programmatic use |
| Interactive TUI | `codex` | Terminal UI — do NOT use programmatically |
| MCP server | `codex mcp-server` | Expose Codex as MCP server |

**Always use `codex exec` for programmatic dispatch.** Bare `codex` opens the TUI and cannot be scripted.

---

## `codex exec` — All Flags

| Flag | Values | Default | Purpose |
|------|--------|---------|---------|
| (message) | string | required | Prompt — first positional argument |
| `--sandbox`, `-s` | `read-only`, `workspace-write`, `full` | `workspace-write` | Filesystem access level |
| `--ask-for-approval`, `-a` | `never`, `on-write`, `always` | `on-write` | When to pause for user approval |
| `--json` | flag | off | Emit newline-delimited JSON event stream |
| `--output-last-message` | path | none | Write final assistant response to file |
| `--ephemeral` | flag | off | Skip disk persistence (no session stored) |
| `--skip-git-repo-check` | flag | off | Allow execution outside git repos |
| `--model`, `-m` | model name | server default | Model override (check latest via `codex models list`) |
| `--profile`, `-p` | string | none | Load named config profile |
| `--config`, `-c` | `key=value` | none | Inline config override (repeatable) |
| `--reasoning-effort` | `medium`, `high`, `xhigh` | `medium` | Reasoning depth for reasoning models |
| `--session` | session ID | none | Resume an existing session |
| `--title` | string | none | Name for the session |

> **Note:** The exact flag name for reasoning effort may vary — check `codex exec --help` for the current version.

---

## `codex models list` — Model Discovery

```bash
codex models list
```

Returns available models. Always check this at runtime — never hardcode a model name.

---

## Authentication

```bash
codex login              # Browser OAuth (interactive)
codex login --device-auth   # Device code flow (headless/CI)
codex login status       # Check authentication status (exit 0 = authenticated)
codex logout             # Remove stored credentials
```

---

## Multi-Agent Feature

```bash
codex features list                       # Show all features and their status
codex features enable multi_agent         # Enable (persists to ~/.codex/config.toml)
codex features disable multi_agent        # Disable
```

Manual config (equivalent):

```toml
# ~/.codex/config.toml
[features]
multi_agent = true
```

---

## MCP Server

```bash
codex mcp-server    # Start Codex as an MCP server
```

Or via npx (no install required):

```bash
npx -y codex mcp-server
```

`.mcp.json` configuration:

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

**Exposed MCP tools:**

| Tool | Purpose |
|------|---------|
| `codex` (mcp__codex__codex) | Start a Codex session |
| `codex-reply` (mcp__codex__codex-reply) | Continue an existing session |

**`codex` tool parameters:**

| Parameter | Values | Purpose |
|-----------|--------|---------|
| `prompt` | string | Prompt content |
| `approval-policy` | `never`, `on-write`, `always` | Approval mode |
| `sandbox` | `read-only`, `workspace-write` | Filesystem access |
| `model` | model name | Model override |
| `reasoning` | `medium`, `high`, `xhigh` | Reasoning depth |
| `base-instructions` | string | Custom system instructions |

**`codex-reply` tool parameters:**

| Parameter | Values | Purpose |
|-----------|--------|---------|
| `prompt` | string | Follow-up prompt |
| `threadId` | string | Thread ID from initial `codex` call |

`threadId` is available in the response as `structuredContent.threadId`.

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | CLI error |
| 124 | Timeout (shell `timeout` wrapper) |

---

## Installation

```bash
npm install -g @openai/codex
# or
npx -y codex   # without global install
```
