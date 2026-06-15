# UACP State Mutation Protocol

Non-authoritative reference for `uacp-state`. Canonical authority remains the UACP docs and config under `UACP_ROOT`.

## Inputs

- `UACP_ROOT/docs/index.md`
- `UACP_ROOT/docs/lifecycle-reference.md`
- `UACP_ROOT/config/state.yaml`
- `UACP_ROOT/config/uacp.toml` (`[paths]` / `base_dir` resolver) — path-root authority (roots.yaml deleted in Slice 5 W3; canonical resolver is `config.py` + `config/uacp.toml [paths]`)
- current `state/current.yaml`
- target `state/runs/<run>.yaml`

## Mutation order

1. Read the authoritative docs and state contract.
2. Resolve the current run and mutation mode.
3. Validate authority, scope, and path policy.
4. Update only owned state fields.
5. Record provenance and artifact references.
6. Verify YAML parse and path hygiene.

## Modes

### Bootstrap direct edit

- Allowed while the bootstrap boundary is open.
- Use only for the current run's UACP artifacts.
- Record the bootstrap provenance explicitly.

### Governed mutation

- Becomes mandatory after bootstrap closes.
- All state changes must route through `uacp-state`.
- Every mutation must carry traceable authority and provenance.

## Owned fields

`uacp-state` may update:

- current run pointer
- run manifest lifecycle fields
- transition artifact references
- Kanban traceability references
- bootstrap closure flags
- governed mutation flag
- tombstone provenance fields

## Boundary rules

- Never rewrite canonical docs or config.
- Never use cwd-dependent paths.
- Prefer symbolic roots and `UACP_ROOT`-relative references.
- Keep high-volume evidence out of state; store paths, not payloads.
- If a mutation would change governance rules, write the state pointer first and escalate the doc change separately.

## Verification

After each mutation:

- parse the touched YAML files
- confirm the state history entry exists
- confirm the current pointer matches the target run
- confirm the mutation did not change doc authority
