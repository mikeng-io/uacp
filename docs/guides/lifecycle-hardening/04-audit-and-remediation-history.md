---
type: guide
tags: [audit-history, codex, kimi, remediation, lifecycle-hardening]
status: living-document
canonical_authority: false
---

# Audit and Remediation History

This file preserves the reasoning shape of the lifecycle-hardening audit loop without replacing git history, ADRs, or verification artifacts.

## Why external audits were required

The lifecycle work affected governance boundaries, runtime enforcement, protected-state behavior, active skill exports, and future dependency readiness. Internal validation alone was not enough. Kimi and Codex were asked to perform full-lineage audits with internal Agent Councils and devil’s advocate roles.

The important shift was from “did the latest commit close a finding?” to “does the whole lifecycle cohere from PROPOSE through RESOLVE?”

## Audit themes

The audits looked for:

- documentation/config/runtime drift,
- validator and Heartgate disagreement,
- Guardian path-binding bypasses,
- warning exception laundering,
- PIV self-certification,
- VERIFY self-approval,
- RESOLVE dropping risks or deferred items,
- unknown `uacp.*` artifact kinds,
- active skill reference rot,
- state/current source-of-truth conflicts,
- runtime smoke tests that polluted real repo state.

## Material remediation in `c28da46`

The full-lineage remediation commit closed the combined audit findings by:

- expanding Guardian path extraction to include workspace, cwd/workdir-relative paths, and `$UACP_ROOT`,
- binding accepted exceptions by artifact path and cluster ID,
- requiring accepted exception evidence to be run-bound,
- making phase-transition validation invoke linked adaptive gate artifacts,
- deep-validating VERIFY readiness during RESOLVE closure,
- requiring closure to carry forward residual risks and deferred items,
- blocking unknown `uacp.*` artifact kinds,
- requiring PIV pass evidence to exist and be run-bound,
- reconciling `state/current.yaml` to the governed current-pointer model,
- adding an active skill-link checker,
- changing the Heartgate runtime smoke harness to use a temporary copied root.

## Verification used before commit

The remediation passed:

```bash
python -m py_compile   scripts/validate_uacp_artifacts.py   runtime-adapters/hermes/plugins/uacp_guardian/kernel.py   verification/fixtures/heartgate-runtime/run_heartgate_runtime_smoke.py   scripts/check_active_uacp_skill_links.py

python scripts/validate_uacp_artifacts.py --root .
python verification/fixtures/heartgate-runtime/run_heartgate_runtime_smoke.py
python scripts/check_active_uacp_skill_links.py
```

It also passed negative sweeps across adaptive EXECUTE, VERIFY, RESOLVE, and Heartgate runtime fail fixtures.

## Review result

An internal lifecycle review passed. A focused adversarial follow-up initially found two residual risks: arbitrary existing-file warning exceptions and substring-bound current-state pointers. Those were fixed before commit, and the final focused adversarial check returned PASS.

## Documentation lesson

The audit history should not be scattered across operator chat, commit messages, and random reference files. Use this guide for the human narrative, ADRs for decisions, fixtures for regression proof, and git history for exact diffs.
