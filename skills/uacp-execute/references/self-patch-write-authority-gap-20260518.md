# UACP self-patch write-authority gap — session lesson

## Trigger

Use this reference when EXECUTE touches UACP's own skill files, validators, Guardian/Heartgate runtime adapters, phase-transition config, or other governance/control-plane code.

## Durable finding

A PLAN adaptive-package repair exposed a legitimate Heartgate blocker: the run's `scope.write_paths` included skill, validator, and runtime-adapter source files, but current execute-phase allowed tools did not make those paths reachable under Heartgate's cross-check. The patch source could be applied, but the lifecycle transition could not honestly be claimed as a clean governed PASS.

## Correct handling

Do not convert this into a broad statement like "Heartgate is broken" or "UACP tools cannot patch skills". The useful pattern is narrower:

1. Treat skill/script/runtime-adapter self-patches as a distinct authority class.
2. Ensure the PLAN scope declares the exact write surfaces and the tool/writer expected to reach each one.
3. Before EXECUTE, run Heartgate or equivalent scope cross-check and confirm the declared writer reaches each path.
4. If the cross-check blocks, record an execution checkpoint with `partial_with_heartgate_blocker` or equivalent; do not report clean completion.
5. Either launch a narrow repair track for self-patch write authority or close with explicit accepted warning, owner, residual risk, and next trigger.

## Evidence to preserve

Execution evidence should include:

- patched surfaces;
- deterministic checks run;
- validator fixture results;
- Heartgate decision and exact blockers;
- whether runtime reload/live interception was proven;
- residual owner and next repair path.

## Future repair shape

A proper repair should define a governed route for self-patches touching:

```text
skills/devops/uacp/**
scripts/validate_uacp_artifacts.py
runtime-adapters/**/plugins/uacp_guardian/**
config/phase-transitions.yaml
config/guardian-policy.yaml
```

The repair should not weaken Guardian. It should make authority explicit: which governed writer, contained shell, or reviewed patch path is allowed for each surface, and what evidence proves it.
