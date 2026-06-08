---
name: bridge-codex
description: Reference adapter for Codex multi-agent review. Read by any orchestrating skill via the Read tool. Native dispatch (preferred when executor is Codex), MCP server path, CLI fallback. Interactive pre-flight advisory when not configured, correct flags embedded. Usable by agent-council, lifecycle skills, or any custom skill that needs Codex-based review.
location: managed
context: reference
dependencies:
  - bridge-commons
  - domain-registry
---

# Bridge: Codex Multi-Agent Adapter

This file is a REFERENCE DOCUMENT. Any orchestrating skill reads it via the `Read` tool and embeds its instructions directly into Task agent prompts. It is not invoked as a standalone skill — it is a reusable set of instructions for Codex review dispatch via MCP server or CLI.

**Input schema, output schema, verdict logic, artifact format, tier system, and status semantics are defined in `bridge-commons/SKILL.md`. This file covers Codex-specific connection detection, tier resolution, prompt adaptation, and execution.**

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
| `timeout_multiplier` | `[bridges.codex]` | float | `1.2` | Multiplier applied to the bridge-commons base timeout estimate. |

**Not read from TOML** (intrinsic to bridge implementation):
- `connection_preference` — defined in this SKILL.md only
- `multi_agent_enabled` — auto-detected via `codex features list`; recorded in output for transparency

---

## Tier Resolution

Codex bridge resolves the model alias and reasoning level from `config/model-registry.yaml` in `UACP_ROOT`. The tier mapping lives **only** in the registry — this skill does not hardcode it.

**Resolution protocol:**
1. Read `UACP_ROOT/config/model-registry.yaml`
2. Look up `tier_mappings.codex.{tier}` → get `alias` + `reasoning`
3. Look up `providers.openai.models.{alias}.concrete_id` → get resolved model ID
4. Apply reasoning level to `--config reasoning-effort`

The alias is stable; the `concrete_id` is updated in the registry when OpenAI releases new models. No bridge skill changes required.

**Reasoning mapping (bridge-specific):**
- `medium` → `--config reasoning-effort=medium`
- `high` → `--config reasoning-effort=high`
- `xhigh` → `--config reasoning-effort=xhigh`

**Override via `bridge_input.tier`:** If the council assigns a specific tier, use it directly. If absent, derive from `task_type` + `intensity` per bridge-commons rules.

**Xhigh Alert (MANDATORY):** When resolved reasoning is `xhigh`, alert the user before proceeding:
```
⚠ Reasoning level: XHIGH
Codex will use maximum reasoning depth for this review.
This increases token usage and may take 2–3× longer than standard.

Continue? (y/n)
```
If user declines → fall back to `high`. Return `resolved_reasoning: "high"` in output.

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

---

## Step 3: Build Domain Prompt

Codex's multi-agent capability means the prompt is addressed to a **coordinator**, not a single domain expert. This differs from the bridge-commons Agent Prompt Template (which addresses one expert per call). Adapt as follows:

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

Each agent must return outputs using the schema from bridge-commons:
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

In single-agent mode, drop the coordinator framing and use the bridge-commons Agent Prompt Template directly, covering all domains in one prompt.

---

## Timeout Estimation

Use bridge-commons base timeout table and intensity multiplier. Codex multi-agent adds sub-agent spawn overhead — apply a higher base when multi-agent is enabled:

```yaml
# When multi_agent_enabled: true — increase base by 50%
# e.g., 5-20 files: 180s → 270s to account for agent spawn latency
# When multi_agent_enabled: false — use bridge-commons base times directly
```

No separate bridge multiplier otherwise.

---

## Step 3A: Execute via MCP Server (Preferred)

Use the `codex` MCP tool directly. The MCP server runs `codex mcp-server` and exposes two tools:

### Model Selection — Resolve from Tier

Before calling either MCP or CLI, resolve the model from the tier:

```bash
# 1. Determine tier (from bridge_input.tier or derive from task_type + intensity)
# 2. Read UACP_ROOT/config/model-registry.yaml
# 3. Look up tier_mappings.codex.{tier} → get alias + reasoning
# 4. Look up providers.openai.models.{alias}.concrete_id → get resolved model ID
# 5. Set RESOLVED_MODEL and RESOLVED_REASONING
```

Do NOT hardcode a model name. If model discovery fails, omit the `model` parameter and let the server select its default.

### Tool: `codex` — Start a session

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

### Tool: `codex-reply` — Continue session (if needed)

```
Call: mcp__codex__codex-reply
Parameters:
  prompt:   "Summarize and consolidate all agent findings into the JSON format specified."
  threadId: {threadId from previous call}
```

The `codex-reply` call implements the bridge-commons Post-Analysis Protocol for the MCP path. Use `codex-reply` for each subsequent round — the thread maintains full Round 1 history, so only inject the context packet:

```
Call: mcp__codex__codex-reply
Parameters:
  prompt:   "{role-specific Round N prompt from bridge-commons context packet}"
  threadId: {threadId from Round 1}
```

Run one `codex` + N `codex-reply` calls per role, one role at a time or in parallel sessions.

---

## Step 3B: Execute via CLI (Fallback)

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

For the Post-Analysis Protocol via CLI, use separate `codex exec` calls per round — no session continuity. Embed the full previous-round context in each Round N prompt (same stateless pattern as Gemini CLI).

### CLI Error Handling

| Exit code | Meaning | Action |
|-----------|---------|--------|
| 0 | Success | Parse `--output-last-message` file for findings |
| 124 | Timeout (shell) | Return SKIPPED, `skip_reason: timeout_after_{n}s` |
| Other | CLI error | Capture stderr, return SKIPPED with error detail |
| Valid exit, invalid JSON | Parse error | Attempt partial extraction; else SKIPPED |

---

## CLI Reference

**Last verified:** 2026-06-07

### Key flags

| Flag | Purpose |
|------|---------|
| `codex exec` | Non-interactive execution (always use this, not bare `codex`) |
| `--model <model>` | Model to use (resolved from tier mapping) |
| `--config reasoning-effort=<level>` | Reasoning effort: medium, high, xhigh |
| `--sandbox read-only` | Analysis-only mode (no file writes) |
| `--ask-for-approval never` | No interactive approval prompts |
| `--json` | Structured JSON output |
| `--output-last-message <path>` | Write final message to file for parsing |
| `--ephemeral` | Discard session after execution |
| `--skip-git-repo-check` | Skip git repository validation |

### MCP tools

| Tool | Purpose |
|------|---------|
| `mcp__codex__codex` | Start a session (returns threadId) |
| `mcp__codex__codex-reply` | Continue session with threadId |

---

## Output

See bridge-commons Output Schema. Bridge-specific fields:

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

Output ID prefix: `X` (e.g., `X001`, `X002`).

---

## Notes

- **Native dispatch is preferred when executor is Codex** — spawn parallel Codex agents directly
- **MCP server is preferred for non-Codex executors** — no CLI install needed, auth handled internally, persistent sessions via `codex-reply`
- **Auto-setup option** — orchestrator can write `.mcp.json` to enable MCP server without user installing anything
- **`codex exec` ≠ `codex`** — bare `codex` opens an interactive session; always use `codex exec` for programmatic use
- **`--sandbox read-only` + `--ask-for-approval never`** are required for analysis-only mode
- **HALTED ≠ SKIPPED** — HALTED means the user must make a choice before the review can continue
- **Model**: resolved from tier mapping in `config/uacp.toml`; never hardcoded
- **X-high reasoning requires explicit user confirmation** before proceeding — never activate silently
- **Tier is never hardcoded** — model selections come from `config/uacp.toml`; update the TOML when OpenAI releases new models
- Timeout base increases when multi-agent is enabled (agent spawn overhead)
