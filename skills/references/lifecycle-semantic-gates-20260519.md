# UACP lifecycle semantic gates — session reference

Use this reference when hardening UACP lifecycle phases or auditing whether a phase is genuinely complete.

## Core corrections from the session

- **PIV means Phase Intent Verification**, not Phase Implementation Verification. EXECUTE can be code, docs, config, artifact generation, council dispatch, migration prep, runtime probe, state transition, or handoff. Use neutral vocabulary: `work_units`, `produced_outputs`, `work_narrative`.
- Do not claim lifecycle hardening is complete after only PROPOSE/PLAN/EXECUTE. VERIFY and RESOLVE are first-class governance phases and need their own gates.
- VERIFY is the truth boundary before RESOLVE. It must separate verified facts from assumptions/deferred items, assess PIV satisfaction, prevent self-approval, and produce run-bound resolve readiness.
- RESOLVE is closure, not a second VERIFY. It consumes VERIFY readiness and proves final closure, residual-risk preservation, lessons/dispositions, state/memory/skill/doc decisions, and operator handoff.

## Preferred workflow for governance-core phase hardening

For high-impact phases like VERIFY and RESOLVE, do not implement first. Use:

1. Retrieval-led gap audit grounded in repo files.
2. Pre-design council to define constraints and must-block cases.
3. Implement docs/config/validator/fixtures/skills.
4. Deterministic validation.
5. Post-implementation council and adversarial audit.
6. Patch findings.
7. Focused follow-up council until PASS.
8. Commit/push only after validation and council closure.

For clearer, lower-risk gaps such as EXECUTE PIV binding, implementation before council can be acceptable, but VERIFY/RESOLVE deserve pre-design council.

## Gate expectations by phase

- **PROPOSE / PLAN**: semantic package directory and `00-index.md`; non-empty selected modules; artifacts under canonical package directory.
- **EXECUTE**: PLAN-authored Phase Intent Verification contract; checkpoints bind to work units and evidence obligations; semantic execution package; drift/deviation disposition.
- **VERIFY**: verification package, PIV assessment when applicable, verified facts with source evidence, assumptions/deferred items with owner/acceptance/condition, self-approval guard, Heartgate coherence when required, run-bound resolve readiness.
- **RESOLVE**: closure package under `..outputs/{run_id}/`, final decision, residual-risk/deferred-item preservation, lesson disposition (`memory|skill|docs|knowledge|no_action`), state/memory disposition, concise operator handoff, artifact-bound closed scope.

## Fixture discipline

Each gate should include positive fixtures and expected-fail negatives for stale/unbound artifacts, missing package/index, dropped risks, invalid enums, missing owners/acceptance, fake readiness, raw operator handoff, and self-approval bypasses.

## External audit pattern

When asking Kimi/Codex for full audit, run read-only with a command-level timeout (for example `timeout 45m ...`) and background process tracking. If a provider-specific model is rejected, retry with the default supported model rather than treating the runtime as unavailable. Do not persist environment-specific auth failures as doctrine; capture only the retry/fallback pattern.