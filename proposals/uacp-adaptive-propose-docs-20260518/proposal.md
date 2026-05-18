# Proposal

## Problem

UACP PROPOSE can currently be interpreted as valid when it emits only machine/governance YAML records: triage, proposal, gate-selection, and council synthesis. That is too thin for serious work.

The first attempted fix overcorrected toward a fixed OpenSpec-like document checklist. That is also wrong: UACP is universal and adaptive, not a coding-spec workflow.

## Objective

Define and enforce adaptive proposal documentation selection for UACP PROPOSE:

- Markdown/human artifacts explain intent, authority, scope, risk, and selected modules.
- YAML/machine artifacts enforce lifecycle, gates, selected concerns, and readiness.
- `package-selection.yaml` bridges the two.
- Granularity scales rigor, but context/the work's heart selects documentation modules.

## Impact

After this patch, medium/high consequence work cannot advance from PROPOSE to PLAN with YAML-only records. It also cannot be blocked merely for lacking OpenSpec-style filenames when the necessary concerns are covered elsewhere.

## Non-goals

- Do not resume LEXA implementation.
- Do not import OpenSpec or Trustless ACP as UACP authority.
- Do not create fixed document quotas by granularity.
- Do not collapse PROPOSE into PLAN.
