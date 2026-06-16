# Guardian Policy Branch Review Pattern

Use when reviewing a UACP feature branch (Guardian, Heartgate, containment) before integration. Derived from a 2026-05-14 review of the `uacp-runtime-guardian` branch.

## 6-Step Review Pattern

1. **Isolate the change.** Verify only UACP-relevant files are in scope. If the diff includes unrelated deletions (locales, docs, platform adapters), demand branch cleanup before review proceeds. A massive diff with thousands of unrelated deletions obscures the actual Guardian changes and makes meaningful review impossible.

2. **Check policy defaults.** Verify a default permissive policy ships disabled-by-default. The system should not fail-closed on fresh installs without operator configuration — missing `guardian-policy.yaml` or `phase-transitions.yaml` should raise a clear error, not silently block everything.

3. **Verify containment enforcement.** If the branch claims filesystem containment, locate the actual enforcement layer (bind mounts, chroot, containers, sandbox backends). A policy gate that checks a `filesystem_guard_verified` flag without providing the underlying containment mechanism is a governance illusion.

4. **Audit test coverage.** Policy engines need dedicated unit tests for classification, decision matrices, and edge cases. Integration tests alone are insufficient. A 584-line policy engine with only 76 lines of plugin tests is under-tested.

5. **Feature flag requirement.** New enforcement should default to `off` or `observe` mode, with `enforce` as an explicit opt-in. This prevents fresh installs from being silently fail-closed.

6. **Council recommendation pattern.** For branches with scope risk + missing defaults + unclear enforcement, recommend **NARROW SCOPE** with concrete sequencing: clean branch from `main` with only relevant files → add default permissive policy → implement or document the containment provider → expand unit test coverage → add feature flag → re-review before merge.

## Cautionary Note on Closed-Branch Findings

Branches reviewed after their integration window may accumulate unrelated refactors that inflate the apparent diff. Always strip unrelated changes before counting the "Guardian footprint" of a branch — otherwise scope-risk findings will be artificially high and review time wasted.

## Authority

- `docs/runtime/runtime-enforcement.md` — runtime enforcement design
- `config/guardian-policy.yaml` — policy seed
