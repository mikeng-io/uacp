# UACP Phase Transition Finalization and Validation Patterns

Use this reference when a UACP run is moving from EXECUTE toward VERIFY or from VERIFY toward RESOLVE after runtime/docs/config changes.

## Trigger

Apply this pattern when the session includes any of:

- Heartgate/Guardian runtime or policy changes.
- Agent Council blocker/concern patching.
- A phase transition artifact with `heartgate_coherence`.
- Local commits before advancing UACP state.
- Final validator/test evidence before changing `state/current.yaml`.

## Sequence

1. **Patch blockers and concerns before transition.** If Agent Council found blockers, do not advance phase on main-session judgement alone. Patch the blockers, then rerun a focused retrieval-led council against ground-truth files.
2. **Record rerun synthesis as verification evidence.** Store the rerun council outcome under `verification/` and reference it from the transition artifact via `heartgate_coherence.artifact_path` when material-risk policy requires it.
3. **Run final validation before state mutation.** At minimum:
   - artifact validator (`scripts/validate_uacp_artifacts.py`),
   - syntax parsing/compile checks for changed runtime scripts,
   - targeted implementation tests,
   - Heartgate check on the proposed transition artifact.
4. **Commit the validated patch set before phase transition when the tree is large or safety-significant.** This preserves rollback/evidence clarity. Do not push unless explicitly authorized.
5. **Create the phase transition artifact.** Include blockers, warnings, deferred items, evidence artifact paths, phase-local granularity, human involvement, and `heartgate_coherence` with required lenses.
6. **Run `uacp_heartgate_check`.** Only move `state/current.yaml` and the run manifest when Heartgate returns pass or warn with no blockers.
7. **Update dashboard/status artifacts after the state change.** Keep the summary short and factual: active phase, accepted warnings, deferred push/PR, and residual risks.
8. **Run one final validator after state/dashboard update.** This catches broken artifact references introduced by the transition itself.
9. **Commit transition/state/dashboard artifacts locally.** Keep commit messages phase-specific and avoid pushing without explicit approval.

## Tooling notes

### Standard terminal under Guardian

When using ordinary terminal commands during UACP-bound work, provide complete UACP context fields if the live Guardian requires them:

```bash
UACP_RUN_ID=<run-id> \
UACP_PHASE=<phase> \
UACP_POLICY_VERSION=uacp-current \
UACP_DECLARED_AUTHORITY=<artifact-path> \
UACP_DECLARED_SIDE_EFFECTS='read-only validation / local commit only / ...' \
<command>
```

Use this for declared local git status/commit/test commands. Keep side effects precise: `no push`, `no deletion`, `read-only validation`, or `local commit only`.

### Contained shell validation

`uacp_contained_shell` binds `UACP_ROOT` read-only. Commands that write bytecode caches under UACP_ROOT can fail even when they are logically validation-only. Prefer bytecode-free syntax parsing when possible:

```bash
cd "$UACP_ROOT" && PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import ast, pathlib
for p in ["runtime-adapters/hermes/plugins/uacp_guardian/kernel.py"]:
    ast.parse(pathlib.Path(p).read_text(), filename=p)
    print("syntax ok", p)
PY
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_uacp_artifacts.py
```

Do not capture this as a negative claim about contained shell; the durable lesson is to choose validation commands that do not need to write into read-only roots.

### Pytest collection fallback

If a repository-level pytest configuration prevents targeted test collection, use an explicit config bypass or direct collection path and record the successful command in the verification artifact, for example:

```bash
python -m pytest -c /dev/null tests/hermes_cli/test_uacp_kanban_guard.py -q
```

This is a fallback pattern, not a claim that pytest is broken.

## Transition artifact reminders

- Keep strict `invariant_summary.status` and `cluster_summary.state` values within Heartgate's accepted vocabulary, usually `pass` for accepted non-blocking concerns.
- Put accepted concerns in `warnings` and `deferred_items` with owner, residual risk, accepted_by, and condition.
- If `heartgate_coherence_required_when` applies, missing coherence should be a blocker.
- Reference the actual rerun council artifact in `heartgate_coherence.artifact_path`; do not reference an older pre-patch council unless that is the evidence being assessed.

## Reporting pattern

When reporting to Mike after finalization, lead with the new phase and blocker status, then list evidence paths and repo status. Explicitly note non-actions: no push, no deletion, no unbind, no security weakening.
