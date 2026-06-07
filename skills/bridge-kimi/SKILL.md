---
name: bridge-kimi
description: Reference adapter for Kimi Code CLI external reviews and execution. Read by orchestrating skills via the Read tool. Defines availability checks, invocation, timeout handling, tier resolution, and bridge-commons output requirements.
location: managed
context: reference
dependencies:
  - bridge-commons
  - domain-registry
---

# Bridge: Kimi Code CLI Adapter

This file is a REFERENCE DOCUMENT. Orchestrating skills read it and embed these instructions into review dispatch prompts. It is not invoked as a standalone skill.

Input schema, output schema, verdict logic, artifact format, tier system, and status semantics are defined in `bridge-commons/SKILL.md`.

## Bridge Identity

```yaml
bridge: kimi
model_family: moonshot/kimi
availability: conditional
connection_preference:
  1: cli
  2: acp-server   # Agent Client Protocol over stdio
  3: skip
```

---

## Tier Resolution

Kimi bridge resolves the model from `config/uacp.toml` using the bridge-commons tier system.

### Default tier mapping (from `config/uacp.toml`)

| Tier | Model alias | Kimi CLI equivalent |
|------|-------------|---------------------|
| 0 | kimi-default | `-m kimi-for-coding` (or omit, uses default) |
| 1 | kimi-default | `-m kimi-for-coding` |
| 2 | kimi-default | `-m kimi-for-coding` |
| 3 | kimi-default | `-m kimi-for-coding` |
| 4 | kimi-default | `-m kimi-for-coding` |

**Current limitation:** Kimi Code currently offers one primary model (`kimi-for-coding` — Kimi K2.6 Thinking). All tiers map to the same model. The tier system is still enforced for consistency and future-proofing — when Moonshot releases additional models, update `config/uacp.toml` only.

**Model alias resolution:** Look up `bridges.kimi.model_aliases` in `config/uacp.toml`.

**Override via `bridge_input.tier`:** If the council assigns a specific tier, use it directly. If absent, derive from `task_type` + `intensity` per bridge-commons rules.

---

## Pre-Flight

### 1. Resolve Kimi binary path

Check in priority order:

1. **UACP config** — `config/uacp.toml` → `bridges.kimi.path`
2. **Environment** — `KIMI_CODE_CLI_PATH` env var
3. **`$PATH` resolution** — `which kimi`
4. **Common locations**:
   - `$HOME/.kimi-code/bin/kimi`
   - `$HOME/.local/bin/kimi`
   - `/usr/local/bin/kimi`

### 2. CLI availability check

```bash
test -x "<resolved-kimi-path>" && "<resolved-kimi-path>" --version
```

If unavailable, return `SKIPPED` with `skip_reason: "kimi CLI not available"`.

### 3. Model resolution

```yaml
priority:
  1: UACP config → config/uacp.toml → bridges.kimi.model_aliases
  2: Environment → KIMI_CODE_MODEL
  3: CLI default → omit --model flag (uses config.toml default_model)
```

Resolve tier first, then look up the model alias:
```bash
# Determine tier (from bridge_input.tier or derive from task_type + intensity)
# Look up bridges.kimi.tiers.{tier} in config/uacp.toml
# Resolve model alias via bridges.kimi.model_aliases
# Set RESOLVED_MODEL
```

Valid model aliases depend on the Kimi Code version. Check available models via:
```bash
kimi provider list
```

### 4. Auth check

Kimi Code uses OAuth device-code flow. Check login status:
```bash
kimi login status 2>/dev/null || echo "not_logged_in"
```

If not authenticated → return `HALTED` with advisory to run `kimi login`.

---

## Execution

### Non-interactive prompt mode (primary)

Run one prompt and print the response:

```bash
"<resolved-kimi-path>" \
  -p "$PROMPT" \
  ${RESOLVED_MODEL:+-m "$RESOLVED_MODEL"} \
  --output-format json
```

For auto-approval of actions (implementation tasks):
```bash
"<resolved-kimi-path>" \
  -p "$PROMPT" \
  ${RESOLVED_MODEL:+-m "$RESOLVED_MODEL"} \
  --output-format json \
  -y
```

For plan mode (read-only analysis, safer default):
```bash
"<resolved-kimi-path>" \
  -p "$PROMPT" \
  ${RESOLVED_MODEL:+-m "$RESOLVED_MODEL"} \
  --output-format json \
  --plan
```

### ACP Server mode (advanced)

Kimi Code can run as an ACP server over stdio:
```bash
kimi acp
```

This exposes the Agent Client Protocol for programmatic integration. Use when the orchestrator supports ACP/stdio communication.

### Session continuity

Resume previous session for the working directory:
```bash
kimi -C -p "$PROMPT" --output-format json
```

Or resume specific session:
```bash
kimi -S "$SESSION_ID" -p "$PROMPT" --output-format json
```

## CLI Reference

### Global options

| Flag | Description |
|------|-------------|
| `-V, --version` | Output version number |
| `-S, --session [id]` | Resume session (with ID) or pick interactively (without) |
| `-C, --continue` | Continue previous session for working directory |
| `-y, --yolo` | Automatically approve all actions |
| `--auto` | Start in auto permission mode |
| `-m, --model <model>` | LLM model alias |
| `-p, --prompt <prompt>` | Run one prompt non-interactively |
| `--output-format <format>` | Output format: `text` or `stream-json` |
| `--skills-dir <dir>` | Load skills from directory (repeatable) |
| `--plan` | Start in plan mode |

### Commands

| Command | Description |
|---------|-------------|
| `export [sessionId]` | Export session as ZIP archive |
| `provider` | Manage LLM providers non-interactively |
| `acp [options]` | Run as ACP server over stdio |
| `login` | Authenticate via device-code flow |
| `doctor` | Validate configuration files |
| `migrate` | Migrate from legacy kimi-cli |
| `upgrade` | Upgrade to latest version |

## Error Handling

- Exit code `0` with content: parse findings into bridge-commons output.
- Timeout: return `SKIPPED` with `skip_reason: "timeout_after_<seconds>s"`.
- Empty output: return `SKIPPED` with `skip_reason: "empty_output"`.
- Other non-zero exit: return `SKIPPED` with stderr summary.
- Auth failure: return `HALTED` with `halt_reason: "not_authenticated"`.

Never treat empty output as a completed review.

## Output

Return bridge-commons output with:

```json
{
  "bridge": "kimi",
  "connection_used": "cli",
  "model_family": "moonshot/kimi",
  "tier": 2,
  "resolved_model": "kimi-for-coding"
}
```
