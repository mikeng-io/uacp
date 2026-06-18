# Intensity Modes and Parameter Presets

## Intensity Modes

```yaml
quick:
  phases: [1, 2, 5]      # Skip challenge and synthesis
  max_rounds: 0
  budget: "reviewer_count + 5 tasks"

standard:
  phases: [1, 2, 3, 4, 5]  # All phases
  max_rounds: 3
  budget: "3 * reviewer_count + 10 tasks"

thorough:
  phases: [1, 2, 3, 4, 5]  # All phases, extended
  max_rounds: 5
  budget: "5 * reviewer_count + 10 tasks"
```

## Round-State Mechanism

- **`quick`** — single in-memory pass (phases 1, 2, 5; `max_rounds: 0`). Writes
  NO `manifest.json` and NO `round-k/` directories. Only the final timestamped
  artifacts are written.
- **`standard` / `thorough`** — file-based round state per
  `references/round-state-manifest.md`. Each round persists to
  `.uacp/debate/{review_id}/round-k/`, durable state lives in `manifest.json`,
  and the coordinator hands out file POINTERS to the next round's sub-agents
  instead of re-embedding the inventory in every prompt.

## Parameter Presets

```yaml
default:
  da_weight: 0.40           # Devil's Advocate finding weight
  consensus_threshold: 0.50  # Fraction needed for "confirmed"
  security_threshold: 0.67   # Higher bar for security findings

security-elevated:
  da_weight: 0.50
  consensus_threshold: 0.67
  security_threshold: 0.75
```
