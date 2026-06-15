---
name: bridge-gemini
description: Reference adapter for Gemini CLI. Read by any orchestrating skill via the Read tool. Defines how to invoke Gemini CLI in non-interactive mode, timeout estimation, and fallback behavior. Usable by agent-council, lifecycle skills, or any custom skill that needs Gemini-based review.
location: managed
context: reference
dependencies:
  - bridge-commons
  - domain-registry
---

# Bridge: Gemini CLI Adapter

This file is a REFERENCE DOCUMENT. Any orchestrating skill reads it via the `Read` tool and embeds its instructions directly into Task agent prompts. It is not invoked as a standalone skill — it is a reusable set of instructions for Gemini CLI dispatch.

**Input schema, agent prompt template, output schema, verdict logic, timeout formula, artifact format, tier system, and status semantics are defined in `bridge-commons/SKILL.md`. This file covers only Gemini-specific connection detection, tier resolution, and execution.**

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

---

## Configuration Reference

Parameters this bridge reads from `config/uacp.toml` at runtime:

| Parameter | Section | Type | Default | Description |
|-----------|---------|------|---------|-------------|
| `enabled` | `[bridges.gemini]` | boolean | `true` | Whether this bridge is active. If `false`, the orchestrator skips it. |
| `timeout_multiplier` | `[bridges.gemini]` | float | `1.0` | Multiplier applied to the bridge-commons base timeout estimate. |

**Not read from TOML** (intrinsic to bridge implementation):
- `connection_preference` — defined in this SKILL.md only
- `subagent_mode` — auto-detected via `.gemini/settings.json` (`experimental.enableAgents`)

---

## Tier Resolution

Gemini bridge resolves the model alias from `config/uacp.toml` `[models]` in `UACP_ROOT`. The tier mapping lives **only** in `uacp.toml` — this skill does not hardcode it.

**Resolution protocol:**
1. Read `UACP_ROOT/config/uacp.toml` `[models]` section
2. Look up `[models.tier_mappings.gemini.{tier}]` → get `alias` + `reasoning`
3. Look up `[models.providers.google.models.{alias}]` → `concrete_id` → get resolved model ID

The alias is stable; the `concrete_id` is updated in the registry when Google releases new models. No bridge skill changes required.

**Override via `bridge_input.tier`:** If the council assigns a specific tier, use it directly. If absent, derive from `task_type` + `intensity` per bridge-commons rules.

---

## Pre-Flight — Connection Detection

### Check A: Native Dispatch?

If the executor is Gemini CLI with subagent support enabled, this is the preferred path — spawn specialized Gemini subagents rather than shelling out to the CLI.

```bash
# Check if subagents are enabled in project or user settings
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

Build the prompt using the Agent Prompt Template from bridge-commons, adapting to `task_type`. Calculate timeout using bridge-commons formula (no bridge-specific multiplier for Gemini).

Resolve tier and model before invocation:
```bash
# 1. Determine tier (from bridge_input.tier or derive from task_type + intensity)
# 2. Read UACP_ROOT/config/uacp.toml [models] section
# 3. Look up [models.tier_mappings.gemini.{tier}] → get alias + reasoning
# 4. Look up [models.providers.google.models.{alias}].concrete_id → get resolved model ID
# 5. Set RESOLVED_MODEL
```

```bash
TIMEOUT={calculated_timeout}
PROMPT="{constructed_prompt}"

timeout $TIMEOUT gemini -p "$PROMPT" \
  --model ${RESOLVED_MODEL} \
  --approval-mode plan \
  --output-format json
```

Error handling:
- Exit code 0 with JSON → parse and return findings
- Exit code 124 (timeout) → return SKIPPED with reason `timeout_after_{n}s`
- Other exit codes → return SKIPPED with reason `gemini CLI error: {stderr}`
- Invalid JSON output → attempt to extract structured content, else SKIPPED

After execution, run the bridge-commons Post-Analysis Protocol. Gemini uses **stateless context passing** between rounds — embed the full previous-round outputs and context packet in each subsequent `gemini -p` call. There is no session continuity between separate CLI invocations.

For `standard` and `thorough` intensity, construct the Round 2 prompt as:

```
{Agent Prompt Template for this role}

--- ROUND 2 CONTEXT ---
Previous round findings:
{JSON of all Round 1 outputs}

{context packet: open_challenges directed at this domain, synthesis}
```

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
- If `false` or missing → run standard single Gemini call covering all domains (valid fallback)

Subagent mode is a progressive enhancement. Record `subagent_mode: true/false` in output.

---

## CLI Reference

**Last verified:** 2026-06-07

### Key flags

| Flag | Description |
|------|-------------|
| `-p "prompt"` | Prompt string — non-interactive mode |
| `--model <model>` | Model to use (resolved from tier mapping) |
| `--approval-mode plan` | Read-only mode (safe for review/audit) |
| `--approval-mode auto_edit` | Auto-approve file edits (implementation tasks only) |
| `--output-format json` | Structured JSON output for parsing |

---

## Output

See bridge-commons Output Schema. Bridge-specific fields:

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

## Notes

- Always check availability first — never assume gemini is installed
- Use non-interactive mode only; always specify `--approval-mode`
- Use `--output-format json` for structured parsing (not `-o json`)
- Timeout is estimated from scope, not hardcoded — see bridge-commons formula
- SKIPPED is a valid, non-error outcome
- **Tier is never hardcoded** — model selections come from `config/uacp.toml`; update the TOML when Google releases new models

**Analysis safety:** Use `--approval-mode plan` for all non-implementation task types.
This prevents Gemini from auto-applying file edits during review/audit/research tasks.
For implementation tasks (task_type = implementation), `auto_edit` may be appropriate.
