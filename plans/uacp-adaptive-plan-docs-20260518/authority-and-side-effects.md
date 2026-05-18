# Authority and Side Effects

## Authority
Mike authorized the run with `Go`.

## Allowed local writes
- UACP skill export: `/home/norty/.hermes/skills/devops/uacp/uacp-plan/SKILL.md`
- UACP config: `config/phase-transitions.yaml`, `config/guardian-policy.yaml`
- UACP validator/runtime source: `scripts/validate_uacp_artifacts.py`, `runtime-adapters/hermes/plugins/uacp_guardian/kernel.py`
- UACP artifacts/fixtures under `plans/`, `verification/`, `outputs/`.

## Forbidden
- External network writes, pushes, PRs.
- Production changes.
- UACP protected state mutation outside UACP state/ledger tools.
- LEXA work.

## Containment caveat
Use UACP governed writers where practical. If code patching requires normal patch tooling, record the bootstrapping exception and verify diffs/tests.
