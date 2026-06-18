---
type: guide
title: "Agent Operating Guide — How to Work in This Area"
description: "Operating posture, required workflow, and completion standard for agents modifying UACP lifecycle gates, Heartgate, Guardian, or validator behavior."
tags: [agent-operating-guide, uacp, lifecycle, validation]
timestamp: 2026-06-18
---

# Agent Operating Guide — How to Work in This Area

Use this when modifying UACP lifecycle gates, semantic packages, Heartgate, Guardian, validator behavior, phase skills, or documentation that explains them.

## Operating posture

Do not treat lifecycle hardening as a docs-only topic. The real contract spans:

- docs and ADRs for intent,
- config for declarative policy,
- validator code for offline truth checks,
- Heartgate for phase-transition runtime enforcement,
- Guardian for protected tool-call enforcement,
- skill exports for agent execution behavior,
- fixtures for regression proof.

A change is incomplete if only one surface is updated.

## Required workflow

1. Inspect ground truth, not summaries.
2. Identify the owner surface for each rule.
3. Patch the owner surface first.
4. Update guide/index docs only to explain or route to the owner.
5. Add or update positive and negative fixtures for every false-pass class.
6. Run validator and runtime smoke tests.
7. Run active skill-link checks when skills or docs move.
8. Use adversarial review for runtime/validator/security changes.
9. Commit with a message that states what changed, why, invariants, and verification.

## Do not scatter doctrine

Avoid adding the same lifecycle rule to multiple files. Instead:

- If it is a phase rule, update `config/phase-transitions.yaml` and the relevant lifecycle/reference doc.
- If it is a runtime rule, update `runtime-adapters/hermes/plugins/uacp_guardian/kernel.py` and runtime docs.
- If it is an artifact validation rule, update `scripts/validate_uacp_artifacts.py` and fixtures.
- If it is an accepted design decision, create or supersede an ADR.
- If it is an explanation for readers, add it to this guide and link to the owner.

## Validation commands

Run the core stack before claiming completion:

```bash
python -m py_compile   scripts/validate_uacp_artifacts.py   runtime-adapters/hermes/plugins/uacp_guardian/kernel.py   verification/fixtures/heartgate-runtime/run_heartgate_runtime_smoke.py   scripts/check_active_uacp_skill_links.py

python scripts/validate_uacp_artifacts.py --root .
python verification/fixtures/heartgate-runtime/run_heartgate_runtime_smoke.py
python scripts/check_active_uacp_skill_links.py
```

For lifecycle gate changes, also run a negative sweep over adaptive and Heartgate fixtures. The exact fixture directories are listed in [03-artifact-and-gate-map.md](03-artifact-and-gate-map.md).

## Review expectation

For runtime, validator, protected-state, or lifecycle-boundary changes, run at least one adversarial review. A useful reviewer should attempt to find:

- offline validator passes where Heartgate blocks,
- Heartgate passes where offline validator blocks,
- self-certifying evidence,
- cross-run artifact laundering,
- command strings that touch UACP without being bound,
- stale active skill paths,
- closure that drops unresolved risk.

## Completion standard

Do not say “done” just because tests are green. Completion requires:

- owner surfaces patched,
- positive and negative fixtures updated,
- docs/index routes updated,
- active skill exports checked when relevant,
- review concerns either fixed or explicitly accepted with rationale,
- clean git state after commit/push.
