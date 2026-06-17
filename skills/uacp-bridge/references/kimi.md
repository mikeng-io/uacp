# Bridge: Kimi (Moonshot) — uacp-bridge reference

*Per-runtime reference for [uacp-bridge](../SKILL.md). Depends on: uacp-bridge, the domain registry (uacp-core/references/domains/).*

---

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
| `timeout_multiplier` | `[bridges.kimi]` | float | `1.0` | Multiplier applied to the uacp-bridge base timeout estimate. |
| `path` | `[bridges.kimi]` | string | `"auto"` | Path to the `kimi` binary. `"auto"` resolves via `$PATH` and common locations. |

**Not read from TOML** (intrinsic to bridge implementation):
- `connection_preference` — defined in this file only
- Model selection — resolved from `config/uacp.toml` `[models]` (same file, `[models.tier_mappings]` + `[models.providers]` sections)

---

## Tier Resolution

Kimi bridge resolves the model alias from `config/uacp.toml` `[models]` in `UACP_ROOT`. The tier mapping lives **only** in `uacp.toml` — this file does not hardcode it.

The general tier resolution protocol is defined in [uacp-bridge/SKILL.md](../SKILL.md). Kimi-specific steps:

1. Read `UACP_ROOT/config/uacp.toml` `[models]` section
2. Look up `[models.tier_mappings.kimi.{tier}]` → get `alias` + `reasoning`
3. Look up `[models.providers.moonshot.models.{alias}]` → `concrete_id` → get resolved model ID

The alias is stable; the `concrete_id` is updated in the registry when Moonshot releases new models. No bridge reference changes required.

**Current limitation:** Kimi Code currently offers one primary model (`kimi-k2.6`). All tiers map to the same alias. When Moonshot releases additional models, update `config/uacp.toml` `[models.providers.moonshot]` and `[models.tier_mappings.kimi]` only.

**Override via `bridge_input.tier`:** If the council assigns a specific tier, use it directly. If absent, derive from `task_type` + `intensity` per uacp-bridge rules (see [uacp-bridge/SKILL.md](../SKILL.md)).

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
  1: uacp.toml [models] → UACP_ROOT/config/uacp.toml → [models.tier_mappings.kimi.{tier}]
  2: Environment → KIMI_CODE_MODEL
  3: CLI default → omit --model flag (uses config.toml default_model)
```

Resolve tier first, then look up the model alias from `uacp.toml`:
```bash
# 1. Determine tier (from bridge_input.tier or derive from task_type + intensity)
# 2. Read UACP_ROOT/config/uacp.toml [models] section
# 3. Look up [models.tier_mappings.kimi.{tier}] → get alias + reasoning
# 4. Look up [models.providers.moonshot.models.{alias}].concrete_id → get resolved model ID
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

> **Deliberate asymmetry with Gemini:** Gemini auth failure returns `SKIPPED`. Kimi auth failure returns `HALTED`. This is intentional — do not homogenize. Kimi's OAuth device-code flow requires explicit user action and cannot be retried automatically; surfacing `HALTED` ensures the user is prompted to run `kimi login` rather than silently dropping coverage.

---

## Native Dispatch (preferred when executor is Kimi Code)

When running inside Kimi Code, use the Agent tool to spawn parallel sub-agents — one per domain from `bridge_input.domains`. Build prompts using the Agent Prompt Template from [uacp-bridge/SKILL.md](../SKILL.md).

```
Agent 1: {domain_1} expert — focus: {focus_areas}, scope: {scope}
Agent 2: {domain_2} expert — focus: {focus_areas}, scope: {scope}
...
Agent N:   Devil's Advocate — challenge assumptions, find failure modes (domain: "cross-domain")
Agent N+1: Integration Checker — cross-component impacts, implicit contracts (domain: "integration")
```

All agents run in parallel. After all complete, run the uacp-bridge Post-Analysis Protocol (see [uacp-bridge/SKILL.md](../SKILL.md)). For subsequent rounds, spawn new agents with the context packet embedded in their prompts — the parent agent holds all state between rounds.

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

> ⚠ **Open question / unresolved:** The `--output-format` value used above is `json`, but the CLI reference table below lists the documented valid values as `text` and `stream-json` — `json` does not appear as a valid value in the CLI help. Flag for human audit against the actual binary before relying on structured JSON output parsing.

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

This exposes the Agent Client Protocol for programmatic integration. Use when the orchestrator supports ACP/stdio communication. This is tier-3 in the connection preference order — unique among CLI bridges (Gemini and Codex have no ACP equivalent at this tier).

### Session continuity

Resume previous session for the working directory:
```bash
kimi -C -p "$PROMPT" --output-format json
```

Or resume specific session:
```bash
kimi -S "$SESSION_ID" -p "$PROMPT" --output-format json
```

> ⚠ **Open question / unresolved:** uacp-bridge treats Kimi as stateless (new `kimi -p` calls with embedded context per round; see Context Passing Between Rounds in [uacp-bridge/SKILL.md](../SKILL.md)). The `-C` and `-S` flags provide session continuity that is in tension with this assumption — if a prior Kimi session is active in the working directory, `-C` will resume it and the embedded context packet may conflict with or confuse the existing session history. Decision needed: should uacp-bridge explicitly suppress `-C`/`-S` during bridge execution, or define a policy for when session continuity is safe to use?

---

## Error Handling

- Exit code `0` with content: parse findings into uacp-bridge output.
- Timeout: return `SKIPPED` with `skip_reason: "timeout_after_<seconds>s"`.
- Empty output: return `SKIPPED` with `skip_reason: "empty_output"`.
- Other non-zero exit: return `SKIPPED` with stderr summary.
- Auth failure: return `HALTED` with `halt_reason: "not_authenticated"`.

Never treat empty output as a completed review.

---

## Output

For the full Output Schema, see [uacp-bridge/SKILL.md](../SKILL.md). Bridge-specific fields added by this adapter:

```json
{
  "bridge": "kimi",
  "connection_used": "native-dispatch | cli | acp-server",
  "model_family": "moonshot/kimi",
  "tier": 2,
  "resolved_model": "<resolved from registry>"
}
```

Output ID prefix: `K` (e.g., `K001`, `K002`).

**Single-model limitation:** Kimi Code currently maps all tiers to the same underlying model. When the resolved model ID is the same across tiers, record `resolved_model` from the registry regardless. Update `config/uacp.toml` `[models.providers.moonshot]` and `[models.tier_mappings.kimi]` when Moonshot releases additional models — no changes to this reference required.

> ⚠ **Open question / unresolved:** The `thinking` reasoning value appears in `[models.tier_mappings.kimi]` in `uacp.toml` but has no corresponding CLI flag in the Kimi Code binary (unlike Codex which uses `--config reasoning-effort`). It is unclear whether `thinking` is an internal label only (used for orchestrator context but not passed to the CLI) or whether a future Kimi CLI version will expose a flag for it. Do not pass `thinking` as a CLI argument until this is resolved. Record `resolved_reasoning` in bridge output as the raw value from the registry.

---

## CLI Reference

*Last verified: 2026-06-07*

### Invocation Modes

| Mode | Command | When to Use |
|------|---------|-------------|
| Prompt flag | `kimi -p "prompt"` | Scripted/programmatic use |
| Interactive | `kimi` | Interactive session |
| ACP server | `kimi acp` | Agent Client Protocol integration |

---

### `kimi` — Global Options

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
| `--skills-dir <dir>` | path | [] | Load skills from directory (repeatable; Kimi-only flag) |
| `--plan` | flag | false | Start in plan mode |
| `-h, --help` | — | — | Show help |

**For bridge use:** `kimi -p "prompt" --output-format json` is the standard invocation.
**For implementation tasks:** add `-y` for auto-approval.
**For read-only analysis:** add `--plan` for safer defaults.

> **Note on `--skills-dir`:** This flag is repeatable and Kimi-specific — no equivalent exists in the Gemini or Codex CLI bridges.

---

### Commands

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

### Authentication

```bash
kimi login              # Device-code OAuth flow
kimi login status       # Check auth status
```

Kimi Code uses OAuth — no manual API key management needed for CLI use.

For API access (third-party tools), create an API Key in the Kimi Code console.

---

### Model Aliases

Check available models via:
```bash
kimi provider list
```

Common aliases depend on the Kimi Code version. The default is configured in `~/.kimi-code/config.toml` under `default_model`.

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
# macOS / Linux
curl -fsSL https://code.kimi.com/kimi-code/install.sh | bash

# Installs to $HOME/.kimi-code/bin/kimi by default
# Optional env:
#   KIMI_VERSION=0.11.0          # Pin version
#   KIMI_INSTALL_DIR=/usr/local  # Custom install dir
#   KIMI_NO_MODIFY_PATH=1        # Skip PATH update
```

Binary location: `$HOME/.kimi-code/bin/kimi`
