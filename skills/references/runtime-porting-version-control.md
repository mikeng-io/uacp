# Runtime Porting + Version Control Pattern

Use this reference when UACP work touches runtime adapter/plugin ownership, repository backup, branch/worktree SOP, or reducing Hermes Agent local patches.

## Core direction

UACP should be the central Git-controlled source of truth for governed runtime behavior:

```text
UACP doctrine/config/state
  -> runtime-neutral contracts
  -> runtime-adapters/<runtime>/...
  -> runtime-specific plugin/hook/config binding
  -> symlink/install/export into Hermes, OpenCode, Claude Code, Codex, etc.
```

Hermes Agent is the first runtime target, not the authority root. Avoid letting `HERMES_AGENT_ROOT/plugins/` become the long-term source of UACP-owned plugin code.

## Preferred layout

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

For Hermes, prefer the user plugin directory as the runtime binding layer:

```text
HERMES_ROOT/plugins/uacp_guardian -> UACP_ROOT/runtime-adapters/hermes/plugins/uacp_guardian
HERMES_ROOT/plugins/thread_title_sync -> UACP_ROOT/runtime-adapters/hermes/plugins/thread_title_sync
```

This keeps Hermes Agent's upstream checkout closer to disposable/upstream-aligned status while UACP owns the adapter source.

## Git policy

- `UACP_ROOT` should be a private Git repo with a private remote; local Git alone is not backup.
- `main` is stable reviewed UACP authority state.
- Use `uacp/<run-id>/<topic>` branches/worktrees for active governed runs.
- Keep high-frequency runtime state out of noisy commits unless it is an audit checkpoint.
- Commit meaningful slices: proposal/plan, runtime adapter source, binding config/SOP, verification evidence, resolution/lessons.

## Branch/worktree SOP

```bash
cd "$UACP_ROOT"
git fetch --all --prune || true
git worktree add \
  "$HERMES_ROOT/worktrees/uacp/<run-id>" \
  -b "uacp/<run-id>/<topic>"
```

Work in the worktree, then merge only after verification:

```bash
cd "$UACP_ROOT"
git merge --ff-only "uacp/<run-id>/<topic>"
# push only after explicit operator approval and configured private remote
git push origin main
```

If `UACP_ROOT/main` is already dirty with unrelated current-canon or active-run changes, keep the runtime-porting work isolated in its own worktree/branch and do **not** merge or commit from the dirty main tree. Record this as a lane-isolation warning in the execution evidence, then wait for the main lane to be resolved before integrating.

## Runtime binding SOP

1. Ground-truth that the runtime can load extensions from the target binding path with a **temporary probe plugin**, not by immediately switching a real production plugin.
2. Add/copy adapter source under `UACP_ROOT/runtime-adapters/<runtime>/...`.
3. Bind into the runtime through symlink/install/export.
4. Verify discovery and behavior.
5. Update UACP binding/status artifacts so they reflect the live binding before claiming the lane is complete.
6. Only then remove or shrink duplicated runtime-repo copies.
7. Remove temporary probe artifacts only after explicit cleanup approval or a governed cleanup path.
8. Record rollback commands and commit refs for both UACP and the runtime repo.

Hermes non-destructive symlink proof shape:

```bash
python "$HERMES_ROOT/skills/devops/uacp/scripts/hermes_symlink_plugin_probe.py" \
  --hermes-agent-root "$HERMES_AGENT_ROOT" \
  --hermes-home "$HERMES_ROOT" \
  --adapter-root "$UACP_WORKTREE/runtime-adapters/hermes/plugins"
```

Expected result: Hermes plugin discovery reports the probe as `manifest_source: user`, `enabled: true`, and registers `on_session_start`; the probe symlink is removed afterward. This proves user-plugin symlink discovery without binding `uacp_guardian` or `thread_title_sync` live.

Only after that proof should a real adapter binding be attempted:

```bash
mkdir -p "$HERMES_ROOT/plugins"
ln -sfn "$UACP_ROOT/runtime-adapters/hermes/plugins/uacp_guardian" "$HERMES_ROOT/plugins/uacp_guardian"
test -L "$HERMES_ROOT/plugins/uacp_guardian"
test -f "$HERMES_ROOT/plugins/uacp_guardian/plugin.yaml"
test -f "$HERMES_ROOT/plugins/uacp_guardian/__init__.py"
hermes plugins list
```

## Config/Gist distinction

Lightweight Norty config templates may live in a Gist or small separate config repo. Do not confuse that with UACP authority:

- Good for Gist/small repo: sanitized `config.yaml` templates, model routing notes, profile bootstrap snippets.
- Not for Gist: secrets, `.env`, `auth.json`, `state.db`, sessions, logs, private memory.
- UACP Git owns governed doctrine, runtime contracts, runtime adapters, verification, and audit artifacts.

## Planning requirement

When asked to plan or execute runtime porting, explicitly include:

- version-control policy,
- branch/worktree SOP,
- runtime binding/symlink SOP,
- verification and rollback,
- Hermes local patch reduction path,
- future-runtime generalization beyond Hermes.
