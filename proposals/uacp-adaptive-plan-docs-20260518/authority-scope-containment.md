# Authority, Scope, Containment

## Authority
Authorized by Mike in current Telegram thread: `Go`.

## In scope
- `skills/devops/uacp/uacp-plan/SKILL.md`
- `config/phase-transitions.yaml`
- `scripts/validate_uacp_artifacts.py`
- `runtime-adapters/hermes/plugins/uacp_guardian/kernel.py`
- `config/guardian-policy.yaml`
- `verification/fixtures/adaptive-plan-package/`
- Optional alignment docs if inspection proves drift.

## Out of scope
- EXECUTE/VERIFY/RESOLVE package refactors.
- LEXA PLAN or implementation work.
- Public/external actions, pushes, PRs, production changes.
- Treating OpenSpec or Trustless ACP as authority.

## Containment
Use UACP artifact/config/doc writers where practical for canonical UACP outputs. If bootstrapping requires normal file tools, record residual risk and verify diffs. Do not mutate protected state except through UACP state/ledger tools.

## Side effects
Local UACP artifact/config/skill/runtime-adapter source edits only. No external network writes.
