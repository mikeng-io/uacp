# Doctrine Delta

## From
PLAN may be represented primarily as:

```text
plans/{run_id}-plan.yaml
plans/{run_id}-scope.yaml
```

This encourages YAML compression.

## To
Serious PLAN work is represented as an adaptive package:

```text
plans/{run_id}/                  # human reasoning package
plans/{run_id}-plan.yaml         # lifecycle envelope
plans/{run_id}-scope.yaml        # scope contract
plans/{run_id}-plan-selection.yaml # bridge to validator/Heartgate
```

## PLAN-specific rule
PROPOSE decides viability. PLAN designs execution topology. EXECUTE performs mutations. PLAN must not execute work.

## Granularity rule
Granularity scales rigor, evidence depth, and review pressure. It does not impose a fixed file list.

## Bridge rule
Markdown explains. YAML enforces. `plan-selection.yaml` bridges.
