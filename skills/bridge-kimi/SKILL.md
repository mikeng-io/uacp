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
  1: native-dispatch  # Executor is Kimi Code — Agent tool sub-agents
  2: cli              # Any other executor — kimi -p
  3: acp-server       # Agent Client Protocol over stdio
  4: skip
```

---

## Configuration Reference

Parameters this bridge reads from `config/uacp.toml` at runtime:

| Parameter | Section | Type | Default | Description |
|-----------|---------|------|---------|-------------|
| `enabled` | `[bridges.kimi]` | boolean | `true` | Whether this bridge is active. If `false`, the orchestrator skips it. |
| `timeout_multiplier` | `[bridges.kimi]` | float | `1.0` | Multiplier applied to the bridge-commons base timeout estimate. |
| `path` | `[bridges.kimi]` | string | `"auto"` | Path to the `kimi` binary. `"auto"` resolves via `$PATH` and common locations. |

**Not read from TOML** (intrinsic to bridge implementation):
- `connection_preference` — defined in this SKILL.md only
- Model selection — resolved from `config/model-registry.yaml`, not TOML

---

## Tier Resolution

Kimi bridge resolves the model alias from `config/model-registry.yaml` in `UACP_ROOT`. The tier mapping lives **only** in the registry — this skill does not hardcode it.

**Resolution protocol:**
1. Read `UACP_ROOT/config/model-registry.yaml`
2. Look up `tier_mappings.kimi.{tier}` → get `alias` + `reasoning`
3. Look up `providers.moonshot.models.{alias}.concrete_id` → get resolved model ID

The alias is stable; the `concrete_id` is updated in the registry when Moonshot releases new models. No bridge skill changes required.

**Current limitation:** Kimi Code currently offers one primary model (`kimi-k2.6`). All tiers map to the same alias in the registry. When Moonshot releases additional models, update `config/model-registry.yaml` only.

**Override via `bridge_input.tier`:** If the council assigns a specific tier, use it directly. If absent, derive from `task_type` + `intensity` per bridge-commons rules.

---

## Pre-Flight

### Check A: Native Dispatch?

If the executor is Kimi Code with Agent tool access, this is the preferred path — spawn parallel Kimi sub-agents rather than shelling out to the CLI.

```bash
# Check if running inside a Kimi Code session
echo ${KIMI_CODE_SESSION_ID:+found}
```

If in a Kimi Code session → **use native dispatch** (Agent tool path in Native Dispatch section).

If executor is not Kimi Code → proceed to Check B.

---

### Check B: Resolve Kimi binary path

Check in priority order:

1. **UACP config** — `config/uacp.toml` → `bridges.kimi.path`
2. **Environment** — `KIMI_CODE_CLI_PATH` env var
3. **`$PATH` resolution** — `which kimi`
4. **Common locations**:
   - `$HOME/.kimi-code/bin/kimi`
   - `$HOME/.local/bin/kimi`
   - `/usr/local/bin/kimi`

### Check C: CLI availability check

```bash
test -x "<resolved-kimi-path>" && "<resolved-kimi-path>" --version
```

If unavailable, return `SKIPPED` with `skip_reason: "kimi CLI not available"`.

### Check D: Model resolution

```yaml
priority:
  1: UACP model registry → UACP_ROOT/config/model-registry.yaml → tier_mappings.kimi.{tier}
  2: Environment → KIMI_CODE_MODEL
  3: CLI default → omit --model flag (uses config.toml default_model)
```

Resolve tier first, then look up the model alias from the registry:
```bash
# 1. Determine tier (from bridge_input.tier or derive from task_type + intensity)
# 2. Read UACP_ROOT/config/model-registry.yaml
# 3. Look up tier_mappings.kimi.{tier} → get alias + reasoning
# 4. Look up providers.moonshot.models.{alias}.concrete_id → get resolved model ID
# 5. Set RESOLVED_MODEL
```

Valid model aliases depend on the Kimi Code version. Check available models via:
```bash
kimi provider list
```

### Check E: Auth check

Kimi Code uses OAuth device-code flow. Check login status:
```bash
kimi login status 2>/dev/null || echo "not_logged_in"
```

If not authenticated → return `HALTED` with advisory to run `kimi login`.

---

## Native Dispatch (preferred when executor is Kimi Code)

When running inside Kimi Code, use the Agent tool to spawn parallel sub-agents — one per domain from `bridge_input.domains`. Build prompts using the Agent Prompt Template from bridge-commons.

```
Agent 1: {domain_1} expert — focus: {focus_areas}, scope: {scope}
Agent 2: {domain_2} expert — focus: {focus_areas}, scope: {scope}
...
Agent N:   Devil's Advocate — challenge assumptions, find failure modes (domain: "cross-domain")
Agent N+1: Integration Checker — cross-component impacts, implicit contracts (domain: "integration")
```

All agents run in parallel. After all complete, run the bridge-commons Post-Analysis Protocol. For subsequent rounds, spawn new agents with the context packet embedded in their prompts — the parent agent holds all state between rounds.

**Key advantage:** No external process spawn overhead; sub-agents reuse the parent's auth, model config, and working directory.

**Fallback:** If Agent tool is unavailable (e.g., nested execution depth limit) → fall back to CLI path.

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

**Last verified:** 2026-06-07

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
  "connection_used": "native-dispatch | cli | acp-server",
  "model_family": "moonshot/kimi",
  "tier": 2,
  "resolved_model": "<resolved from registry>"
}
```
