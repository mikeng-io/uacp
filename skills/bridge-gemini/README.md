# Bridge: Gemini

Reference adapter for Gemini CLI. Part of the Deep Skills Suite bridge layer.

## What is this?

A **reference document** read by any orchestrating skill via the `Read` tool. Instructions are embedded into Task agent prompts for bridge execution.

## Connection Method

CLI only: `gemini -p "..." --approval-mode plan -o json`

## Availability

Conditional — requires `gemini` CLI to be installed and in PATH.

Availability check: `which gemini`

If not available → bridge returns SKIPPED (non-blocking).

## Timeout Estimation

Calculated dynamically from review scope (number of files / LOC) × intensity multiplier. Never hardcoded.

| Scope | Base Timeout |
|-------|-------------|
| < 5 files / 500 LOC | 60s |
| 5-20 files / 2k LOC | 180s |
| 20-50 files / 10k LOC | 300s |
| 50+ files / 10k+ LOC | 600s |

Intensity multipliers: quick=0.5×, standard=1.0×, thorough=1.5×

## Fallback

Returns `status: SKIPPED` on:
- CLI not found
- Timeout exceeded
- CLI error
- JSON parse failure

Never blocks or throws — always returns a report.

## Part of

- Deep Skills Suite
- Consumed by: any orchestrating skill (e.g., `deep-council`, `deep-review`, `deep-audit`, or custom skills)
