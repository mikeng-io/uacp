# Claude Code CLI Reference

Complete reference for `claude` CLI non-interactive usage. Used when bridge-claude runs via an external executor (OpenCode, Codex, Gemini, or any agent that can shell out to `claude`).

---

## Non-Interactive Mode

```bash
claude -p "prompt"
```

The `-p` flag runs Claude non-interactively without opening an interactive session.

---

## Key Flags

| Flag | Values | Purpose |
|------|--------|---------|
| `-p`, `--print` | string | Prompt string — enables non-interactive mode |
| `--output-format` | `text`, `json`, `stream-json` | Output format |
| `--allowedTools` | comma-separated tool names | Restrict available tools |
| `--continue` | — | Resume most recent session |
| `--resume` | session ID | Resume a specific session |
| `--model` | model ID | Override model |
| `--verbose` | — | Debug output (remove in production) |
| `--dangerously-skip-permissions` | — | Skip all permission checks (use in sandboxed env only) |

---

## Output Formats

| Format | Description | Use Case |
|--------|-------------|---------|
| `text` | Plain text (default) | Human-readable output |
| `json` | Structured JSON result | Programmatic parsing |
| `stream-json` | Streaming JSON events | Real-time processing, long tasks |

---

## Tool Scoping for Read-Only Analysis

```bash
claude -p "{prompt}" \
  --output-format json \
  --allowedTools "Read,Grep,Glob,Bash(ls *),Bash(cat *)"
```

Restricts Claude to reading files only — appropriate for review, analysis, planning tasks where no writes should occur.

---

## Piping Input

```bash
# Pipe file contents as context
cat error.log | claude -p "Analyze this log for errors"

# Pipe from another command
git diff | claude -p "Summarize what changed"
```

---

## Agent Teams (Claude Code native, not CLI-invocable)

Agent Teams require `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in environment and are only available when Claude Code is the executor. They cannot be triggered via `claude -p`.

Enable in `settings.json`:
```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

---

## Sub-Agents (Custom)

Define specialized sub-agents in `.claude/agents/`:

```markdown
---
name: security-reviewer
description: Reviews code for security vulnerabilities
tools: Read, Grep, Glob, Bash
model: opus
---
You are a security engineer. Review for injection vulnerabilities,
auth flaws, secrets in code, and insecure data handling.
```

Invoke: `"Use a security-reviewer subagent to analyze src/auth/"`

---

## Anthropic API (Fallback)

When `claude` CLI is not available, fall back to the Anthropic API directly:

```bash
# Discover latest model at runtime
CLAUDE_MODEL=$(curl -s -H "x-api-key: $ANTHROPIC_API_KEY" \
  https://api.anthropic.com/v1/models \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])")

curl -s -X POST https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"$CLAUDE_MODEL\",
    \"max_tokens\": 8096,
    \"messages\": [{\"role\": \"user\", \"content\": \"$PROMPT\"}]
  }"
```

---

## Installation

```bash
# Via npm
npm install -g @anthropic-ai/claude-code

# Check version
claude --version
```
