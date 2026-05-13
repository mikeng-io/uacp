# 14 — Validator Hardening And Fixtures

Status: implemented in manual-drill validator  
Scope: `scripts/validate_uacp_artifacts.py`

## Decision

The lightweight validator remains a **manual-drill validator** for now. It is not a substitute for Guardian/Heartgate and is not yet a production dependency.

## Added coverage

The validator now checks:

- YAML parseability for core configs and provided artifacts.
- Canonical finding states: `open`, `resolved`, `accepted_risk`, `not_applicable`, `deferred`.
- Phase transition required fields, decisions, and terminal vocabulary.
- Council synthesis required fields and verdict vocabulary.
- Gate-selection artifacts for required metadata, invariant status shape, selected cluster states, and reasoning.
- EXECUTE task artifacts for required top-level fields, runtime surface vocabulary, scope boundaries, side-effect declaration, verification, and completion sections.
- Evidence cluster artifacts for required fields and canonical cluster state vocabulary.
- Evidence-Domain Registry honesty: warn if claimed active without verified selector.

## Sample commands

```bash
python3 scripts/validate_uacp_artifacts.py --root UACP_ROOT verification/*.yaml
python3 scripts/validate_uacp_artifacts.py --root UACP_ROOT proposals/*.yaml verification/*.yaml executions/*.yaml
```

In this runtime, ordinary shell execution under UACP may be blocked by Guardian context requirements. If a manual drill uses an alternate path, the verification artifact must record that as a known enforcement gap, not as normal enforcement.

## Fixture guidance

Future fixture files should live under `knowledge/validator-fixtures/` and include:

- one passing phase transition,
- one failing phase transition missing `phase_local_granularity`,
- one passing council synthesis,
- one failing council synthesis with invalid finding state,
- one passing execute task,
- one failing execute task with invalid `runtime.surface`,
- one gate-selection artifact with an invariant status other than `pass|block`.

Fixtures are deferred because this run's acceptance target is validator coverage plus documented sample commands, not a full pytest-style fixture suite.
