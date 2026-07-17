# S1 Smoke Summary — hermes-bare pipeline check

- Generated: 2026-07-17T19:46:24.499879+00:00
- Cell: `hermes-bare`  Task: `hello-file`  Model: `qwen3.5:4b`
- Replicates (N): 5  Per-replicate timeout: 240s
- Output: `/Users/mike/Workplace/uacp/.worktrees/pg-s1/tools/proving-ground/records/smoke-out`

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
| 22.924 | 7.182 | 17.868 | 34.978 | 8.916 |

Per-replicate records: `/Users/mike/Workplace/uacp/.worktrees/pg-s1/tools/proving-ground/records/smoke-out/replicates.jsonl`

Aggregate JSON: `/Users/mike/Workplace/uacp/.worktrees/pg-s1/tools/proving-ground/records/smoke-out/aggregate.json`

