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
