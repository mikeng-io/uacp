# Bridge: Gemini (Google) — uacp-bridge reference

*Per-runtime reference for [uacp-bridge](../SKILL.md). Depends on: uacp-bridge, the domain registry (uacp-core/references/domains/).*

---

## Bridge Identity

```yaml
bridge: gemini
model_family: google/gemini
availability: conditional
connection_preference:
  1: native-dispatch  # Executor is Gemini CLI — Gemini subagents (enableAgents)
  2: cli              # Any other executor — gemini -p
  3: skip             # Neither — return SKIPPED (non-blocking)
```

Terminal failure state: **SKIPPED only** — this bridge has no HALT path. If Gemini is unavailable or auth fails, return SKIPPED and continue. Never block the calling orchestrator.

---

## Configuration Reference

Parameters this bridge reads from `config/uacp.toml` at runtime:

| Parameter | Section | Type | Default | Description |
|-----------|---------|------|---------|-------------|
| `enabled` | `[bridges.gemini]` | boolean | `true` | Whether this bridge is active. If `false`, the orchestrator skips it. |
| `timeout_multiplier` | `[bridges.gemini]` | float | `1.0` | Multiplier applied to the uacp-bridge base timeout estimate. No surcharge for Gemini. |

**Not read from TOML** (intrinsic to bridge implementation):
- `connection_preference` — defined in this file only
- `subagent_mode` — auto-detected via `.gemini/settings.json` (`experimental.enableAgents`)

---

## Tier Resolution

Gemini bridge resolves the model alias from `config/uacp.toml` `[models]` in `UACP_ROOT`. The tier mapping lives **only** in `uacp.toml` — this file does not hardcode it.

The general tier resolution protocol is defined in [uacp-bridge/SKILL.md](../SKILL.md). Gemini-specific steps:

1. Read `UACP_ROOT/config/uacp.toml` `[models]` section
2. Look up `[models.tier_mappings.gemini.{tier}]` → get `alias` + `reasoning`
3. Look up `[models.providers.google.models.{alias}]` → `concrete_id` → get resolved model ID

The alias is stable; the `concrete_id` is updated in the registry when Google releases new models. No bridge reference changes required.

**Override via `bridge_input.tier`:** If the council assigns a specific tier, use it directly. If absent, derive from `task_type` + `intensity` per uacp-bridge rules (see [uacp-bridge/SKILL.md](../SKILL.md)).

---

## Pre-Flight — Connection Detection

### Check A: Native Dispatch?

If the executor is Gemini CLI with subagent support enabled, this is the preferred path — spawn specialized Gemini subagents rather than shelling out to the CLI.

```bash
# Check if subagents are enabled in project settings
cat .gemini/settings.json 2>/dev/null | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('experimental',{}).get('enableAgents', False))"

# Also check user-level settings
cat ~/.gemini/settings.json 2>/dev/null | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('experimental',{}).get('enableAgents', False))"
```

If `True` and the current executor is Gemini CLI → **use native dispatch** (subagent path in Subagent Mode section).

If executor is not Gemini, or `enableAgents` is `false` or missing → proceed to Check B.

---

### Check B: CLI Installed?

```bash
which gemini
```

If found → proceed to Check C.

If not found → return immediately:

```json
{
  "bridge": "gemini",
  "status": "SKIPPED",
  "skip_reason": "gemini CLI not available (which gemini returned empty)",
  "outputs": [],
  "verdict": null
}
```

Never fail or block — SKIPPED is a valid bridge outcome.

---

### Check C: Auth / Quota Probe

A gemini CLI that is installed but has an expired token or exhausted quota passes Check B and then fails silently at execution time. Catch this at availability check instead:

```bash
# Lightweight probe — verifies auth without a full execution
gemini --version 2>/dev/null
# Or: a minimal non-interactive list/ping command if available
```

If the probe exits non-zero or returns an auth error → return:

```json
{
  "bridge": "gemini",
  "status": "SKIPPED",
  "skip_reason": "gemini CLI auth probe failed: {stderr}",
  "outputs": [],
  "verdict": null
}
```

If the probe succeeds → **use CLI path** (Execution section).

---

## Execution

Build the prompt using the Agent Prompt Template from [uacp-bridge/SKILL.md](../SKILL.md), adapting to `task_type`. Calculate timeout using the uacp-bridge formula with `timeout_multiplier = 1.0` (no surcharge for Gemini).

Resolve tier and model before invocation:
```bash
# 1. Determine tier (from bridge_input.tier or derive from task_type + intensity)
# 2. Read UACP_ROOT/config/uacp.toml [models] section
# 3. Look up [models.tier_mappings.gemini.{tier}] → get alias + reasoning
# 4. Look up [models.providers.google.models.{alias}].concrete_id → get resolved model ID
# 5. Set RESOLVED_MODEL
```

```bash
PROMPT="{constructed_prompt}"

# run_to = OS-portable timeout helper from uacp-bridge/SKILL.md. Run with cwd at the provisioned
# review sandbox (Review Containment). `--approval-mode plan` = read_only_enforcement: tool-mode.
run_to {final_timeout} gemini -p "$PROMPT" \
  --model ${RESOLVED_MODEL} \
  --approval-mode plan \
  --output-format json
```

**SAFETY INVARIANT — `--approval-mode`:**
- `--approval-mode plan` for **all non-implementation task types** (review, analysis, research, audit, planning)
- `--approval-mode auto_edit` **only** for `task_type = implementation`

This prevents Gemini from auto-applying file edits during review/audit/research tasks. Never omit `--approval-mode` or default to `auto_edit` for non-implementation work.

**FLAG TRAP: `--output-format json` is correct. `-o json` is WRONG** — always use the long form `--output-format json` to ensure structured output for parsing.

Error handling:
- Exit code 0 with JSON → parse and return findings
- Exit code 124 (timeout) → return SKIPPED with reason `timeout_after_{n}s`
- Other exit codes → return SKIPPED with reason `gemini CLI error: {stderr}`
- Invalid JSON output → attempt to extract structured content, else SKIPPED

After execution, run the uacp-bridge Post-Analysis Protocol (see [uacp-bridge/SKILL.md](../SKILL.md)). Gemini uses **stateless context passing** between rounds — embed the full previous-round outputs and context packet in each subsequent `gemini -p` call. There is no session continuity between separate CLI invocations.

For `standard` and `thorough` intensity, construct the Round 2 prompt as:

```
{Agent Prompt Template for this role}

--- ROUND 2 CONTEXT ---
Previous round findings:
{JSON of all Round 1 outputs}

{context packet: open_challenges directed at this domain, synthesis}
```

The literal `--- ROUND 2 CONTEXT ---` header is a delimiter for prompt-construction logic that may pattern-match on it. Preserve it exactly.

**Never block the calling orchestrator** — always return a report (even if SKIPPED).

---

## Subagent Mode

Gemini CLI supports custom subagents for parallel domain dispatch when `experimental.enableAgents` is set in `.gemini/settings.json`.

```bash
# Confirm subagents are enabled
cat .gemini/settings.json 2>/dev/null | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('experimental',{}).get('enableAgents', False))"
```

- If `true` → spawn one subagent per domain; run consolidation pass after all complete
- If `false` or missing → run standard single Gemini call covering all domains

Subagent mode is a **progressive enhancement** — single-call fallback is valid, not degraded. Record `subagent_mode: true/false` in output regardless of path taken.

---

## Output

For the full Output Schema, see [uacp-bridge/SKILL.md](../SKILL.md). Bridge-specific fields added by this adapter:

```json
{
  "bridge": "gemini",
  "model_family": "google/gemini",
  "connection_used": "native-dispatch | cli",
  "subagent_mode": true,
  "tier": 2,
  "resolved_model": "gemini-2.5-pro"
}
```

Output ID prefix: `G` (e.g., `G001`, `G002`).

---

## CLI Reference

*Last verified: 2026-06-07*

### Invocation Modes

| Mode | Command | When to Use |
|------|---------|-------------|
| Prompt flag | `gemini -p "prompt"` | Scripted/programmatic use |
| Interactive | `gemini` | Interactive session |

---

### `gemini` — Key Flags

| Flag | Values | Default | Purpose |
|------|--------|---------|---------|
| `-p`, `--prompt` | string | none | Prompt string (non-interactive) |
| `--approval-mode` | `plan`, `auto`, `none` | `auto` | Tool approval policy |
| `--output-format` | `json`, `text`, `markdown` | `text` | Output format — use `--output-format json`, NOT `-o json` |
| `-y`, `--yolo` | flag | off | Skip all approval prompts (use with caution) |
| `-m`, `--model` | model name | latest | Model override |
| `--sandbox` | flag | off | Run in sandboxed mode |
| `--debug` | flag | off | Enable debug logging |

**For bridge use:** `--approval-mode plan --output-format json` is the standard invocation.

---

### Subagent Capability

Gemini CLI supports custom subagents — specialized agents that handle specific tasks with their own tools and context windows.

#### Enable subagents

```json
// ~/.gemini/settings.json or .gemini/settings.json
{
  "experimental": {
    "enableAgents": true
  }
}
```

#### Built-in agents

| Agent | Tool name | Purpose |
|-------|-----------|---------|
| Codebase Investigator | `codebase_investigator` | Analyzes codebases, reverse-engineers dependencies |
| CLI Help | `cli_help` | Gemini CLI knowledge |
| Generalist | `generalist_agent` | Routes tasks to appropriate subagents |
| Browser | `browser_agent` | Web automation via Chrome DevTools |

#### Custom subagent definition

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

### Authentication

```bash
gemini auth login      # Authenticate (Google account)
gemini auth status     # Check auth status
gemini auth logout     # Remove credentials
```

---

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| Non-zero | Error — check stderr |
| 124 | Timeout (shell `timeout` wrapper) |

---

### Installation

```bash
npm install -g @google/gemini-cli
# or
brew install gemini-cli
```
