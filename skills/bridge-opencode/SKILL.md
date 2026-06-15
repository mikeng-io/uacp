---
name: bridge-opencode
description: Reference adapter for OpenCode — model-agnostic multi-provider bridge. Read by any orchestrating skill via the Read tool. Covers pre-flight checks with interactive advisory, HTTP API server path (preferred), CLI run path as fallback, correct flags and model format embedded. Usable by agent-council, lifecycle skills, or any custom skill that needs multi-model review.
location: managed
context: reference
dependencies:
  - bridge-commons
  - domain-registry
---

# Bridge: OpenCode Multi-Model Adapter

This file is a REFERENCE DOCUMENT. Any orchestrating skill reads it via the `Read` tool and embeds its instructions directly into Task agent prompts. It is not invoked as a standalone skill — it is a reusable set of instructions for OpenCode dispatch.

**Input schema, agent prompt template, output schema, verdict logic, artifact format, tier system, and status semantics are defined in `bridge-commons/SKILL.md`. This file covers OpenCode-specific connection detection, tier resolution, timeout multiplier, and execution paths.**

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

---

## Configuration Reference

Parameters this bridge reads from `config/uacp.toml` at runtime:

| Parameter | Section | Type | Default | Description |
|-----------|---------|------|---------|-------------|
| `enabled` | `[bridges.opencode]` | boolean | `true` | Whether this bridge is active. If `false`, the orchestrator skips it. |
| `timeout_multiplier` | `[bridges.opencode]` | float | `1.5` | Multiplier applied to the bridge-commons base timeout estimate. |
| `models` | `[bridges.opencode]` | array of strings | `[]` | Multi-model dispatch list (`["provider/model", ...]`). Empty = single-model default. |

**Not read from TOML** (intrinsic to bridge implementation):
- `connection_preference` — defined in this SKILL.md only
- Model selection — delegated to OpenCode's own config (`opencode config get model`)

---

## Why OpenCode?

OpenCode is provider-agnostic — it routes to whichever AI providers are configured (Anthropic, OpenAI, Google, GLM, Qwen, etc.). Running it as a bridge lets the calling skill get a second opinion from a different model family than the one currently executing the skill.

**Trade-off:** 1.5× timeout multiplier applies because model calls go through OpenCode's routing layer.

---

## Tier Resolution

OpenCode bridge does **not** resolve models from `config/uacp.toml` `[models]`. OpenCode is a user-configured multi-provider gateway — the user selects providers, authenticates them, and sets a default model in OpenCode's own configuration. UACP never overrides OpenCode's model selection unless `bridge_input` explicitly requests it.

### What tier means for OpenCode

| Tier | Effect on OpenCode dispatch |
|------|----------------------------|
| 0–4 | **No model selection.** Tier drives `task framing`, `intensity`, and `timeout estimation` only. |

OpenCode uses whatever model the user has configured as default. The bridge discovers this at pre-flight.

### Model discovery protocol (pre-flight step)

```bash
# 1. Check if OpenCode has a default model configured
opencode config get model 2>/dev/null || echo "no_default"

# 2. If no default, list authenticated providers
opencode auth list
```

- **Default model present** → record `resolved_model: "<provider/model>"` (informational only)
- **No default, but providers authenticated** → OpenCode will prompt or use its internal heuristic; record `resolved_model: "opencode-default"`
- **No providers authenticated** → HALT with advisory to run `opencode auth login`

### When UACP passes `--model`

Only when `bridge_input` explicitly contains `model_override: "provider/model"`:

```bash
opencode run "{prompt}" --model "{model_override}"
```

Normal tier resolution **never** adds `--model`.

### Multi-model dispatch

When `bridges.opencode.models` in `config/uacp.toml` has 2+ entries, OpenCode runs its own mini-council — one invocation per configured model in parallel. This is independent of tier resolution. The `models` array is user-configured and opaque to UACP.

---

## Step 1: Pre-Flight — Connection Detection

### Check A: Native Dispatch?

If the executor is OpenCode, this is the preferred path — route the task to an OpenCode internal agent within the current session rather than shelling out or calling the HTTP API.

```bash
# Check if running inside an OpenCode session
echo ${OPENCODE_SESSION_ID:+found}
# Alternatively: OPENCODE_CLIENT is set when OpenCode is the executor
echo ${OPENCODE_CLIENT:+found}
```

If in an OpenCode session → **use native dispatch** (route to `general` or `explore` subagent).

If executor is not OpenCode → proceed to Check B.

---

### Check B: HTTP API Server Running?

```bash
curl -s --max-time 3 http://localhost:4096 -o /dev/null -w "%{http_code}"
# Also check custom port if OPENCODE_PORT env var is set
```

If responds (any HTTP code) → **use HTTP API path** (Step 3A). Server is already running.

---

### Check C: CLI Installed?

```bash
which opencode
```

If found → proceed to Check D.

If not found → **no connection available — go to Step 2 (Advisory)**.

---

### Check D: Model Discovery (CLI path only)

```bash
# Discover what OpenCode has configured
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

---

### Non-Interactive Environments

Return `status: HALTED` with the full advisory in `halt_message`. Never silently skip.

---

## Step 3: Read Multi-Model Configuration

Before estimating timeout, check `config/uacp.toml` for the `bridges.opencode.models` array. This controls multi-model dispatch within the bridge.

```bash
# Read from UACP config
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

```yaml
multi_model_dispatch:
  condition: "bridges.opencode.models is present AND has 2+ entries"
  action: "Spawn one execution per model — treat each as an independent participant"
  example_config:
    models: ["glm/glm-4-7", "kimi/moonshot-v1-8k", "qwen/qwen-plus"]

single_model_dispatch:
  condition: "models missing OR empty OR has exactly 1 entry"
  action: "Single execution using tier-resolved model or OpenCode's default"
```

**Why multi-model matters:** Each model has different training data, biases, and reasoning patterns. With 3 models configured, bridge-opencode becomes its own mini-council — 3 independent perspectives before findings even reach the cross-bridge synthesis layer.

---

## Timeout Estimation

Use bridge-commons base timeout table and intensity multiplier, then apply the OpenCode-specific multiplier:

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

## Step 3: Dispatch — Single-Model vs Multi-Model

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

**Post-dispatch: Mini-Synthesis within bridge-opencode**

After all model invocations complete, run a mini-synthesis before returning to the orchestrator:

1. **Deduplication**: Findings with >70% description overlap across models → merge (inherit highest severity, list contributing models as `confirmed_by_models`)
2. **Model-confirmed**: Merged findings are elevated (`intra-bridge_multi_model_confirmed: true`)
3. **Single-model findings**: Retained with model attribution
4. **Verdict**: Apply bridge-commons verdict logic to the merged finding set

This mini-synthesis is the intra-bridge equivalent of the cross-bridge synthesis stage — but lighter (no full DA challenge round, just deduplication and model-agreement detection).

---

### Single-Model Dispatch (when `models` is empty/missing or has 1 entry)

Resolve tier first, then use the tier-mapped model (or the single configured model, or OpenCode's default if none specified).

```bash
# 1. Determine tier (from bridge_input.tier or derive from task_type + intensity)
#    Tier drives task framing, intensity, and timeout only.
# 2. Model selection is delegated to OpenCode:
#    - If bridge_input.model_override is set → use that (provider/model format)
#    - Else if bridges.opencode.models has 1 entry → use that
#    - Else → omit --model, let OpenCode use its configured default
# 3. Set RESOLVED_MODEL (informational only)
```

Proceed to Step 3A or 3B with the resolved model.

---

## Step 3A: Execute via HTTP API (Preferred)

The OpenCode HTTP server exposes a REST API. Use it when the server is already running.

OpenAPI spec available at: `http://localhost:{port}/doc`

### Create a session and send a message

```bash
# Create session
SESSION=$(curl -s -X POST http://localhost:4096/session \
  -H "Content-Type: application/json" \
  -d '{"title": "bridge-review-{session_id}"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Send prompt — use bridge-commons Agent Prompt Template for the constructed_prompt
curl -s -X POST http://localhost:4096/session/$SESSION/message \
  -H "Content-Type: application/json" \
  -d '{
    "content": [{"type": "text", "text": "{constructed_prompt}"}],
    "model": "{RESOLVED_MODEL}"
  }'
```

For the bridge-commons Post-Analysis Protocol, use the same session for each round — the HTTP session maintains full conversation history, so Round 2+ only needs the context packet injected. Run each role as a separate message (or separate session per role for parallelism):

```bash
# Round 2 message — session already has Round 1 history
curl -s -X POST http://localhost:4096/session/$SESSION/message \
  -H "Content-Type: application/json" \
  -d '{
    "content": [{"type": "text", "text": "{role-specific Round N prompt from bridge-commons context packet}"}]
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

selection_strategy:
  - Resolve from tier mapping in config/uacp.toml
  - Or pass the model configured in the caller's context
  - Or use OpenCode default (omit model field)
```

### Authentication (if server has password)

```bash
# With auth: -u opencode:$OPENCODE_SERVER_PASSWORD
curl -s -u opencode:$OPENCODE_SERVER_PASSWORD \
  -X POST http://localhost:4096/session/...
```

### Agent selection (optional)

```bash
# Use the built-in 'plan' agent for read-only analysis
curl -s -X POST http://localhost:4096/session \
  -H "Content-Type: application/json" \
  -d '{"title": "...", "agent": "plan"}'
```

Built-in agents:
- `plan` — restricted, read-only, suited for analysis tasks
- `build` — full tool access (not appropriate for review-only)

---

## Step 3B: Execute via CLI (Fallback)

Build the prompt using the bridge-commons Agent Prompt Template.

```bash
timeout {final_timeout} opencode run "{constructed_prompt}" \
  --format json \
  --model {RESOLVED_MODEL}
```

**Important:** `opencode` (bare) opens the interactive TUI. Always use `opencode run "..."` for programmatic use.

For the Post-Analysis Protocol via CLI, use separate `opencode run` calls per round — no session continuity. Embed the full previous-round outputs and context packet in each Round N prompt (stateless context passing, same pattern as Gemini CLI).

### CLI Error Handling

| Exit code | Meaning | Action |
|-----------|---------|--------|
| 0 | Success | Parse JSON event stream for final message |
| 124 | Timeout | Return SKIPPED, `skip_reason: timeout_after_{n}s` |
| Other | CLI error | Capture stderr, return SKIPPED with detail |

---

## CLI Reference

**Last verified:** 2026-06-07

### Key commands

| Command | Purpose |
|---------|---------|
| `opencode run "<prompt>"` | Non-interactive execution (always use this, not bare `opencode`) |
| `opencode run "<prompt>" --model <provider/model>` | Run with specific model |
| `opencode serve --port 4096` | Start HTTP API server |
| `opencode config get model` | Discover default model |
| `opencode auth list` | List authenticated providers |
| `opencode auth login` | Authenticate a provider |

### HTTP API endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /session` | Create a session |
| `POST /session/{id}/message` | Send a message |

---

## Output

See bridge-commons Output Schema. Bridge-specific fields:

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

Output ID prefix: `O` (e.g., `O001`, `O002`). In multi-model mode, prefix per model: `O-glm-001`, `O-kimi-001`, etc. Merged findings use: `O-merged-001`.

---

## Notes

- **HTTP API is preferred** — use it when `opencode serve` is already running (lower overhead, session continuity)
- **`opencode run` ≠ `opencode`** — bare `opencode` opens the interactive TUI; always use `opencode run "..."` for scripted use
- **Model format is `provider/model`** — e.g., `anthropic/claude-sonnet-4-6`, not just `claude`
- **`plan` agent** is the safe choice for review tasks (read-only mode)
- **1.5× timeout multiplier** always applies (provider routing overhead)
- **HALTED ≠ SKIPPED** — HALTED requires user input before the review can proceed
- **Tier is never hardcoded** — model selections come from `config/uacp.toml`; update the TOML when providers release new models
- **Multi-model config is separate from tier mapping** — `bridges.opencode.models` enables parallel multi-model dispatch; tier mapping selects the default single-model
