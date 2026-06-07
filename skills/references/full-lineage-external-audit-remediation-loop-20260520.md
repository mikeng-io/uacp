# Full-lineage external audit remediation loop

Use when Mike asks Kimi Code and Codex to audit UACP lifecycle/governance changes, especially after a multi-commit hardening series.

## Core lesson

Do not scope external audits to only the latest remediation commit unless Mike explicitly asks for that. For UACP governance/lifecycle changes, the correct audit unit is usually the **full lineage of related changes** and the end-to-end lifecycle coherence across PROPOSE → PLAN → EXECUTE → VERIFY → RESOLVE.

A narrow prompt like "verify whether commit X closes findings from commit Y" is useful as a follow-up check, but it is not a substitute for a full lifecycle audit.

## Required prompt shape

External Kimi/Codex prompts should require:

- read-only audit;
- repository ground truth over assistant summaries;
- explicit internal Agent Council / multi-role reasoning;
- devil's advocate / false-pass role;
- lifecycle consistency historian role;
- dependency readiness role;
- full change-lineage scope, listing relevant commits when known;
- surfaces across docs, config, validator, runtime, fixtures, active skill exports, state, and real artifacts;
- explicit closure matrix by lifecycle phase and runtime/skill surfaces;
- whether downstream governed work may safely depend on the result.

Minimum council roles:

1. Lifecycle governance reviewer.
2. Validator/runtime enforcement auditor.
3. Heartgate/Guardian security reviewer.
4. Adversarial devil's advocate / false-pass reviewer.
5. Operator-handoff / semantic-recovery reviewer.
6. Lifecycle consistency historian.
7. Dependency readiness reviewer.

## Remediation pattern

When external auditors return findings, patch root causes across all authoritative surfaces, not just the visible failing fixture:

1. Runtime enforcement — Guardian/Heartgate behavior.
2. Offline validator — same false-pass class must block offline too.
3. Config/schema — canonical contract must match runtime requirements.
4. Fixtures — add positive and negative regression cases.
5. Runtime smoke harness — assert actual `evaluate()` decisions where relevant, not only helper predicates.
6. Active skill exports — fix live `~/.hermes/skills/...` references separately from repo docs.
7. State/source-of-truth — reconcile current state when it contradicts doctrine.
8. Docs/trace tables — remove stale links and terminology drift.

Then run internal adversarial follow-up. If it returns CONCERNS/FAIL, patch again and rerun until PASS.

## Specific pitfalls from the 2026-05-20 audit

- Guardian path binding must account for `workspace`, `cwd`, `workdir`, `$UACP_ROOT`, `$HOME`, and relative shell paths like `touch state/x` or `touch uacp/state/x`.
- For protected shell checks, assert `Guardian.evaluate()` blocks, not merely that `is_uacp_bound()` returns true.
- Heartgate accepted warning exceptions must bind by both `artifact_path` and `cluster_id`; require `accepted_by`, owner, rationale, next-phase acceptance, and an existing **run-bound** evidence path.
- Do not allow accepted exceptions to cite arbitrary existing `verification/` or `..outputs/` files from another run.
- Offline `uacp.phase_transition` validation should invoke the same linked adaptive artifact checks that Heartgate relies on; otherwise agents can claim "validator passed" for a transition Heartgate would block.
- RESOLVE closure must deep-validate VERIFY readiness and carry forward residual risks/deferred items from readiness and resolve package.
- PIV pass evidence must reference existing, run-bound artifacts; if a plan PIV exists, VERIFY must provide the PIV assessment.
- Unknown `uacp.*` artifact kinds should block rather than silently pass.
- `state/current.yaml` pointers should be exact run-token/prefix bound, not substring-bound.
- Runtime smoke tests should use a temporary copied UACP root or otherwise prove they leave no repo state residue.
- Add/check an active skill-export link checker when auditors find stale `UACP_ROOT/...` or `../references/...` paths.

## Verification bundle

A robust pass should include at least:

```bash
python -m py_compile \
  scripts/validate_uacp_artifacts.py \
  runtime-adapters/hermes/plugins/uacp_guardian/kernel.py \
  verification/fixtures/heartgate-runtime/run_heartgate_runtime_smoke.py \
  scripts/check_active_uacp_skill_links.py
python scripts/validate_uacp_artifacts.py --root .
python verification/fixtures/heartgate-runtime/run_heartgate_runtime_smoke.py
python scripts/check_active_uacp_skill_links.py
# negative sweep across adaptive execute/verify/resolve and heartgate fail fixtures
```

Finish with a concise operator report: commit SHA, pushed/clean state, findings closed, validation evidence, and whether external follow-up remains pending.
