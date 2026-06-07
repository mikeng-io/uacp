# Artifact Map

## UACP Lifecycle Artifacts

| Artifact | Location | Phase | Purpose |
|---|---|---|---|
| Triage artifact | `proposals/nora-doctrine-remediation-20260605-170000-triage.yaml` | TRIAGE | UACP admission, routing, granularity |
| Proposal artifact | `proposals/nora-doctrine-remediation-20260605-170000-proposal.yaml` | PROPOSE | Machine lifecycle envelope |
| Gate-selection | `proposals/nora-doctrine-remediation-20260605-170000-gate-selection.yaml` | PROPOSE | Gate selection |
| Proposal package | `proposals/nora-doctrine-remediation-20260605-170000/` | PROPOSE | Human-readable proposal |
| Package selection | `proposals/nora-doctrine-remediation-20260605-170000-package-selection.yaml` | PROPOSE | Package selection |

## Proposal Package Documents

| Document | Location | Purpose |
|---|---|---|
| Index | `proposals/nora-doctrine-remediation-20260605-170000/00-index.md` | Overview and navigation |
| Proposal | `proposals/nora-doctrine-remediation-20260605-170000/proposal.md` | Main proposal: what, why, how |
| Authority/Scope | `proposals/nora-doctrine-remediation-20260605-170000/authority-scope-containment.md` | Authority, scope, containment |
| Risks/Verification | `proposals/nora-doctrine-remediation-20260605-170000/risks-and-verification.md` | Risks and verification criteria |
| Artifacts | `proposals/nora-doctrine-remediation-20260605-170000/artifacts.md` | This document |

## Council Evidence

| Artifact | Location | Purpose |
|---|---|---|
| Council synthesis | `/home/norty/.hermes/profiles/nora/EXPERTS_COUNCIL_SYNTHESIS.json` | Structured synthesis |
| Council report | `/home/norty/.hermes/profiles/nora/COUNCIL_REPORT.md` | Human-readable report |

## Gate Ledger

| Artifact | Location | Purpose |
|---|---|---|
| Gate ledger | `state/gate-ledger/nora-doctrine-remediation-20260605-170000.jsonl` | Gate transitions |

## Target Files (to be modified in EXECUTE)

| File | Location | Changes |
|---|---|---|
| KERNEL.md | `/home/norty/.hermes/profiles/nora/KERNEL.md` | Add doctrinal grant |
| SECURITY.md | `/home/norty/.hermes/profiles/nora/SECURITY.md` | Add authority tier, carve out |
| SOUL.md | `/home/norty/.hermes/profiles/nora/SOUL.md` | Update "must not reveal" rule |
| IDENTITY.md | `/home/norty/.hermes/profiles/nora/IDENTITY.md` | Carve out identity-registry context |
| PERSONALITY.md | `/home/norty/.hermes/profiles/nora/PERSONALITY.md` | Add language/tone precedence |
| Plugin __init__.py | `/home/norty/.hermes/profiles/nora/plugins/identity_registry/__init__.py` | Tighten safe card, add schema validation |
| Plugin plugin.yaml | `/home/norty/.hermes/profiles/nora/plugins/identity_registry/plugin.yaml` | Update if needed |
| Registry engine | `/home/norty/.hermes/operator-data/nora/identity-registry/identity_registry.py` | Add schema validation, health check |

## Transition Meaning

**PROPOSE → PLAN:** Proposal is viable, scope is bounded, authority is granted. PLAN must define exact file changes, test commands, rollback path, and audit roles.

**PLAN → EXECUTE:** Plan is complete, work packages defined. EXECUTE must not restart gateway unless Mike explicitly approves after VERIFY.

**EXECUTE → VERIFY:** Implementation complete, tests pass. VERIFY must confirm doctrine consistency, security posture, and behavioral verification.

**VERIFY → RESOLVE:** Verification complete, all findings resolved. RESOLVE must extract lessons and decide on next steps.
