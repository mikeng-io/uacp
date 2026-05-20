---
type: guide
tags: [artifact-map, gates, validator, heartgate, guardian]
status: living-document
canonical_authority: false
---

# Artifact and Gate Map

This map shows where meaning and enforcement live after the lifecycle hardening series. It is a guide; the canonical transition table is `docs/reference/lifecycle-trace-table.md`.

## Phase artifact pattern

| Phase | Machine envelope | Semantic package | Main enforcement |
|---|---|---|---|
| PROPOSE | proposal and package-selection YAML | `proposals/{run_id}/` | semantic package validator |
| PLAN | plan/package-selection YAML and PIV contract | `plans/{run_id}/` | plan package validator + PIV contract validator |
| EXECUTE | execution checkpoint YAML | `executions/{run_id}/` | PIV obligation validation + Heartgate EXECUTE gate |
| VERIFY | verify-selection, PIV assessment, resolve-readiness YAML | `verification/{run_id}/` | verification package validator + self-approval guard |
| RESOLVE | resolve-selection and closure YAML | `outputs/{run_id}/` | readiness/closure carry-forward validator + Heartgate RESOLVE gate |

## Key enforcement files

- `scripts/validate_uacp_artifacts.py` — offline artifact validation and linked transition checks.
- `runtime-adapters/hermes/plugins/uacp_guardian/kernel.py` — Guardian path binding and Heartgate transition runtime gates.
- `config/phase-transitions.yaml` — declarative phase and gate policy.
- `config/state.yaml` — state/current pointer schema.
- `state/current.yaml` — current governed state pointer.

## Fixture areas

Positive and negative fixtures are part of the contract. Do not remove them because they look artificial.

- `verification/fixtures/adaptive-execute-evidence/negative/`
- `verification/fixtures/adaptive-verify-evidence/negative/`
- `verification/fixtures/adaptive-resolve-closure/negative/`
- `verification/fixtures/heartgate-runtime/`

The Heartgate runtime smoke harness is:

```text
verification/fixtures/heartgate-runtime/run_heartgate_runtime_smoke.py
```

It runs against a temporary copied UACP root so fixture ledgers do not pollute real repo state.

## Critical invariants

### Semantic package invariant

Markdown package artifacts are mandatory semantic substrate for non-trivial governed work. They are not optional decoration. They must contain enough intent, rationale, evidence, decisions, and handoff context for future recovery.

### PIV invariant

PIV means Phase Intent Verification. It is not implementation-specific. PLAN defines what EXECUTE must prove; EXECUTE records evidence; VERIFY judges whether the intent was satisfied.

### VERIFY / RESOLVE separation

VERIFY is the truth gate. RESOLVE is the closure gate. RESOLVE may consume verified truth and carry forward unresolved items; it must not silently re-verify or drop risk.

### Runtime parity invariant

Offline validation and Heartgate runtime validation must not disagree on material transition truth. If a Heartgate fail fixture passes the offline validator, that is a bug.

### Path-binding invariant

Guardian must bind protected UACP writes even when the path appears only inside a shell command, an environment variable, a workspace, or a cwd-relative path.

### Run-binding invariant

Evidence used to satisfy a run must be bound to that run. Existing unrelated files cannot be used to launder warnings, exceptions, PIV evidence, or closure evidence.
