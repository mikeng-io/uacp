# Runtime porting live-binding cleanup notes

Use this when UACP-owned Hermes adapters have been symlink-bound from `UACP_ROOT/runtime-adapters/hermes/plugins/*` into `HERMES_ROOT/plugins/*` and the next step is source-of-truth cleanup.

## Session-proven sequence

1. Verify live bindings before deleting duplicates:
   - `hermes plugins list` shows target plugins as `enabled` and `Source=user`.
   - `HERMES_ROOT/plugins/<name>` is a symlink to `UACP_ROOT/runtime-adapters/hermes/plugins/<name>`.
   - Symlink target exists and contains `plugin.yaml` plus adapter code.
2. Compare Hermes Agent local plugin copies to UACP adapter source before removal.
   - Ignore `__pycache__`/`.pyc`.
   - If files are byte-identical and the user-plugin source is active, Hermes Agent copies are transitional duplicates.
3. Patch UACP status/config docs before or alongside cleanup:
   - `config/uacp.toml [runtime_bindings]`: mark real adapters `live_bound_user_plugin` and keep verification artifact pointers.
   - `docs/index.md`: update old follow-up language from “bind after review” to “bindings active; remaining cleanup/hardening”.
   - `.outputs/uacp-current-status.yaml`: distinguish live adapter activation from production-complete enforcement.
   - `config/state.yaml`: say Guardian adapter is live-bound/partial, not merely “not implemented”.
4. Remove temporary probe adapter after real adapters prove discovery/loading:
   - `runtime-adapters/hermes/plugins/uacp_symlink_probe/`.
5. Remove tracked Hermes Agent duplicate plugin copies with `git rm -r` from the Hermes Agent repo only after explicit operator approval.
6. Re-verify after cleanup:
   - `hermes plugins list` still shows enabled user plugins.
   - Symlink targets still resolve.
   - YAML parses for changed UACP files.
   - Probe and duplicate Hermes Agent directories no longer exist.
   - Git status/diff match expected doc/config/probe deletions and Hermes duplicate deletions.

## Stale gate-task resolution after binding is already live

If a carried-over task still says “review whether to proceed to live binding” but the binding is already active and verified, do not re-run the binding decision as if it were pending. Treat it as stale task state and resolve it by evidence:

1. Ground-truth current bindings and loader behavior first (`hermes plugins list`, symlink targets, plugin manifests, live proof output if available).
2. If evidence confirms the adapters are already live-bound, update/close the gate task as “completed by prior execution; remaining work is cleanup/hardening,” rather than reopening the approval question.
3. Continue with reversible cleanup review: duplicate Hermes Agent source reduction, temporary probe removal, status/doc sync, and rollback notes.
4. If evidence is missing or contradictory, pause for focused council before changing bindings or authority posture.

Temporary probe cleanup remains conditional: remove `runtime-adapters/hermes/plugins/uacp_symlink_probe/` only when real adapter discovery/loading has current proof and the probe is not referenced by active verification scripts. Do not delete unrelated adapter artifacts under the source tree without explicit approval.

## Active-session cleanup checkpoint

When resuming after a handoff that says local plugin-copy reduction and probe cleanup *may* still be pending, ground-truth before acting:

1. Check the Hermes Agent repo and live plugin paths together:
   - `git -C HERMES_AGENT status --short --branch`
   - `python - <<'PY'` with `Path(...).exists()`, `is_symlink()`, and `resolve()` for `HERMES_ROOT/plugins/thread_title_sync`, `HERMES_ROOT/plugins/uacp_guardian`, and their `HERMES_AGENT/plugins/...` duplicate paths.
   - `hermes plugins list` to confirm `thread_title_sync` and `uacp_guardian` are `enabled` and `user` source.
2. Check temporary probe absence in both source and binding locations:
   - `UACP_ROOT/runtime-adapters/hermes/plugins/uacp_symlink_probe`
   - `HERMES_ROOT/plugins/uacp_symlink_probe`
3. If duplicates/probes are already absent, do not perform a destructive cleanup. Resolve the stale cleanup/gate item as already completed by evidence.
4. Synchronize `.outputs/uacp-operational-dashboard.yaml` and `.outputs/uacp-current-status.yaml` through governed writer surfaces when they still say cleanup is in progress or tool schemas require reload.
5. Record status accurately: live bindings active, duplicate Hermes Agent plugin source absent, temp probe source absent, active schema includes the current Guardian tools if verified.
6. Commit locally if artifacts changed, but do not push unless the operator has granted the current push authority.

If a general shell validator is blocked by Guardian because UACP context fields are missing, treat that as expected fail-closed behavior for the standard execution path. Use governed writers for artifact edits, YAML parse checks where allowed, and record the blocked validator attempt as boundary evidence rather than weakening Guardian or bypassing context requirements.

## Pitfall: governed writer surface gap

Current `uacp_artifact_write` may intentionally refuse `docs/` and `config/` writes, while ordinary file writes under `UACP_ROOT` may be blocked by Guardian unless complete UACP context reaches the hook. If explicit operator approval requires doc/config sync and no governed docs/config writer exists yet, a narrow local write may be used as a manual-drill fallback only if the verification artifact records it as an accepted implementation gap, not as normal precedent.

## Compression side issue

If runtime-porting cleanup happens after a session transfer caused by compression loops, keep the compression diagnosis separate. Do not let compression follow-up block the UACP cleanup lane; preserve a handoff note for the separate debugging session.
