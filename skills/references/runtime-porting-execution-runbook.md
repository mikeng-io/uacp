# Runtime Porting Execution Runbook

Use this when executing UACP-owned runtime-adapter/plugin porting, especially Hermes user-plugin symlink binding and migration away from runtime-repo-owned plugin source.

## Proven pattern

1. **Settle canonical root first**
   - Inspect `UACP_ROOT` dirty state before merging/rebasing runtime-porting work.
   - If dirty, create a reversible backup before committing:
     - tracked diff under a timestamped backup path,
     - tarball of untracked files.
   - Validate YAML and run `scripts/validate_uacp_artifacts.py` when present.
   - Commit dirty artifacts in concern-separated slices rather than one mixed commit.

2. **Use an isolated UACP worktree/branch for runtime-porting**
   - Branch pattern: `uacp/<run-id>/<topic>`.
   - Worktree pattern: `HERMES_ROOT/worktrees/uacp/<run-id>/`.
   - Keep the branch clean before attempting rebase/merge.

3. **Resolve `docs/index.md` conflicts semantically**
   - Prefer current `main` as the base for registry/decision-log content.
   - Re-apply the runtime-porting inventory rows, decision entry, and open-action lines.
   - Check no conflict markers remain.
   - Do not blindly accept one side; `docs/index.md` is the authority front door.

4. **Verify branch before merging**
   - Parse new YAML configs/evidence.
   - Confirm required runtime-adapter files exist.
   - Run `git diff --check`.
   - Run the UACP artifact validator if available.
   - Merge into `main` with `--ff-only` when possible.

5. **Prove Hermes symlink discovery non-destructively**
   - Use a temporary probe plugin under `UACP_ROOT/runtime-adapters/hermes/plugins/<probe>/`.
   - Temporarily link it into `HERMES_ROOT/plugins/<probe>`.
   - In an isolated Python process, monkeypatch plugin enabled/disabled discovery so the proof does not mutate `config.yaml`.
   - Expected proof fields:
     - loaded plugin exists,
     - `enabled: true`,
     - `manifest_source: user`,
     - expected hook/tool registered,
     - symlink removed after proof.

6. **Record post-merge evidence**
   - Add a verification artifact under `verification/` after proof from canonical `main`.
   - Commit this evidence separately.

## Boundaries

Do **not** do these during the proof-only lane:

- remote push,
- live `uacp_guardian` / `thread_title_sync` binding switch,
- Hermes Agent bundled/transitional plugin removal,
- gateway restart,
- Hermes local patch amendment.

Those are later gates requiring focused review/council and targeted runtime tests.

## Review checkpoint before live binding

After merge and proof, run a focused review or light Agent Council before binding real plugins. Review questions:

- Is `plugins.enabled` behavior safe for user-plugin overrides?
- Which plugin should bind first? Lower-risk `thread_title_sync` usually precedes blocking `uacp_guardian`.
- Is rollback sufficient and executable?
- What exact test slice must pass before reducing Hermes Agent local patches?
- Should temporary probe source remain or be removed after evidence capture?
