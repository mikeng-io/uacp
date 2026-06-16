# Bridge: OpenCode (multi-model) — uacp-bridge reference

*Per-runtime reference for [uacp-bridge](../SKILL.md). Depends on: uacp-bridge, domain-registry.*

---

## Bridge Identity

```yaml
bridge: opencode
model_family: multi-provider   # Routes to any configured AI provider
availability: conditional
connection_preference:
  1: native-dispatch  # Executor is OpenCode — internal agent routing
  2: http-api         # Any executor — opencode serve REST API at :4096
  3: cli              # Any other executor — opencode run
  4: halt             # None available — surface advisory, offer setup
```

**Note:** `http-api` is at slot 2 (before cli) and `halt` is at slot 4 (not skip). This is unique to the OpenCode bridge — no silent skip when all paths are exhausted.

---

## Configuration Reference

Parameters this bridge reads from `config/uacp.toml` at runtime:

| Parameter | Section | Type | Default | Description |
|-----------|---------|------|---------|-------------|
| `enabled` | `[bridges.opencode]` | boolean | `true` | Whether this bridge is active. If `false`, the orchestrator skips it. |
| `timeout_multiplier` | `[bridges.opencode]` | float | `1.5` | Multiplier applied to the uacp-bridge base timeout estimate. |
| `models` | `[bridges.opencode]` | array of strings | `[]` | Multi-model dispatch list (`["provider/model", ...]`). Empty = single-model default. |

**Not read from TOML** (intrinsic to bridge implementation):
- `connection_preference` — defined in this file only
- Model selection — delegated to OpenCode's own config (`opencode config get model`)

---

## Tier Resolution

OpenCode bridge does **not** resolve models from `config/uacp.toml` `[models]`. OpenCode is a user-configured multi-provider gateway — the user selects providers, authenticates them, and sets a default model in OpenCode's own configuration. UACP never overrides OpenCode's model selection unless `bridge_input` explicitly requests it.

The general tier resolution protocol in [uacp-bridge/SKILL.md](../SKILL.md) does not apply here. This exception is also noted in the shared contract's `[models]` section.

### What tier means for OpenCode

| Tier | Effect on OpenCode dispatch |
|------|----------------------------|
| 0–4 | **No model selection.** Tier drives `task framing`, `intensity`, and `timeout estimation` only. |

OpenCode uses whatever model the user has configured as default. The bridge discovers this at pre-flight.

### When UACP passes `--model`

Only when `bridge_input` explicitly contains `model_override: "provider/model"`:

```bash
opencode run "{prompt}" --model "{model_override}"
```

Normal tier resolution **never** adds `--model`.

---

## Pre-Flight

### Check A: Native Dispatch?

If the executor is OpenCode, this is the preferred path — route the task to an OpenCode internal agent within the current session rather than shelling out or calling the HTTP API.

```bash
# BOTH vars checked — either indicates an active OpenCode session
echo ${OPENCODE_SESSION_ID:+found}
echo ${OPENCODE_CLIENT:+found}
```

If either is set → **use native dispatch** (route to `general` or `explore` subagent).

If executor is not OpenCode → proceed to Check B.

---

### Check B: HTTP API Server Running?

```bash
curl -s --max-time 3 http://localhost:4096 -o /dev/null -w "%{http_code}"
# Also check custom port if OPENCODE_PORT env var is set
```

If responds (any HTTP code) → **use HTTP API path** (Step 3A). Server is already running.

If no response → proceed to Check C.

---

### Check C: CLI Installed?

```bash
which opencode
```

If found → proceed to Check D.

If not found → **no connection available — go to Step 2 (Advisory)** with `reason: cli_not_found`.

---

### Check D: Model Discovery (CLI path only)

```bash
opencode config get model 2>/dev/null || echo "no_default"
opencode auth list
```

**Outcomes:**
- Default model configured + providers authenticated → proceed to CLI path, record `resolved_model`
- No default, but providers authenticated → proceed to CLI path, `resolved_model: "opencode-default"`
- No providers configured → **go to Step 2 (Advisory)** with `reason: no_provider_configured`

---

## Step 2: Advisory — Halt and Present Options

**Do not skip silently.** Surface the appropriate message and wait for a choice.

### Advisory: Not Installed

```
⚠ OpenCode is not installed or not in PATH.

Options:
  [1] Install OpenCode
      npm install -g opencode-ai
      # or: brew install opencode

  [2] Start the OpenCode server (if already installed elsewhere)
      opencode serve --port 4096
      Then re-run this review.

  [3] Skip OpenCode bridge
      Continue without OpenCode. Other available bridges will run.

  [4] Abort the entire review

What would you like to do? (1/2/3/4)
```

Return `status: HALTED`, `halt_reason: cli_not_found`.

---

### Advisory: No Provider Configured

```
⚠ OpenCode is installed but no AI provider is authenticated.

Configure a provider:
  opencode auth login    # Select and authenticate a provider

Alternatively:
  [1] Skip OpenCode bridge
  [2] Abort the entire review
```

Return `status: HALTED`, `halt_reason: no_provider_configured`.

**HALTED (not SKIPPED) for `no_provider_configured` is intentional.** OpenCode auth is user-managed outside UACP — it cannot be retried automatically. HALTED forces a user decision and ensures coverage is not silently dropped. Do not convert this to SKIPPED without recording it in `auto_skipped_halted_bridges` (see [uacp-bridge/SKILL.md](../SKILL.md) HALTED→SKIPPED conversion rules).

---

### Non-Interactive Environments

Return `status: HALTED` with the full advisory in `halt_message`. Never silently skip.

---

## Step 3: Read Multi-Model Configuration

Before estimating timeout, check `config/uacp.toml` for the `bridges.opencode.models` array. This controls multi-model dispatch within the bridge.

```bash
cat config/uacp.toml 2>/dev/null | python3 -c "
import sys, re
content = sys.stdin.read()
# Extract models array from [bridges.opencode] section
m = re.search(r'\[bridges\.opencode\][^\[]*?models\s*=\s*(\[[^\]]*\])', content, re.DOTALL)
if m:
    print(m.group(1))
else:
    print('[]')
"
```

**Fragility note:** This regex depends on section ordering and multi-line array formatting in the TOML file. If `[bridges.opencode]` appears after another section that also has `models`, the regex may match the wrong block. Validate the extracted value before use.

```yaml
multi_model_dispatch:
  condition: "bridges.opencode.models is present AND has 2+ entries"
  action: "Spawn one execution per model — treat each as an independent participant"
  example_config:
    models: ["glm/glm-4-7", "kimi/moonshot-v1-8k", "qwen/qwen-plus"]

single_model_dispatch:
  condition: "models missing OR empty OR has exactly 1 entry"
  action: "Single execution using model_override or OpenCode's configured default"
```

**Why multi-model matters:** Each model has different training data, biases, and reasoning patterns. With 3 models configured, this bridge becomes its own mini-council — 3 independent perspectives before findings reach the cross-bridge synthesis layer.

---

## Timeout Estimation

Use [uacp-bridge/SKILL.md](../SKILL.md) base timeout table and intensity multiplier, then apply the OpenCode-specific multiplier:

```yaml
opencode_multiplier: 1.5   # Always applied — provider routing overhead

# Single-model dispatch:
final_timeout: base_timeout × intensity_multiplier × 1.5

# Multi-model dispatch (models run in parallel, not sequential):
final_timeout: max(per_model_base_timeout) × intensity_multiplier × 1.5
# NOT the sum — all model invocations run simultaneously
```

OpenCode internally dispatches to one or more providers — each provider call adds latency.

---

## Step 4: Dispatch — Single-Model vs Multi-Model

### Multi-Model Dispatch (when `models` has 2+ entries)

Spawn one parallel execution per configured model. All models receive the identical `bridge_input` — independence is the point.

**Via HTTP API (preferred when server running):**

```bash
# For each model in bridges.opencode.models, in parallel:
SESSION_A=$(curl -s -X POST http://localhost:4096/session \
  -H "Content-Type: application/json" \
  -d '{"title": "opencode-{model_slug}-{session_id}"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

curl -s -X POST http://localhost:4096/session/$SESSION_A/message \
  -H "Content-Type: application/json" \
  -d '{
    "content": [{"type": "text", "text": "{constructed_prompt}"}],
    "model": "{model_A}"   # e.g., "glm/glm-4-7"
  }' &

SESSION_B=... # similarly for model B
SESSION_C=... # similarly for model C

wait  # collect all
```

**Via CLI (fallback):**

```bash
# Run in parallel — one per model
timeout {final_timeout} opencode run "{constructed_prompt}" --model {model_A} &
PID_A=$!
timeout {final_timeout} opencode run "{constructed_prompt}" --model {model_B} &
PID_B=$!
timeout {final_timeout} opencode run "{constructed_prompt}" --model {model_C} &
PID_C=$!
wait $PID_A $PID_B $PID_C
```

If any model invocation times out or errors → mark it as `skipped` in `instances_completed` and continue with remaining results. Never block on a single model failure.

**Post-dispatch: Intra-Bridge Mini-Synthesis (OpenCode only)**

After all model invocations complete, run a mini-synthesis before returning to the orchestrator. This is scoped to OpenCode's multi-model dispatch — it does not generalize to other bridges.

1. **Deduplication**: Findings with >70% description overlap across models → merge (inherit highest severity, list contributing models as `confirmed_by_models`)
2. **Model-confirmed**: Merged findings are elevated (`intra_bridge_multi_model_confirmed: true`)
3. **Single-model findings**: Retained with model attribution
4. **Verdict**: Apply [uacp-bridge/SKILL.md](../SKILL.md) verdict logic to the merged finding set

This mini-synthesis is the intra-bridge equivalent of the cross-bridge synthesis stage — lighter (no full DA challenge round, just deduplication and model-agreement detection), but it means bridge-opencode can report multi-model-confirmed findings before they even reach Layer 1.

---

### Single-Model Dispatch (when `models` is empty/missing or has 1 entry)

Tier drives task framing, intensity, and timeout only (no model selection). Then:

```bash
# Model selection priority:
# 1. If bridge_input.model_override is set → use that (provider/model format)
# 2. If bridges.opencode.models has exactly 1 entry → use that
# 3. Else → omit --model, let OpenCode use its configured default
# Record RESOLVED_MODEL (informational only)
```

Proceed to Step 3A or 3B with the resolved model.

---

## Step 3A: Execute via HTTP API (Preferred)

The OpenCode HTTP server exposes a REST API. Use it when the server is already running (Check B succeeded).

OpenAPI spec available at: `http://localhost:{port}/doc`

### Create a session and send a message

```bash
# Create session
SESSION=$(curl -s -X POST http://localhost:4096/session \
  -H "Content-Type: application/json" \
  -d '{"title": "bridge-review-{session_id}"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Send prompt — use uacp-bridge Agent Prompt Template for the constructed_prompt
curl -s -X POST http://localhost:4096/session/$SESSION/message \
  -H "Content-Type: application/json" \
  -d '{
    "content": [{"type": "text", "text": "{constructed_prompt}"}],
    "model": "{RESOLVED_MODEL}"
  }'
```

### Round 2+ context passing

The HTTP session maintains full conversation history. Round 2+ only needs the context packet injected — not the full Round 1 output re-embedded:

```bash
# Round 2 message — session already has Round 1 history
curl -s -X POST http://localhost:4096/session/$SESSION/message \
  -H "Content-Type: application/json" \
  -d '{
    "content": [{"type": "text", "text": "{role-specific Round N prompt from uacp-bridge context packet}"}]
  }'
```

For true parallel role execution within a round, create one session per role — embed the previous-round outputs explicitly since sessions don't share state:

```bash
# Parallel round execution — one session per role, context embedded in each
CHALLENGER_SESSION=$(curl -s -X POST http://localhost:4096/session \
  -H "Content-Type: application/json" \
  -d '{"title": "challenger-round-2-{session_id}"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
# ... then send challenger Round 2 prompt with embedded context
```

### Model format

Models must use `provider/model` format:

```yaml
model_format: "provider/model"
examples:
  - "anthropic/claude-sonnet-4-6"
  - "openai/gpt-5.4"
  - "google/gemini-3.5-flash"
  - "glm/glm-4-flash"
  - "qwen/qwen-plus"
```

### Authentication (if server has password)

```bash
# With auth: -u opencode:$OPENCODE_SERVER_PASSWORD
curl -s -u opencode:$OPENCODE_SERVER_PASSWORD \
  -X POST http://localhost:4096/session/...
```

### Agent selection

```bash
# Use the built-in 'plan' agent for read-only analysis
curl -s -X POST http://localhost:4096/session \
  -H "Content-Type: application/json" \
  -d '{"title": "...", "agent": "plan"}'
```

Built-in agents:
- `plan` — restricted, read-only, suited for analysis and review tasks (use this for bridge review tasks)
- `build` — full tool access (not appropriate for review-only)

---

## Step 3B: Execute via CLI (Fallback)

Build the prompt using the [uacp-bridge/SKILL.md](../SKILL.md) Agent Prompt Template.

```bash
timeout {final_timeout} opencode run "{constructed_prompt}" \
  --format json \
  --model {RESOLVED_MODEL}
```

**TUI guard:** `opencode` (bare) opens the interactive TUI and hangs in scripted environments. Always use `opencode run "..."` for programmatic use — never bare `opencode`.

For the Post-Analysis Protocol via CLI, use separate `opencode run` calls per round — no session continuity. Embed the full previous-round outputs and context packet in each Round N prompt (stateless context passing, same pattern as Gemini and Codex CLI).

### CLI Error Handling

| Exit code | Meaning | Action |
|-----------|---------|--------|
| 0 | Success | Parse JSON event stream for final message |
| 124 | Timeout | Return SKIPPED, `skip_reason: timeout_after_{n}s` |
| Other | CLI error | Capture stderr, return SKIPPED with detail |

---

## Output

For the full Output Schema, see [uacp-bridge/SKILL.md](../SKILL.md). Bridge-specific fields added by this adapter:

```json
{
  "bridge": "opencode",
  "model_family": "multi-provider",
  "connection_used": "native-dispatch | http-api | cli",
  "dispatch_mode": "multi-model | single-model",
  "tier": 2,
  "resolved_model": "glm/glm-4-7",
  "models_configured": ["glm/glm-4-7", "kimi/moonshot-v1-8k", "qwen/qwen-plus"],
  "models_used": ["glm/glm-4-7", "kimi/moonshot-v1-8k"],
  "instances_spawned": 3,
  "instances_completed": 2,
  "intra_bridge_confirmed": 4
}
```

- `models_configured`: full list from `config/uacp.toml`
- `models_used`: models that successfully completed (subset if any timed out)
- `instances_spawned`: number of parallel executions launched
- `instances_completed`: number that returned results (may be less than spawned)
- `intra_bridge_confirmed`: count of findings confirmed by 2+ models within this bridge (before cross-bridge synthesis)

**Output ID prefix:** `O` (e.g., `O001`, `O002`). In multi-model mode, prefix per model: `O-glm-001`, `O-kimi-001`, etc. Merged findings use: `O-merged-001`. The orchestrator's cross-bridge dedup parses these prefixes to attribute findings by bridge and model.

*Last verified: 2026-06-07*

---

## CLI Reference

### Invocation Modes

| Mode | Command | When to Use |
|------|---------|-------------|
| Non-interactive run | `opencode run "prompt"` | Scripted/programmatic use |
| Interactive TUI | `opencode` | Terminal UI — do NOT use programmatically |
| HTTP API server | `opencode serve` | Start REST API at `:4096` |

**Always use `opencode run` for programmatic dispatch.** Bare `opencode` opens the TUI and hangs.

---

### `opencode run` — All Flags

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

### HTTP API

OpenCode exposes a REST API when running as a server.

#### Start the server

```bash
opencode serve --port 4096   # Default port 4096
# OPENCODE_PORT env var also accepted
```

OpenAPI spec: `http://localhost:{port}/doc`

#### Session management

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

#### Authentication (if password set)

```bash
curl -u opencode:$OPENCODE_SERVER_PASSWORD -X POST http://localhost:4096/session ...
```

#### Full session+message flow (bash)

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

### Authentication (Provider)

```bash
opencode auth login       # Authenticate a provider (interactive)
opencode auth list        # List authenticated providers
opencode auth logout      # Remove provider authentication
```

**Supported providers:** Anthropic, OpenAI, Google, GLM, Qwen, and others depending on version.

---

### Agents

| Agent | Mode | Best For |
|-------|------|---------|
| `plan` | Read-only | Analysis, review, code inspection |
| `build` | Full tool access | Implementation tasks |

For bridge review tasks, always use `plan`.

---

### Exit Codes (`opencode run`)

| Code | Meaning |
|------|---------|
| 0 | Success |
| Non-zero | Error — check stderr |
| 124 | Timeout (shell `timeout` wrapper) |

---

### Installation

```bash
npm install -g opencode-ai
# or
brew install opencode
```

---

## Notes

- **HTTP API is preferred** — use it when `opencode serve` is already running (lower overhead, session continuity)
- **`opencode run` ≠ `opencode`** — bare `opencode` opens the interactive TUI; always use `opencode run "..."` for scripted use
- **Model format is `provider/model`** — e.g., `anthropic/claude-sonnet-4-6`, not just `claude`
- **`plan` agent** is the safe choice for review tasks (read-only mode)
- **1.5× timeout multiplier** always applies (provider routing overhead)
- **HALTED ≠ SKIPPED** — HALTED requires user input before the review can proceed
- **Tier never selects a model** — model selections come from OpenCode's own config; use `opencode config get model` / `opencode auth list` to discover
- **Multi-model config is separate from tier mapping** — `bridges.opencode.models` enables parallel multi-model dispatch; tier mapping selects the default single-model for all other bridges but not this one
- **Intra-bridge mini-synthesis is OpenCode-only** — the 70% dedup + `intra_bridge_multi_model_confirmed` flag applies only to multi-model dispatch within this bridge; do not generalize to other bridges
