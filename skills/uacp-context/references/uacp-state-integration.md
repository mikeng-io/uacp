# Phase 2: Read Active UACP State

If `uacp-state` is available and `state/current.yaml` exists, read it to enrich context:

```bash
cat state/current.yaml
```

Merge relevant fields into context:

```yaml
uacp_state_context:
  active_run: ""            # run_id if a run is in progress
  current_phase: ""         # triage | propose | plan | execute | verify | resolve
  uacp_mode: ""             # manual | semi_auto | supervised_auto | full_auto
  pending_transitions: []   # Phase transitions awaiting evidence
  recent_artifacts: []      # Recently produced artifacts
  blockers: []              # Active blockers from state
```

If no active run → `active_run: null`; context is unconstrained.
