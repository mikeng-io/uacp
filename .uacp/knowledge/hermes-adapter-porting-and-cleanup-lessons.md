---
type: analysis
id: hermes-adapter-porting-and-cleanup-lessons
title: Hermes Adapter Porting and Cleanup Lessons
description: UACP adapter ownership direction, hermes_symlink_plugin_probe.py invocation, dirty-state precheck, branch-verification checklist, deferred-action boundary, and stale-gate-task resolution for Hermes porting work.
tags: [hermes, adapter, porting, runtime]
timestamp: 2026-06-17
---

# Hermes Adapter Porting and Cleanup Lessons

Durable lessons for UACP-owned runtime adapter/plugin porting, Hermes user-plugin symlink binding, and source-of-truth cleanup after live binding. Covers version-control policy, execution runbook, and live-binding cleanup.

Cross-reference `docs/runtime/runtime-porting-and-version-control.md` for canonical porting policy and `docs/lifecycle/worktree-protocol.md` for worktree SOP.

---

## Ownership Direction

UACP is the central Git-controlled source of truth for governed runtime behavior:

```text
UACP doctrine/config/state
  -> runtime-neutral contracts
  -> runtime-adapters/<runtime>/...
  -> runtime-specific plugin/hook/config binding
  -> symlink/install/export into Hermes, OpenCode, Claude Code, Codex, etc.
```

Hermes Agent is the first runtime target, not the authority root. Avoid letting `HERMES_AGENT_ROOT/plugins/` become the long-term source of UACP-owned plugin code.

Preferred adapter layout:

```text
UACP_ROOT/
  runtime-adapters/
    hermes/
      plugins/
        uacp_guardian/
        thread_title_sync/
    opencode/
    claude-code/
    codex/
    kimi/
    gemini/
```

For Hermes, the binding layer is the user plugin directory:

```text
HERMES_ROOT/plugins/uacp_guardian -> UACP_ROOT/runtime-adapters/hermes/plugins/uacp_guardian
HERMES_ROOT/plugins/thread_title_sync -> UACP_ROOT/runtime-adapters/hermes/plugins/thread_title_sync
```

Note: `HERMES_ROOT/worktrees/` is the path used when adding UACP worktrees for Hermes-adjacent runtime porting work.

---

## hermes_symlink_plugin_probe.py Invocation

Non-destructive Hermes symlink proof shape — run this before any live binding:

```bash
python "$HERMES_ROOT/skills/devops/uacp/scripts/hermes_symlink_plugin_probe.py" \
  --hermes-agent-root "$HERMES_AGENT_ROOT" \
  --hermes-home "$HERMES_ROOT" \
  --adapter-root "$UACP_WORKTREE/runtime-adapters/hermes/plugins"
```

Expected result fields:

- loaded plugin exists
- `enabled: true`
- `manifest_source: user`
- expected hook/tool registered
- symlink removed after proof

This proves user-plugin symlink discovery without binding `uacp_guardian` or `thread_title_sync` live.

Only after that proof should a real adapter binding be attempted:

```bash
mkdir -p "$HERMES_ROOT/plugins"
ln -sfn "$UACP_ROOT/runtime-adapters/hermes/plugins/uacp_guardian" \
  "$HERMES_ROOT/plugins/uacp_guardian"
test -L "$HERMES_ROOT/plugins/uacp_guardian"
test -f "$HERMES_ROOT/plugins/uacp_guardian/plugin.yaml"
test -f "$HERMES_ROOT/plugins/uacp_guardian/__init__.py"
hermes plugins list
```

Python symlink idiom for ground-truthing (use in a `-c` or heredoc block):

```python
from pathlib import Path
p = Path("$HERMES_ROOT/plugins/uacp_guardian")
print(p.exists(), p.is_symlink(), p.resolve())
```

---

## Planning Requirement

When asked to plan or execute runtime porting, explicitly include:

- Version-control policy.
- Branch/worktree SOP.
- Runtime binding/symlink SOP.
- Verification and rollback.
- Hermes local patch reduction path.
- Future-runtime generalization beyond Hermes.

---

## Dirty-State Precheck and Tarball Backup

Before merging/rebasing runtime-porting work:

1. Inspect `UACP_ROOT` dirty state.
2. If dirty, create a reversible backup before committing:
   - Tracked diff under a timestamped backup path.
   - Tarball of untracked files.
3. Validate YAML and run `scripts/validate_uacp_artifacts.py` when present.
4. Commit dirty artifacts in concern-separated slices rather than one mixed commit.

If `UACP_ROOT/main` is already dirty with unrelated current-canon or active-run changes, keep the runtime-porting work isolated in its own worktree/branch and do not merge or commit from the dirty main tree. Record this as a lane-isolation warning in the execution evidence, then wait for the main lane to be resolved before integrating.

---

## docs/index.md Semantic-Conflict Resolution

When rebasing runtime-porting work onto current `main`:

- Prefer current `main` as the base for registry/decision-log content.
- Re-apply the runtime-porting inventory rows, decision entry, and open-action lines.
- Check no conflict markers remain.
- Do not blindly accept one side; `docs/index.md` is the authority front door.

---

## Branch-Verification Checklist

Before merging a runtime-porting branch into `main`:

- [ ] Parse new YAML configs/evidence (confirm valid YAML).
- [ ] Confirm required runtime-adapter files exist.
- [ ] Run `git diff --check` (no whitespace errors or conflict markers).
- [ ] Run UACP artifact validator if available.
- [ ] Merge into `main` with `--ff-only` when possible.

---

## Deferred-Action Boundary List

Do **not** perform these during the proof-only lane:

- Remote push.
- Live `uacp_guardian` / `thread_title_sync` binding switch.
- Hermes Agent bundled/transitional plugin removal.
- Gateway restart.
- Hermes local patch amendment.

Those are later gates requiring focused review/council and targeted runtime tests.

---

## Pre-Live-Binding Review Questions

After merge and proof, run a focused review or light Agent Council. Answer before binding real plugins:

- Is `plugins.enabled` behavior safe for user-plugin overrides?
- Which plugin should bind first? (Lower-risk `thread_title_sync` usually precedes blocking `uacp_guardian`.)
- Is rollback sufficient and executable?
- What exact test slice must pass before reducing Hermes Agent local patches?
- Should temporary probe source remain or be removed after evidence capture?

---

## Stale Gate-Task Resolution Principle

If a carried-over task still says "review whether to proceed to live binding" but the binding is already active and verified:

1. Ground-truth current bindings first (`hermes plugins list`, symlink targets, plugin manifests, live proof output if available).
2. If evidence confirms adapters are already live-bound, update/close the gate task as "completed by prior execution; remaining work is cleanup/hardening" — do not reopen the approval question.
3. Continue with reversible cleanup review: duplicate Hermes Agent source reduction, temporary probe removal, status/doc sync, and rollback notes.
4. If evidence is missing or contradictory, pause for focused council before changing bindings or authority posture.

**Principle: ground-truth before re-asking; close stale tasks as completed-by-prior-execution when evidence supports it.**

---

## Verify-Before-Delete

Before deleting any duplicate source:

1. `hermes plugins list` shows target plugins as `enabled` and `Source=user`.
2. `HERMES_ROOT/plugins/<name>` is a symlink to `UACP_ROOT/runtime-adapters/hermes/plugins/<name>`.
3. Symlink target exists and contains `plugin.yaml` plus adapter code.
4. Compare Hermes Agent local plugin copies to UACP adapter source before removal.
   - Ignore `__pycache__`/`.pyc`.
   - If files are byte-identical and the user-plugin source is active, Hermes Agent copies are transitional duplicates.
5. Remove temporary probe adapter only after real adapters prove discovery/loading.
6. Re-verify after cleanup: `hermes plugins list` still shows enabled user plugins, symlink targets resolve, YAML parses for changed UACP files.

---

## Active-Session Cleanup Checkpoint

When resuming after a handoff that says local plugin-copy reduction and probe cleanup may still be pending, ground-truth before acting:

1. Check the Hermes Agent repo and live plugin paths together.
2. Check temporary probe absence in both source (`UACP_ROOT/runtime-adapters/hermes/plugins/uacp_symlink_probe`) and binding (`HERMES_ROOT/plugins/uacp_symlink_probe`) locations.
3. If duplicates/probes are already absent, resolve the stale cleanup/gate item as already completed by evidence.
4. Synchronize `.outputs/uacp-operational-dashboard.yaml` and `.outputs/uacp-current-status.yaml` through governed writer surfaces when they still say cleanup is in progress.
5. Commit locally if artifacts changed, but do not push unless the operator has granted current push authority.

---

## Governed Writer Surface Gap

Current `uacp_artifact_write` may intentionally refuse `docs/` and `config/` writes, while ordinary file writes under `UACP_ROOT` may be blocked by Guardian unless complete UACP context reaches the hook. If explicit operator approval requires doc/config sync and no governed docs/config writer exists yet, a narrow local write may be used as a manual-drill fallback only if the verification artifact records it as an accepted implementation gap, not as normal precedent.

---

> _Sources: `skills/references/runtime-porting-version-control.md`, `skills/references/runtime-porting-execution-runbook.md`, and `skills/references/runtime-porting-live-binding-cleanup.md`. All removed in ADR-0017 / Step 2 Slice 3. Completed Hermes-specific task lists and stale dashboard refs dropped._
