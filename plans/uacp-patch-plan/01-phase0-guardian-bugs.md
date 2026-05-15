# Phase 0 — Guardian Bug Fixes

**Phase**: 0 of 4 (Phases 0–4 scheduled)
**Granularity**: 5
**Plugin-only**: yes (no Hermes core changes)
**Commit boundary**: one atomic commit after Codex gate passes

## Objective

Fix three concrete Guardian issues that block all downstream enforcement work.
Until Phase 0 is complete, Phase 1's mechanical contracts cannot be tested end-to-end.

## Item 0.1 — `filesystem_guard_verified` Never Set

**File**: `runtime-adapters/hermes/plugins/uacp_guardian/__init__.py`

**Problem**: The `uacp_contained_shell` tool handler stores a sandbox attestation in
`_CONTAINED_SHELL_ATTESTATIONS[attestation_id]` but never sets
`filesystem_guard_verified=True` in that record. The Guardian containment check
evaluates this field and always finds it False, blocking all UACP-bound shell and
code execution regardless of mode.

**Fix**:
1. Locate the `uacp_contained_shell` handler in `__init__.py`.
2. After the bwrap subprocess completes successfully (exit 0), set:
   `_CONTAINED_SHELL_ATTESTATIONS[attestation_id]["filesystem_guard_verified"] = True`
3. Verify the containment check in `kernel.py` reads from the attestation dict rather
   than re-evaluating independently. If it re-evaluates, update it to read the attestation.
4. Write a targeted behavioral test: call `uacp_contained_shell` with a safe command,
   confirm the attestation has `filesystem_guard_verified=True`, confirm a subsequent
   containment check passes.

**Acceptance**: `filesystem_guard_verified` is True in the attestation after a successful
bwrap execution. Guardian's containment check passes for contained-shell paths.

## Item 0.2 — Enforce Mode Is Cosmetic

**File**: `runtime-adapters/hermes/plugins/uacp_guardian/kernel.py`

**Problem**: `Guardian.evaluate()` returns the same decision regardless of
`self.policy.mode`. A `warn` verdict in `monitor` mode stays `warn` in `enforce` mode
for `uacp_bound` categories. The mode field has no effect on enforcement.

**Fix**:
1. In `Guardian.evaluate()` in `kernel.py`, after the initial decision is produced,
   add a mode-escalation step:
   ```python
   if self.policy.mode == "enforce" and decision.verdict == "warn":
       if event.category in {"uacp_bound", "uacp_write"}:
           decision = decision.escalate_to_block(reason="enforce_mode_escalation")
   ```
2. If `GuardianDecision` has no `escalate_to_block` method, add one that returns a new
   decision with `verdict=block`, `blocks_execution=True`, and the escalation reason appended.
3. Write a unit test: same event in `monitor` mode → warn; same event in `enforce` mode
   → block. Verify `blocks_execution` is True in the enforce-mode result.

**Acceptance**: `guardian_mode=enforce` produces `block` for any `uacp_bound` warn event.
Unit test passes. No existing `monitor`-mode behavior changes.

## Item 0.3 — Post-Hook Architectural Constraint Documentation

**File**: `docs/runtime-integration-guide.md`

**Problem**: Runtime adapter implementers may design detection logic that relies on
`post_tool_call` to block harmful actions. This is architecturally impossible in Hermes —
`post_tool_call` always returns `None` and is fail-open by design. This constraint is
not currently documented.

**Fix**:
Add the following paragraph to the "Known Implementation Pitfalls" section of
`docs/runtime-integration-guide.md`:

> **Post-hook cannot block.** In Hermes, `post_tool_call` always returns `None` and is
> fail-open by design. Subprocess errors, timeouts, and non-zero exits all return `None`
> silently. This means `post_tool_call` is detection-only. Any enforcement that must
> prevent a harmful action must happen in `pre_tool_call`. Do not design blocking
> logic that relies on post-hook execution; it will silently fail to block.

**Acceptance**: The paragraph exists verbatim in the pitfalls section. The constraint
is machine-discoverable by agents reading the integration guide.

## Verification Checklist

Before running the Codex gate:

- [ ] `filesystem_guard_verified` is set to True in the attestation after bwrap success
- [ ] Guardian containment check reads attestation dict, not independent re-evaluation
- [ ] Targeted behavioral test passes for 0.1
- [ ] `enforce` mode produces block for uacp_bound warn events
- [ ] `monitor` mode behavior is unchanged
- [ ] Unit test passes for 0.2 in both modes
- [ ] Post-hook constraint paragraph exists in runtime-integration-guide.md
- [ ] All modified Python files parse without syntax error
- [ ] No existing Guardian tests broken
- [ ] Changes committed (or staged) before Codex gate runs

## Codex Gate

After checklist passes, run Codex review at `tier_2_role_diverse`:
- Technical role: verify bug fix correctness and test coverage
- Governance role: verify post-hook constraint documentation is precise and complete
- Skeptic role: look for regressions, edge cases, and paths that 0.1 and 0.2 do not cover

**Verdict required**: `pass`, zero material findings.
**Artifact**: `verification/uacp-patch-plan-phase0-codex-review.yaml`
