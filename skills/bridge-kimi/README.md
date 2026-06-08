# Bridge: Kimi Code CLI

Reference adapter for Kimi Code CLI dispatch. Part of the UACP bridge layer.

## What is this?

A **reference document** read by any orchestrating skill via the `Read` tool. Instructions are embedded into Task agent prompts for bridge execution.

## Connection Method

CLI: `kimi -p "..." --output-format json`

ACP server (advanced): `kimi acp` — Agent Client Protocol over stdio.

## Availability

Conditional — requires `kimi` CLI to be installed and in PATH.

Availability check: `which kimi` or check common install locations:
- `$HOME/.kimi-code/bin/kimi`
- `$HOME/.local/bin/kimi`
- `/usr/local/bin/kimi`

If not available → bridge returns `SKIPPED` (non-blocking).

## Auth

Kimi Code uses OAuth device-code flow. Check status:
```bash
kimi login status
```

If not authenticated → bridge returns `HALTED` with advisory to run `kimi login`.

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
- Empty output
- JSON parse failure

Returns `status: HALTED` on:
- Not authenticated

Never blocks or throws — always returns a report.

## Part of

- UACP Bridge Adapter Suite
- Consumed by: any orchestrating skill (e.g., `agent-council`, lifecycle skills, or custom skills)
- Depends on: `bridge-commons`, `domain-registry`
