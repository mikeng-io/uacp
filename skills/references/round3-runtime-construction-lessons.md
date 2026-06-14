# Round 3 Runtime Construction Lessons

Use this reference when moving UACP Guardian/Heartgate work from planning into Hermes runtime implementation.

## Lessons captured

- Start with an inventory slice before implementation. Classify local changes into unrelated local patches, generic Hermes seams, UACP plugin/kernel work, UACP leakage into core, Kanban/governance-context work, and tests.
- Keep the Guardian kernel inside the plugin package or another neutral package, not `hermes_cli/`. In the Round 3 slice the kernel moved from `hermes_cli/uacp_guardian.py` to `plugins/uacp_guardian/kernel.py`.
- The neutral kernel must not import Hermes runtime modules such as `hermes_cli`, `model_tools`, or `PluginManager`. Runtime-specific provider inference belongs in the adapter/plugin layer.
- Remove hardcoded UACP fallback logic from generic core plugin plumbing. A function like `_uacp_builtin_guardian_block_message()` inside `hermes_cli/plugins.py` is UACP leakage; plugin-disabled behavior should not silently contain UACP doctrine.
- Add guarded writers through the plugin boundary:
  - `uacp_state_write` remains the only state writer and is restricted to `state/`.
  - `uacp_artifact_write` may write approved artifact roots: `plans/`, `proposals/`, `executions/`, `verification/`, `.outputs/`, `knowledge/`.
  - `uacp_artifact_write` must reject `state/`, `docs/`, `config/`, absolute paths, and traversal.
- Generalize Kanban context at the API boundary before attempting a DB migration. Prefer `governance_context` with `policy_family: uacp`, preserve legacy `uacp_context`, and project to existing `UACP_*` env vars at dispatch.
- Defer physical DB table rename (`task_uacp_context` -> `task_governance_context`) unless the migration is explicitly in scope; wrappers can provide the generalized API first.
- Do not amend the single Hermes local commit when unrelated working-tree changes are mixed in. Separate or review the diff first.

## Verification pattern

Run focused checks before reporting completion:

```bash
git grep -n "hermes_cli.uacp_guardian\|_uacp_builtin_guardian" -- . || true
python - <<'PY'
from pathlib import Path
text = Path('plugins/uacp_guardian/kernel.py').read_text()
for needle in ['hermes_cli', 'model_tools', 'PluginManager']:
    print(f'{needle}: {needle in text}')
PY
python -m py_compile plugins/uacp_guardian/__init__.py plugins/uacp_guardian/kernel.py hermes_cli/plugins.py hermes_cli/kanban_db.py hermes_cli/kanban.py tools/kanban_tools.py plugins/kanban/dashboard/plugin_api.py
uv run --extra dev pytest tests/hermes_cli/test_uacp_kanban_guard.py tests/plugins/test_uacp_guardian_plugin.py tests/test_model_tools.py -q
```

Expected shape:

- grep has no matches for old core Guardian locations/fallbacks.
- kernel import check prints `False` for host-runtime imports.
- focused pytest slice passes.
