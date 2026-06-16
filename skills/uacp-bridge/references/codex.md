# Bridge: Codex (OpenAI) — uacp-bridge reference

*Per-runtime reference for [uacp-bridge](../SKILL.md). Depends on: uacp-bridge, domain-registry.*

---

## Bridge Identity

```yaml
bridge: codex
model_family: openai/codex
availability: conditional
connection_preference:
  1: native-dispatch  # Executor is Codex — multi-agent dispatch (experimental)
  2: mcp              # Any executor with MCP access — mcp__codex__codex server
  3: cli              # Any other executor — codex exec
  4: halt             # None available — surface advisory, offer setup
```

---

## Configuration Reference

Parameters this bridge reads from `config/uacp.toml` at runtime:

| Parameter | Section | Type | Default | Description |
|-----------|---------|------|---------|-------------|
| `enabled` | `[bridges.codex]` | boolean | `true` | Whether this bridge is active. If `false`, the orchestrator skips it. |
| `timeout_multiplier` | `[bridges.codex]` | float | `1.2` | Multiplier applied to the uacp-bridge base timeout estimate. |

**Not read from TOML** (intrinsic to bridge implementation):
- `connection_preference` — defined in this file only
- `multi_agent_enabled` — auto-detected via `codex features list`; recorded in output for transparency

---

## Tier Resolution

Codex bridge resolves the model alias and reasoning level from `config/uacp.toml` `[models]` in `UACP_ROOT`. The tier mapping lives **only** in `uacp.toml` — this file does not hardcode it.

The general tier resolution protocol is defined in [uacp-bridge/SKILL.md](../SKILL.md). Codex-specific steps:

1. Read `UACP_ROOT/config/uacp.toml` `[models]` section
2. Look up `[models.tier_mappings.codex.{tier}]` → get `alias` + `reasoning`
3. Look up `[models.providers.openai.models.{alias}]` → `concrete_id` → get resolved model ID
4. Apply reasoning level to `--config reasoning-effort`

The alias is stable; the `concrete_id` is updated in the registry when OpenAI releases new models. No bridge reference changes required.

**Reasoning mapping (Codex-specific — maps reasoning level to `--config reasoning-effort` value):**
- `medium` → `--config reasoning-effort=medium`
- `high` → `--config reasoning-effort=high`
- `xhigh` → `--config reasoning-effort=xhigh`

**Override via `bridge_input.tier`:** If the council assigns a specific tier, use it directly. If absent, derive from `task_type` + `intensity` per uacp-bridge rules (see [uacp-bridge/SKILL.md](../SKILL.md)).

**Xhigh Alert (MANDATORY):** When resolved reasoning is `xhigh`, alert the user before proceeding:

```
⚠ Reasoning level: XHIGH
Codex will use maximum reasoning depth for this review.
This increases token usage and may take 2–3× longer than standard.

Continue? (y/n)
```

If user declines → fall back to `high`. Return `resolved_reasoning: "high"` in output.

Silently activating `xhigh` without presenting this prompt is an explicit anti-pattern. Never skip this gate.

---

## Step 1: Pre-Flight — Connection Detection

### Check A: Native Dispatch?

If the executor is Codex CLI with multi-agent support enabled, this is the preferred path — spawn parallel Codex agents rather than routing through MCP or CLI.

```bash
# Check if running inside a Codex execution context
echo ${CODEX_SESSION_ID:+found}

# Check if multi-agent feature is enabled
codex features list 2>/dev/null | grep -q "multi_agent" && echo "enabled"
```

If in a Codex session AND multi-agent is enabled → **use native dispatch** (multi-agent path).

This is an experimental feature. If multi-agent is not enabled, or the executor is not Codex → proceed to Check B.

---

### Check B: MCP Server Configured?

Look for a `codex` entry in the active MCP configuration:

```bash
# Check project-level MCP config
cat .mcp.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('found' if 'codex' in d.get('mcpServers',{}) else 'not-found')" 2>/dev/null

# Or check Claude's global MCP settings
cat ~/.claude.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('found' if 'codex' in str(d) else 'not-found')" 2>/dev/null
```

If found → **use MCP path** (Step 3A). No further pre-flight needed — MCP server handles auth internally.

---

### Check C: CLI Available?

```bash
which codex
```

If found → proceed to Check D.

If not found → **no connection available — go to Step 2 (Advisory)**.

---

### Check D: Authenticated? (CLI path only)

```bash
codex login status
```

Exit code 0 → authenticated. Other → **go to Step 2 (Advisory)** with `reason: not_authenticated`.

---

### Check E: Multi-Agent Feature Enabled? (CLI path only — optional)

```bash
codex features list
```

Look for `multi_agent` marked as enabled.

- If enabled → proceed with **parallel multi-agent dispatch** (one sub-agent per domain)
- If not enabled → proceed in **single-agent mode** (one Codex session reviews all domains together)

Multi-agent is a progressive enhancement. Single-agent mode is a valid fallback — do not halt.

Record `multi_agent_enabled: true/false` in output for caller transparency.

→ **Use CLI path** (Step 3B).

---

## Step 2: Advisory — Halt and Present Options

**Do not skip silently.** Surface the appropriate message to the user and wait for a choice.

### Advisory: MCP Server Not Configured + CLI Not Found

```
⚠ Codex is not connected. This bridge requires either the Codex MCP server
  or the Codex CLI.

Options:
  [1] Set up MCP server automatically
      I will add the Codex MCP server to .mcp.json so future sessions
      use it without any CLI installation needed.
      Requires: Node.js 18+ and npx available.

  [2] Install the Codex CLI
      Run: npm install -g @openai/codex
      Then re-run this review.

  [3] Skip Codex bridge
      Continue the review without Codex. Other available bridges will run.

  [4] Abort
      Stop the entire review.

What would you like to do? (1/2/3/4)
```

**If user chooses [1] — Auto-setup MCP server:**

Write (or merge) into `.mcp.json`:

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

Then verify the server is reachable. If successful → continue with **MCP path (Step 3A)**.
If verification fails → tell the user and offer options [2]/[3]/[4] again.

**If user chooses [2]:** Return `status: HALTED`, `halt_reason: cli_not_installed`. Show install command.

**If user chooses [3]:** Return `status: SKIPPED`, `skip_reason: user_chose_skip`.

**If user chooses [4]:** Return `status: ABORTED`. Calling orchestrator must stop entire review.

---

### Advisory: CLI Found But Not Authenticated

```
⚠ Codex CLI found but not authenticated.

To log in:
  codex login              # Browser OAuth flow (interactive)
  codex login --device-auth   # Device code flow (headless/CI)

After authenticating, re-run this review.

Or:
  [1] Skip Codex bridge and continue
  [2] Abort the entire review
```

Return `status: HALTED`, `halt_reason: not_authenticated`.

---

### Non-Interactive Environments (Automated Pipelines)

If no interactive context is available, return `status: HALTED` with the full advisory text in `halt_message`. Never silently skip in a way that hides a configuration gap.

See [uacp-bridge/SKILL.md](../SKILL.md) for the HALTED→SKIPPED orchestrator conversion policy (non-interactive auto-mode).

---

## Step 3: Build Domain Prompt

### When `multi_agent_enabled: true` — use this coordinator prompt instead of the shared Agent Prompt Template

Codex's multi-agent capability means the prompt is addressed to a **coordinator**, not a single domain expert. Use the following coordinator-framing prompt when in multi-agent mode. In single-agent mode, use the Agent Prompt Template from [uacp-bridge/SKILL.md](../SKILL.md) directly.

```
You are a multi-agent code review coordinator. Spawn one agent per domain
below, run them in parallel using your multi-agent capability, wait for all
to complete, then return a consolidated findings JSON.

Review scope: {review_scope}
Context: {context_summary}
Intensity: {intensity}
Tier: {tier}

Domains to analyze (spawn one agent per domain):
{for each domain:
  "- {domain_name}: focus on {focus_areas from domain-registry}"}

Each agent must return outputs using the schema from uacp-bridge:
{
  "domain": "...",
  "outputs": [
    {
      "severity": "CRITICAL | HIGH | MEDIUM | LOW | INFO",
      "title": "...",
      "description": "...",
      "evidence": "...",
      "action": "..."
    }
  ]
}

After all agents complete, consolidate all findings and return:
{
  "domains_analyzed": [...],
  "outputs": [...],
  "verdict": "PASS | FAIL | CONCERNS"
}
```

In single-agent mode, drop the coordinator framing and use the [uacp-bridge/SKILL.md](../SKILL.md) Agent Prompt Template directly, covering all domains in one prompt.

---

## Timeout Estimation

Use uacp-bridge base timeout table and intensity multiplier (see [uacp-bridge/SKILL.md](../SKILL.md)). Codex multi-agent adds sub-agent spawn overhead — apply a higher base when multi-agent is enabled:

```yaml
# When multi_agent_enabled: true — increase base by 50%
# e.g., 5-20 files: 180s → 270s to account for agent spawn latency
# When multi_agent_enabled: false — use uacp-bridge base times directly
```

The Codex bridge `timeout_multiplier = 1.2` from `[bridges.codex]` is applied on top of the scope/intensity base as defined in [uacp-bridge/SKILL.md](../SKILL.md).

---

## Step 3A: Execute via MCP Server (Preferred)

Use the `codex` MCP tool directly. The MCP server runs `codex mcp-server` and exposes two tools.

### Model Selection — Resolve from Tier

Before calling either MCP or CLI, resolve the model from the tier:

```bash
# 1. Determine tier (from bridge_input.tier or derive from task_type + intensity)
# 2. Read UACP_ROOT/config/uacp.toml [models] section
# 3. Look up [models.tier_mappings.codex.{tier}] → get alias + reasoning
# 4. Look up [models.providers.openai.models.{alias}].concrete_id → get resolved model ID
# 5. Set RESOLVED_MODEL and RESOLVED_REASONING
```

Do NOT hardcode a model name. If model discovery fails, omit the `model` parameter and let the server select its default.

### Tool: `mcp__codex__codex` — Start a session

```
Call: mcp__codex__codex
Parameters:
  prompt:          {constructed_prompt}
  approval-policy: "never"                  # No interactive approval prompts
  sandbox:         "read-only"              # Analysis only — no file writes
  model:           {RESOLVED_MODEL, or omit}
  reasoning:       {RESOLVED_REASONING}     # medium | high | xhigh
```

Capture `structuredContent.threadId` from response for multi-turn use.

### Tool: `mcp__codex__codex-reply` — Continue session (if needed)

```
Call: mcp__codex__codex-reply
Parameters:
  prompt:   "Summarize and consolidate all agent findings into the JSON format specified."
  threadId: {threadId from previous call}
```

The MCP path is **stateful** — the `threadId` maintains full Round 1 history. For subsequent Post-Analysis Protocol rounds, only inject the context packet (not the full previous-round output):

```
Call: mcp__codex__codex-reply
Parameters:
  prompt:   "{role-specific Round N prompt from uacp-bridge context packet}"
  threadId: {threadId from Round 1}
```

Run one `mcp__codex__codex` + N `mcp__codex__codex-reply` calls per role, one role at a time or in parallel sessions.

---

## Step 3B: Execute via CLI (Fallback)

The CLI path is **stateless** — each `codex exec` call is independent. For Post-Analysis Protocol rounds via CLI, use separate `codex exec` calls per round and embed the full previous-round context in each Round N prompt (stateless full-context-embed, unlike MCP's threadId session continuity).

```bash
# Resolve model from tier
RESOLVED_MODEL=$(python3 -c "
import tomllib, sys
try:
    with open('config/uacp.toml', 'rb') as f:
        cfg = tomllib.load(f)
    tier = {TIER}
    alias = cfg['bridges']['codex']['tiers'][str(tier)]['model']
    model = cfg['bridges']['codex']['model_aliases'][alias]
    print(model)
except: pass
")
MODEL_FLAG=${RESOLVED_MODEL:+--model $RESOLVED_MODEL}

timeout {final_timeout} codex exec "{constructed_prompt}" \
  --sandbox read-only \
  --ask-for-approval never \
  --json \
  --output-last-message /tmp/codex-bridge-{session_id}.json \
  --ephemeral \
  --skip-git-repo-check \
  $MODEL_FLAG \
  --config reasoning-effort={RESOLVED_REASONING}
```

### CLI Error Handling

Shared rows from [uacp-bridge/SKILL.md](../SKILL.md), plus one Codex-specific row:

| Exit code | Meaning | Action |
|-----------|---------|--------|
| 0 | Success | Parse `--output-last-message` file for findings |
| 124 | Timeout (shell) | Return SKIPPED, `skip_reason: timeout_after_{n}s` |
| Other | CLI error | Capture stderr, return SKIPPED with error detail |
| Valid exit, invalid JSON | Parse error | Attempt partial extraction; else SKIPPED |

---

## Output

For the full Output Schema, see [uacp-bridge/SKILL.md](../SKILL.md). Bridge-specific fields added by this adapter:

```json
{
  "bridge": "codex",
  "model_family": "openai/codex",
  "connection_used": "native-dispatch | mcp | cli",
  "multi_agent_enabled": true,
  "tier": 2,
  "resolved_model": "<resolved from registry>",
  "resolved_reasoning": "high"
}
```

`multi_agent_enabled` is **always emitted** regardless of connection path — for caller transparency.

Output ID prefix: `X` (e.g., `X001`, `X002`).

---

## Notes

- **Native dispatch is preferred when executor is Codex** — spawn parallel Codex agents directly
- **MCP server is preferred for non-Codex executors** — no CLI install needed, auth handled internally, persistent sessions via `codex-reply` (stateful — threadId carries full history)
- **CLI path is stateless** — each `codex exec` call starts fresh; embed full prior-round context in Round N prompts (unlike MCP)
- **Auto-setup option** — orchestrator can write `.mcp.json` to enable MCP server without user installing anything
- **`codex exec` ≠ `codex`** — bare `codex` opens an interactive session; always use `codex exec` for programmatic use
- **`--sandbox read-only` + `--ask-for-approval never`** are required for analysis-only mode
- **HALTED ≠ SKIPPED** — HALTED means the user must make a choice before the review can continue; connection_preference step 4 is HALT, not skip
- **Model**: resolved from tier mapping in `config/uacp.toml`; never hardcoded
- **X-high reasoning requires explicit user confirmation** before proceeding — never activate silently; silently activating xhigh is an explicit anti-pattern
- **Tier is never hardcoded** — model selections come from `config/uacp.toml`; update the TOML when OpenAI releases new models
- **+50% base timeout when multi_agent_enabled** — agent spawn overhead; apply before the 1.2× bridge multiplier

---

## CLI Reference

*Last verified: 2026-06-07*

### Invocation Modes

| Mode | Command | When to Use |
|------|---------|-------------|
| Non-interactive exec | `codex exec "prompt"` | Scripted/programmatic use |
| Interactive TUI | `codex` | Terminal UI — do NOT use programmatically |
| MCP server | `codex mcp-server` | Expose Codex as MCP server |

**Always use `codex exec` for programmatic dispatch.** Bare `codex` opens the TUI and cannot be scripted.

---

### `codex exec` — All Flags

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

### `codex models list` — Model Discovery

```bash
codex models list
```

Returns available models. Always check this at runtime — never hardcode a model name.

---

### Authentication

```bash
codex login              # Browser OAuth (interactive)
codex login --device-auth   # Device code flow (headless/CI)
codex login status       # Check authentication status (exit 0 = authenticated)
codex logout             # Remove stored credentials
```

---

### Multi-Agent Feature

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

### MCP Server

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
| `mcp__codex__codex` | Start a Codex session |
| `mcp__codex__codex-reply` | Continue an existing session |

**`mcp__codex__codex` tool parameters:**

| Parameter | Values | Purpose |
|-----------|--------|---------|
| `prompt` | string | Prompt content |
| `approval-policy` | `never`, `on-write`, `always` | Approval mode |
| `sandbox` | `read-only`, `workspace-write` | Filesystem access |
| `model` | model name | Model override |
| `reasoning` | `medium`, `high`, `xhigh` | Reasoning depth |
| `base-instructions` | string | Custom system instructions |

**`mcp__codex__codex-reply` tool parameters:**

| Parameter | Values | Purpose |
|-----------|--------|---------|
| `prompt` | string | Follow-up prompt |
| `threadId` | string | Thread ID from initial `mcp__codex__codex` call |

`threadId` is available in the response as `structuredContent.threadId`.

---

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | CLI error |
| 124 | Timeout (shell `timeout` wrapper) |

---

### Installation

```bash
npm install -g @openai/codex
# or
npx -y codex   # without global install
```
