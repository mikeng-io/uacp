# S1 Smoke Summary — hermes-bare pipeline check

- Generated: 2026-07-19T18:21:00.420206+00:00
- Cell: `hermes-bare`  Task: `hello-file`  Model: `qwen3.5:4b`
- Replicates (N): 5  Per-replicate timeout: 240s
- Output: `records/smoke-out` (relative to `tools/proving-ground/`)

This is a pipeline check against the cheap smoke tier — outcomes only, no scoring (oracles arrive at S3+). It confronts the data-handling reality and the wall-clock bill before any scored sweep exists (40-benchmark's statistics law, built at S1).

## Outcomes

| outcome | count |
|---|---|
| completed | 5 |
| timeout | 0 |
| error | 0 |

## Wall-clock (seconds)

| mean | stdev | min | max | ci95 half-width |
|---|---|---|---|---|
| 28.953 | 6.358 | 22.311 | 35.806 | 7.893 |

Per-replicate records: `records/smoke-out/replicates.jsonl`

Aggregate JSON: `records/smoke-out/aggregate.json`

