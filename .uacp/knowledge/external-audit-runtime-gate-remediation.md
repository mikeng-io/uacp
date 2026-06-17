---
type: pattern
title: External Audit Runtime Gate Remediation
description: Pattern for closing external auditor findings when docs/config pass but runtime enforcement is incomplete
tags: [audit, runtime, remediation, guardian]
timestamp: 2026-06-17
---

# External audit remediation pattern for UACP lifecycle gates

Use this reference when an external auditor (Codex/Kimi/etc.) reviews UACP lifecycle hardening and finds that docs/config/offline validators pass but runtime enforcement is incomplete.

## Core lesson

Do not claim UACP phase hardening is complete just because docs, config, fixtures, and `scripts/validate_uacp_artifacts.py` pass. For lifecycle gates, completion requires the corresponding runtime path to enforce the gate too, especially Heartgate transition validation.

## Required audit closure surfaces

For adaptive phase gates, verify all of these separately:

1. **Doctrine/docs** — ADR/reference explains phase intent and invariants.
2. **Config** — `config/phase-transitions.yaml` declares the gate and selection policy.
3. **Offline validator** — `scripts/validate_uacp_artifacts.py` validates positive and negative fixtures.
4. **Runtime Heartgate** — `runtime-adapters/hermes/plugins/uacp_guardian/kernel.py` enforces the gate during transition validation.
5. **Fixtures/smoke tests** — include positive and negative transition fixtures that prove Heartgate blocks missing runtime artifacts.
6. **Active skill exports** — if active skill-store copies exist outside git, sync or record them as an explicit residual risk.
7. **External/focused review** — run focused council/adversarial review after remediation and require PASS before commit/push.

## Runtime-gate checklist

When adding a new adaptive gate for a phase transition:

- Add the call inside `Heartgate.validate_transition()`.
- Use root-confined YAML/artifact loaders; fail closed on path errors.
- Bind artifacts to `run_id`, expected kind, and expected relative path.
- Block missing package directories and missing handoff/readiness artifacts.
- For deep semantic checks, prefer delegating to the canonical validator (`scripts/validate_uacp_artifacts.py`) or a shared validator module rather than re-implementing a shallow subset in Heartgate. External auditors will correctly flag presence-only runtime checks as incomplete.
- Add runtime transition fixtures under `verification/fixtures/heartgate-runtime/` or equivalent.
- Add a self-contained runtime smoke harness that creates temporary gate-ledger/PIV records required by legacy Heartgate checks, validates pass and fail fixtures, then deletes those temporary ledger files. Do not commit transient state ledger files.
- Include negative runtime fixtures for semantic false-pass classes, not only missing-file classes: required PIV warn/deferred with `ready`, VERIFY self-approval without independent reverification, RESOLVE dropped residual risk/deferred item, escaped coherence artifact paths, and weak accepted-exception/deferred acceptance.
- If shell/code execution can touch `UACP_ROOT` through command text rather than explicit `path`/`cwd` metadata, add conservative command-string detection and smoke tests for absolute, `~`, `$HOME`, and split `cd ~/.hermes && ... uacp/...` forms.

## PIV terminology and evidence caution

UACP currently has two historically overlapping concepts:

- legacy **Post-Phase Verification** ledger rule (`piv_rule`, recorded as `gate: PIV` for compatibility);
- newer **Phase Intent Verification** contract (`uacp.phase_intent_verification_contract`) authored by PLAN for EXECUTE evidence.

Keep them explicitly disambiguated in docs/config/prompts. Do not let `PIV` shorthand hide which one is being audited.

For Phase Intent Verification checkpoints:

- `next_phase_readiness.status: ready` requires all required evidence obligations to be `result: pass`.
- `warn` or `deferred` required evidence must carry owner, residual risk, and next action.
- deferred/warn evidence should use `ready_with_deferred_items`, not plain `ready`.

## Path containment caution

Any helper that loads artifacts from YAML-provided paths must resolve relative to `UACP_ROOT` and reject absolute or `../` escapes. Guardian/Heartgate path predicates must fail closed on exceptions; never return true on path-resolution failure.

## Operator reporting

If an audit finds a runtime enforcement gap after earlier claims of completion, correct the claim explicitly:

```text
Docs/config/offline validator passed, but runtime Heartgate enforcement was incomplete.
```

Then report the remediation by finding ID, validation commands, council verdict, commit SHA, and residual risks without dumping raw inventories.

After a remediation commit, rerun the external auditors against the new `HEAD` when practical. Use the Agent Council audit loop in `references/kimi-codex-agent-council-audit-loop-20260520.md` when Mike asks for Kimi + Codex, and explicitly ask each runtime whether the change is safe to use as a dependency for subsequent governed work.
