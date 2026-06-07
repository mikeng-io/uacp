# Gemini CLI Reference

Complete reference for Gemini CLI usage including subagent capability. Embedded here so orchestrators have an authoritative, offline source — no external lookups required.

---

## Invocation Modes

| Mode | Command | When to Use |
|------|---------|-------------|
| Prompt flag | `gemini -p "prompt"` | Scripted/programmatic use |
| Interactive | `gemini` | Interactive session |

---

## `gemini` — Key Flags

| Flag | Values | Default | Purpose |
|------|--------|---------|---------|
| `-p`, `--prompt` | string | none | Prompt string (non-interactive) |
| `--approval-mode` | `plan`, `auto`, `none` | `auto` | Tool approval policy |
| `-o`, `--output-format` | `json`, `text`, `markdown` | `text` | Output format |
| `-y`, `--yolo` | flag | off | Skip all approval prompts (use with caution) |
| `-m`, `--model` | model name | latest | Model override |
| `--sandbox` | flag | off | Run in sandboxed mode |
| `--debug` | flag | off | Enable debug logging |

**For bridge use:** `--approval-mode plan -o json` is the standard invocation.

---

## Subagent Capability

Gemini CLI supports custom subagents — specialized agents that handle specific tasks with their own tools and context windows.

### Enable subagents

```json
// ~/.gemini/settings.json or .gemini/settings.json
{
  "experimental": {
    "enableAgents": true
  }
}
```

### Built-in agents

| Agent | Tool name | Purpose |
|-------|-----------|---------|
| Codebase Investigator | `codebase_investigator` | Analyzes codebases, reverse-engineers dependencies |
| CLI Help | `cli_help` | Gemini CLI knowledge |
| Generalist | `generalist_agent` | Routes tasks to appropriate subagents |
| Browser | `browser_agent` | Web automation via Chrome DevTools |

### Custom subagent definition

Custom subagents are Markdown files with YAML frontmatter placed in:
- `.gemini/agents/*.md` — project-level
- `~/.gemini/agents/*.md` — user-level

```markdown
---
name: domain-expert
description: Expert reviewer for security and API domains
tools:
  - read_file
  - search_files
model: gemini-2.5-pro
max_turns: 20
timeout_mins: 5
---

You are a security and API domain expert. Analyze the provided scope for issues...
```

When agents are enabled, the main Gemini session can call a subagent as a tool, delegating the task and receiving its output. This enables parallel domain-expert dispatch similar to Codex multi-agent.

> **Note:** Subagents operate without per-step user confirmation when `enableAgents` is active.

---

## Authentication

```bash
gemini auth login      # Authenticate (Google account)
gemini auth status     # Check auth status
gemini auth logout     # Remove credentials
```

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
npm install -g @google/gemini-cli
# or
brew install gemini-cli
```
