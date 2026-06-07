# Kimi Code CLI Reference

Complete reference for Kimi Code CLI usage. Embedded here so orchestrators have an authoritative, offline source — no external lookups required.

---

## Invocation Modes

| Mode | Command | When to Use |
|------|---------|-------------|
| Prompt flag | `kimi -p "prompt"` | Scripted/programmatic use |
| Interactive | `kimi` | Interactive session |
| ACP server | `kimi acp` | Agent Client Protocol integration |

---

## `kimi` — Global Options

| Flag | Values | Default | Purpose |
|------|--------|---------|---------|
| `-V, --version` | — | — | Output version number |
| `-S, --session [id]` | session ID | — | Resume session (with ID) or pick interactively |
| `-C, --continue` | flag | false | Continue previous session for working directory |
| `-y, --yolo` | flag | false | Automatically approve all actions |
| `--auto` | flag | false | Start in auto permission mode |
| `-m, --model <model>` | model alias | config.toml default | LLM model override |
| `-p, --prompt <prompt>` | string | none | Run one prompt non-interactively |
| `--output-format <format>` | `text`, `stream-json` | `text` | Output format for prompt mode |
| `--skills-dir <dir>` | path | [] | Load skills from directory (repeatable) |
| `--plan` | flag | false | Start in plan mode |
| `-h, --help` | — | — | Show help |

**For bridge use:** `kimi -p "prompt" --output-format json` is the standard invocation.
**For implementation tasks:** add `-y` for auto-approval.
**For read-only analysis:** add `--plan` for safer defaults.

---

## Commands

| Command | Description |
|---------|-------------|
| `export [sessionId]` | Export session as ZIP archive |
| `provider` | Manage LLM providers non-interactively |
| `acp [options]` | Run as Agent Client Protocol (ACP) server over stdio |
| `login` | Authenticate via device-code flow |
| `doctor` | Validate configuration files |
| `migrate` | Migrate data from legacy kimi-cli |
| `upgrade` | Upgrade to latest version |

---

## Authentication

```bash
kimi login              # Device-code OAuth flow
kimi login status       # Check auth status
```

Kimi Code uses OAuth — no manual API key management needed for CLI use.

For API access (third-party tools), create an API Key in the Kimi Code console.

---

## Model Aliases

Check available models via:
```bash
kimi provider list
```

Common aliases depend on the Kimi Code version. The default is configured in `~/.kimi-code/config.toml` under `default_model`.

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| Non-zero | Error — check stderr |
| 124 | Timeout (shell `timeout` wrapper) |

---

## Installation

```bash
# macOS / Linux
curl -fsSL https://code.kimi.com/kimi-code/install.sh | bash

# Installs to $HOME/.kimi-code/bin/kimi by default
# Optional env:
#   KIMI_VERSION=0.11.0          # Pin version
#   KIMI_INSTALL_DIR=/usr/local  # Custom install dir
#   KIMI_NO_MODIFY_PATH=1        # Skip PATH update
```

Binary location: `$HOME/.kimi-code/bin/kimi`
