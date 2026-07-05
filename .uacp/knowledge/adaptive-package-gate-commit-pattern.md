---
type: pattern
id: adaptive-package-gate-commit-pattern
title: Adaptive Package Gate Commit Pattern
description: How to settle a large UACP working tree after governed design/runtime work by committing with a durable explanation surface
tags: [adaptive-packages, commit, lifecycle, governance]
timestamp: 2026-06-17
---

# Adaptive package gate commit pattern — 2026-05-19

## Trigger

Use this reference when settling a large UACP working tree after governed design/runtime work, especially when the change set includes lifecycle artifacts, docs, runtime-adapter code, validators, fixtures, gate ledgers, and design outputs.

## Durable lesson

For UACP commits, do not merely commit the dirty tree. First add a durable explanation surface that future agents can inspect without reconstructing the conversation.

Minimum documentation surfaces:

1. **Architecture / decision record** — add or update an ADR-style document that states:
   - what changed;
   - why it changed / rational intent;
   - invariants that must be preserved;
   - enforcement details;
   - operational notes and verification commands.
2. **Index / command docs** — update navigation and command references if the change adds a new gate, validator behavior, fixture lane, or operational nuance.
3. **Inline comments for changed verify scripts** — when a new invariant causes old tests to fail, patch the test with a comment explaining the new invariant rather than merely adding fixture boilerplate.
4. **Commit message** — make it self-contained. Include `What changed`, `Why`, `Invariants and details`, and `Verification` sections.

## Pattern used

When adaptive PROPOSE/PLAN package gates were committed:

- Added `docs/architecture/0009-adaptive-proposal-and-plan-packages.md`.
- Updated `docs/architecture/INDEX.md` and `docs/INDEX.md`.
- Updated `COMMANDS.md` to distinguish positive package-selection fixtures from intentional negative fixtures.
- Patched `scripts/phase1_verify.py` so the historical phase-exit invariant pass lane creates the required PLAN package-selection bridge, package directory, and scope artifact.
- Ran:

```bash
python scripts/validate_uacp_artifacts.py --root .
python -m py_compile runtime-adapters/hermes/plugins/uacp_guardian/kernel.py scripts/validate_uacp_artifacts.py scripts/phase1_verify.py
python scripts/validate_uacp_artifacts.py --root . \
  verification/fixtures/adaptive-proposal-package/pass-package-selection.yaml \
  verification/fixtures/adaptive-plan-package/pass-plan-selection.yaml
for n in 0 1 2 3 4; do python scripts/phase${n}_verify.py; done
```

## Pitfalls

- `python scripts/validate_uacp_artifacts.py .` treats `.` as an artifact path and fails. Use `--root .` for config/root validation.
- Do not bulk-pass intentional `block-*` fixtures to the validator when expecting a green run. They are negative evidence and should produce `RESULT BLOCK` when selected.
- Shell interpolation can corrupt `${n}` in a commit message if the message is passed through double-quoted shell args. Prefer a temporary commit-message file and `git commit --amend -F <file>` or `git commit -F <file>` for long UACP commit messages.
- A repo commit proves the canonical repo state only. It does not prove active Hermes skill exports have been refreshed.

## Commit-message skeleton

```text
<type>: <summary>

What changed:
- ...

Why:
- ...

Invariants and details:
- ...

Verification:
- ...
```
