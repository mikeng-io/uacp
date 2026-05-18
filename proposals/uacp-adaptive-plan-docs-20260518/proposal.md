# Proposal

## Objective
Make UACP PLAN package-first for medium/high consequence work.

## Problem
Current PLAN artifacts are too easy to compress into `plans/{run_id}-plan.yaml` plus `scope.yaml`. That gives machines a contract, but hides execution topology, dependency reasoning, runtime/tool selection, rollback, verification strategy, and council topology inside one envelope.

## Proposed change
Introduce adaptive PLAN packages:

```text
plans/{run_id}/                  # human-reviewable PLAN package
plans/{run_id}-plan.yaml         # machine lifecycle envelope only
plans/{run_id}-scope.yaml        # machine scope contract
plans/{run_id}-plan-selection.yaml # bridge/check artifact
```

## Non-copy rule
OpenSpec and Trustless ACP are evidence only. UACP must distill their discipline without inheriting fixed filenames, Trustless worktrees/state paths, or OpenSpec's proposal/design/specs/tasks topology.

## Success condition
PLAN package-selection is validated by deterministic validator and checked by Heartgate for PLAN→EXECUTE where selected. Guardian policy recognizes adaptive PLAN package artifacts as UACP artifacts.
