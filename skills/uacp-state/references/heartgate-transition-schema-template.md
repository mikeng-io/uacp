# Heartgate transition schema template

Use this as the baseline shape when a UACP phase transition artifact fails Heartgate because of missing required fields.

## Required blocks to include

- `decision`
- `invariant_summary`
- `cluster_summary`
- `blockers`
- `warnings`
- `deferred_items`
- `authority`
- `artifact_paths`
- `declared_side_effects`
- `write_containment_record`
- `blocker_synthesis`
- `council_synthesis_artifact`
- `verification_artifact`
- `accepted_exceptions`
- `phase_local_granularity`
- `composite_granularity`
- `human_involvement`

## Working rule

If Heartgate blocks a transition on schema shape, do not improvise a smaller file. Start from a previously accepted transition artifact in the same phase family, copy the missing blocks, and then re-run Heartgate.
