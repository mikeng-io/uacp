# Bridge: OpenCode

Reference adapter for OpenCode — model-agnostic multi-provider bridge. Part of the Deep Skills Suite bridge layer.

## What is this?

A **reference document** read by any orchestrating skill via the `Read` tool. Instructions are embedded into Task agent prompts for bridge execution.

## Why OpenCode?

OpenCode is provider-agnostic — it routes to whichever AI providers are configured (Anthropic, OpenAI, Google, GLM, Qwen, etc.). A single OpenCode call gives a multi-provider perspective without configuring each provider separately.

**Trade-off:** 1.5× timeout multiplier applies because model calls go through OpenCode's provider routing layer.

## Connection Methods (Preference Order)

| Priority | Method | When Available |
|----------|--------|---------------|
| 1 (preferred) | HTTP API (`http://localhost:4096`) | `opencode serve` is already running |
| 2 (fallback) | CLI (`opencode run "prompt"`) | `which opencode` + provider configured |
| — | Advisory + halt | Neither configured |

Unlike other bridges, OpenCode **halts** (not silently skips) when not available, prompting the user to install or configure it.

## Pre-Flight Checks

1. **HTTP server running?** `curl --max-time 3 http://localhost:4096` → any response means use HTTP API
2. **CLI installed?** `which opencode` → found: check provider
3. **Provider configured?** `opencode auth list` → at least one authenticated provider

If checks 2 and 3 both fail → halt with interactive advisory offering: install / start server / skip / abort.

## HTTP API Path (Preferred)

When `opencode serve` is running at `:4096`:

```bash
# Create session with 'plan' agent (read-only)
SESSION=$(curl -s -X POST http://localhost:4096/session \
  -H "Content-Type: application/json" \
  -d '{"title": "review", "agent": "plan"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Send prompt
curl -s -X POST http://localhost:4096/session/$SESSION/message \
  -H "Content-Type: application/json" \
  -d '{"content": [{"type": "text", "text": "..."}], "model": "provider/model"}'
```

**Model format:** `provider/model` — e.g., `anthropic/claude-sonnet-4-20250514`, `openai/gpt-4o`, `google/gemini-2.0-flash`. Omit model field to use server default.

**Built-in agents:**
- `plan` — read-only, suited for review and analysis tasks (use this)
- `build` — full tool access (not appropriate for review-only)

## CLI Path (Fallback)

```bash
opencode run "{prompt}" \
  --format json \
  --model {provider/model} \
  --agent plan
```

Note: `opencode` (bare) opens the interactive TUI. Always use `opencode run "..."` for programmatic use.

## Timeout Calculation

`final_timeout = base_scope_timeout × 1.5 × intensity_multiplier`

| Scope | Base Timeout |
|-------|-------------|
| < 5 files / 500 LOC | 60s |
| 5-20 files / 2k LOC | 180s |
| 20-50 files / 10k LOC | 300s |
| 50+ files / 10k+ LOC | 600s |

Intensity: quick=0.5×, standard=1.0×, thorough=1.5×

## Status Values

| Status | Meaning |
|--------|---------|
| `COMPLETED` | Review ran, findings returned |
| `SKIPPED` | Non-fatal error (timeout, parse failure) |
| `HALTED` | Pre-flight failed — needs user input |
| `ABORTED` | User chose to abort |

**HALTED ≠ SKIPPED** — HALTED blocks until the user makes a choice.

## Part of

- Deep Skills Suite
- Consumed by: any orchestrating skill (e.g., `deep-council`, `deep-review`, `deep-audit`, or custom skills)
