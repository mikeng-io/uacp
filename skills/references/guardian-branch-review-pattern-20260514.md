# Guardian Branch Review Pattern — 2026-05-14

## Context
Session reviewed the `uacp-runtime-guardian` branch in hermes-agent for UACP filesystem containment integration. The branch contains the Guardian policy engine and Heartgate lifecycle transition validator.

## Branch Structure (commit a07da521a)

### Core files added/modified
| File | Lines | Purpose |
|---|---|---|
| `hermes_cli/uacp_guardian.py` | 584 | Runtime-neutral policy engine: GuardianPolicy, GuardianEvent, GuardianDecision, Heartgate |
| `plugins/uacp_guardian/__init__.py` | 221 | Hermes plugin adapter: pre/post tool hooks, `uacp_state_write` tool |
| `run_agent.py` | +22/-1226 | Agent loop integration for UACP context propagation |
| `model_tools.py` | +34/-3 | Tool orchestration integration |
| `tools/kanban_tools.py` | +11/-329 | Kanban task context binding |
| `hermes_cli/kanban.py` | +11/-152 | CLI UACP context fields |
| `hermes_cli/kanban_db.py` | +184/-604 | DB schema for UACP context |
| `hermes_cli/plugins.py` | +150/-231 | Plugin manager hook registration |
| `tests/plugins/test_uacp_guardian_plugin.py` | +76/-418 | Plugin tests |
| `tests/hermes_cli/test_uacp_kanban_guard.py` | +23/-96 | Kanban guard tests |

### Policy engine architecture
- **GuardianPolicy**: Loads `guardian-policy.yaml` from `UACP_ROOT/config/`
- **GuardianEvent**: Immutable event with tool provider, name, args, UACP context fields
- **GuardianDecision**: 5 outcomes: `allow`, `allow_with_audit`, `require_approval`, `block`, `block_pending_heartgate`
- **Heartgate**: Validates phase transitions against `phase-transitions.yaml`

### Key containment checks
- `filesystem_guard_verified` flag required for protected write categories
- Direct UACP state writes must use `uacp_state_write` tool
- Missing UACP context fields (workspace, run_id, phase, policy_version, authority, side_effects) blocks protected actions
- Fail-closed: unclassified tools default to `external.unknown_mutator` with block policy

## Critical findings from review

1. **Scope risk**: Branch diff is massive (~8,364 insertions, ~76,686 deletions across 885 files). Many deletions appear unrelated to UACP containment (locales, docs, tests, platform adapters). The branch may have accumulated unrelated changes or a large refactor.

2. **Filesystem containment gap**: The `filesystem_guard_verified` flag is checked but the actual containment implementation (chroot, containerization, or path sandboxing) was not visible in the reviewed code. The policy blocks when containment is "unavailable" but does not appear to *provide* the containment mechanism itself.

3. **Missing default policies**: Guardian requires `guardian-policy.yaml` and Heartgate requires `phase-transitions.yaml`. No default/fallback policy ships with the code — missing config raises `GuardianPolicyError` and blocks protected operations.

4. **Test coverage**: Only ~76 lines of plugin tests and ~23 lines of Kanban guard tests. The 584-line policy engine lacks dedicated unit tests in the visible diff.

## Recommended review pattern for UACP branches

When reviewing a UACP feature branch before integration:

1. **Isolate the change**: Verify only UACP-relevant files are in scope. If the diff includes unrelated deletions (locales, docs, platform adapters), demand branch cleanup before review proceeds.

2. **Check policy defaults**: Verify a default permissive policy ships disabled-by-default. The system should not fail-closed on fresh installs without operator configuration.

3. **Verify containment enforcement**: If the branch claims filesystem containment, locate the actual enforcement layer (bind mounts, chroot, containers, sandbox backends). A policy gate without an enforcement mechanism is a governance illusion.

4. **Audit test coverage**: Policy engines need dedicated unit tests for classification, decision matrices, and edge cases. Integration tests alone are insufficient.

5. **Feature flag requirement**: New enforcement should default to `off` or `observe` mode, with `enforce` as an explicit opt-in.

6. **Council recommendation pattern**: For branches with scope risk + missing defaults + unclear enforcement → recommend **NARROW SCOPE** with concrete sequencing:
   - Clean branch from `main` with only relevant files
   - Add default permissive policy
   - Implement or document the containment provider
   - Expand unit test coverage
   - Add feature flag
   - Re-review before merge

## Authority
- `docs/runtime-enforcement.md` — runtime enforcement design
- `config/guardian-policy.yaml` — policy seed
- `verification/containment-fail-closed-20260514.yaml` — fail-closed proof
- `.outputs/uacp-operational-dashboard.yaml` — open blockers
