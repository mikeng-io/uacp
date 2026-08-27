# Phase 2: Read Active UACP State

If `uacp-state` is available and `.uacp/state/current.yaml` exists, read it to enrich context:

```bash
cat .uacp/state/current.yaml
```

The pointer (`state/current.yaml`) only NAMES the active run and where its manifest
lives — it is a pointer, not the run's state. Merge its real fields into context:

```yaml
uacp_state_context:
  active_run: ""            # active_run_id — the run_id if a run is in progress
  active_run_manifest: ""   # path to the authoritative run manifest (read it — see below)
  uacp_mode: ""             # manual | semi_auto | supervised_auto | full_auto
```

If no active run → `active_run: null`; context is unconstrained.

**The run manifest is authoritative** for a run's actual lifecycle state — its
`current_phase`, produced `artifacts`, `status`, and any blockers/findings. These are
NOT written to the pointer; do not infer them from `current.yaml`. Read the manifest at
`active_run_manifest` (or via the read-only `uacp_run_status` tool, which returns
`{ok, manifest, findings}`) and re-orient from it.
