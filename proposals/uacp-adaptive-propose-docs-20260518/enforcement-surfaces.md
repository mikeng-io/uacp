# Enforcement Surfaces

Doctrine alone is insufficient. The adaptive documentation model must be wired into operational surfaces during PLAN/EXECUTE.

This document identifies downstream patch targets. It does **not** claim those patches are already complete in PROPOSE.

## Enforcement sequence

1. PROPOSE selects required concerns and modules.
2. Council reviews whether selection is sufficient.
3. PLAN converts selected enforcement work into bounded patch tranches.
4. EXECUTE applies patches.
5. VERIFY proves validator/Heartgate behavior with fixtures.

## Skill layer

Downstream patch target:

- `uacp-propose/SKILL.md`
- `uacp-propose/references/modular-proposal-package.md`

Expected behavior:

- require adaptive package selection for serious work;
- reject YAML-only serious proposals;
- reject fixed document quotas;
- require selected concerns to be reviewed before PROPOSE→PLAN.

## Transition config

Downstream patch target: `config/phase-transitions.yaml`.

Expected behavior:

- add PROPOSE package readiness gate;
- require package-selection artifact when selected;
- block missing selected concerns;
- block weak not-applicable rationale;
- treat YAML-only serious proposals as incomplete.

## Validator

Downstream patch target: `scripts/validate_uacp_artifacts.py`.

Expected behavior:

- validate package-selection artifact shape;
- validate universal core coverage;
- validate selected module artifact existence;
- validate not-applicable rationale.

## Heartgate

Downstream patch target: Heartgate transition expectation for PROPOSE→PLAN.

Expected behavior:

- require package readiness evidence for selected medium/high consequence work;
- block transition artifacts that cite only YAML metadata for serious work.

## Guardian

Downstream patch target: `config/guardian-policy.yaml`.

Expected behavior:

- clarify adaptive proposal package artifacts under `proposals/<run_id>/` and top-level package-selection exports are governed UACP artifact writes;
- preserve path containment.
