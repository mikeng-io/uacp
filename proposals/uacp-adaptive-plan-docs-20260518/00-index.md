# UACP Adaptive PLAN Package — Index

Run: `uacp-adaptive-plan-docs-20260518`

Status: PROPOSE draft.

## Purpose
Patch UACP PLAN so serious PLAN work is package-first and adaptive, not compressed into one YAML plan artifact.

## Documents
- `proposal.md` — intent and proposed change.
- `authority-scope-containment.md` — authority, in/out scope, containment.
- `doctrine-delta.md` — doctrine change from YAML-first PLAN to package-first PLAN.
- `adaptive-plan-package-model.md` — PLAN-specific package model and universal core.
- `plan-selection-schema.md` — bridge YAML schema for plan package selection.
- `enforcement-surfaces.md` — validator, Heartgate, Guardian, fixtures.
- `trustless-openspec-distillation.md` — reference evidence distilled without copying.
- `risks-and-verification.md` — risks, tests, and council requirements.
- `decision-journal.md` — material decisions and reversals.
- `artifacts.md` — artifact map and envelope/package distinction.
- `machine/package-selection.yaml` — proposal package bridge artifact.

## Core rule
A UACP PLAN is an adaptive execution package. `plans/{run_id}-plan.yaml` is a machine lifecycle envelope only.
