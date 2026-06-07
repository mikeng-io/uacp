# OpenCode CLI & API Reference

Complete reference for OpenCode CLI and HTTP API usage. Embedded here so orchestrators have an authoritative, offline source — no external lookups required.

---

## Invocation Modes

| Mode | Command | When to Use |
|------|---------|-------------|
| Non-interactive run | `opencode run "prompt"` | Scripted/programmatic use |
| Interactive TUI | `opencode` | Terminal UI — do NOT use programmatically |
| HTTP API server | `opencode serve` | Start REST API at `:4096` |

**Always use `opencode run` for programmatic dispatch.** Bare `opencode` opens the TUI.

---

## `opencode run` — All Flags

| Flag | Values | Default | Purpose |
|------|--------|---------|---------|
| (message) | string | required | Prompt — first positional argument |
| `--format`, `-f` | `json`, `text` | `text` | Output format |
| `--model`, `-m` | `provider/model` | server default | Model in `provider/model` format |
| `--agent` | `plan`, `build` | `build` | Agent mode |
| `--file`, `-F` | path | none | Attach file to session |
| `--session`, `-s` | session ID | none | Resume existing session |
| `--title` | string | none | Session name |

**Model format:** `provider/model` — e.g., `anthropic/claude-sonnet-4-20250514`, `openai/gpt-4o`, `google/gemini-2.0-flash`. Omit to use server default.

**Agents:**
- `plan` — read-only, suited for review and analysis (use this for bridge tasks)
- `build` — full tool access

---

## HTTP API

OpenCode exposes a REST API when running as a server.

### Start the server

```bash
opencode serve --port 4096   # Default port 4096
# OPENCODE_PORT env var also accepted
```

OpenAPI spec: `http://localhost:{port}/doc`

### Session management

```bash
# Create session
POST /session
Body: { "title": "...", "agent": "plan" }
Response: { "id": "session-id", ... }

# Send message
POST /session/{id}/message
Body: {
  "content": [{"type": "text", "text": "..."}],
  "model": "provider/model"    # optional
}
Response: streaming event stream

# List sessions
GET /session

# Get session
GET /session/{id}
```

### Authentication (if password set)

```bash
curl -u opencode:$OPENCODE_SERVER_PASSWORD -X POST http://localhost:4096/session ...
```

### Full session+message flow (bash)

```bash
SESSION=$(curl -s -X POST http://localhost:4096/session \
  -H "Content-Type: application/json" \
  -d '{"title": "review", "agent": "plan"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

curl -s -X POST http://localhost:4096/session/$SESSION/message \
  -H "Content-Type: application/json" \
  -d "{\"content\": [{\"type\": \"text\", \"text\": \"$PROMPT\"}]}"
```

---

## Authentication (Provider)

```bash
opencode auth login       # Authenticate a provider (interactive)
opencode auth list        # List authenticated providers
opencode auth logout      # Remove provider authentication
```

**Supported providers:** Anthropic, OpenAI, Google, GLM, Qwen, and others depending on version.

---

## Agents

| Agent | Mode | Best For |
|-------|------|---------|
| `plan` | Read-only | Analysis, review, code inspection |
| `build` | Full tool access | Implementation tasks |

For bridge review tasks, always use `plan`.

---

## Exit Codes (`opencode run`)

| Code | Meaning |
|------|---------|
| 0 | Success |
| Non-zero | Error — check stderr |
| 124 | Timeout (shell `timeout` wrapper) |

---

## Installation

```bash
npm install -g opencode-ai
# or
brew install opencode
```
