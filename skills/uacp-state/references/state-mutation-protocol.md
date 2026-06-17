# UACP State Mutation Protocol

## The boundary

After bootstrap closes (`bootstrap_closed: true`, `governed_mutation_active: true`),
all UACP state writes are governed. Direct `write_file` calls into the governed
namespace are blocked by the UACP Guardian:

> UACP Guardian blocked state.uacp: direct UACP state writes must use uacp_state_write

The governed namespace root is resolved at runtime — it is **not** a hardcoded
path. `config.py` defines `base: str = ".uacp"` and `base_dir(root)` returns
`<root>/<paths.base>` (default `.uacp/`, overridable via a project-local
`.uacp/config.toml [paths]`). State lives under that resolved base, e.g.
`<UACP_ROOT>/.uacp/state/`. Never write `~/.hermes/...` or any absolute root.

## The governed primary path

`uacp_state_write` is the live, governed primary path for state mutation — not a
future fix and not a workaround. Route every state write through it (or the
runtime's guarded state-mutation surface) carrying full UACP context: run id,
phase, policy version, authority, declared side effects, and workspace policy.
The Guardian checks the target path class, so the writer — not the method — is
what keeps the mutation in policy.

Two state surfaces are mechanically protected even from `uacp_state_write` and
have dedicated writers:

- `state/gate-ledger/{run_id}.jsonl` → `uacp_gate_ledger_append`
- `state/run-registry.yaml` → `uacp_run_registry_update`

## What goes where

| Artifact | Path | Writer |
|---|---|---|
| Run manifest | `state/runs/{run_id}.yaml` | uacp-state |
| Transition artifact | `state/runs/{run_id}-{from}-to-{to}-transition.yaml` | uacp-state |
| Current pointer | `state/current.yaml` | uacp-state only |
| Gate ledger | `state/gate-ledger/{run_id}.jsonl` | `uacp_gate_ledger_append` |
| Run registry | `state/run-registry.yaml` | `uacp_run_registry_update` |

Manifests and transition artifacts are YAML (`state_machine.py` serializes the
`RunManifest` with `yaml.safe_dump` to `state/runs/{run_id}.yaml`). Triage,
proposal, and plan artifacts are produced by their own phase skills under the
governed namespace and linked into the manifest's `artifacts` map via
`register-artifact`; they are not state-mutator outputs.

## Non-waivable invariants for state writes

1. Record provenance (who wrote, why, from which phase) in `state_history`.
2. Use `UACP_ROOT`-relative or symbolic paths; never cwd-dependent paths.
3. Don't mutate canonical docs or config from a state write.
4. Keep state changes narrow and traceable.

## Inputs

- `UACP_ROOT/config/state.yaml`
- `UACP_ROOT/config/uacp.toml` (`[paths]` / `base_dir` resolver) — path-root
  authority (roots.yaml deleted in Slice 5 W3; canonical resolver is `config.py`
  + `config/uacp.toml [paths]`)
- current `state/current.yaml`
- target `state/runs/{run_id}.yaml`

## Mutation order

1. Read the authoritative state contract and path policy.
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
- All state changes route through `uacp_state_write` (or the dedicated protected
  writers above).
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
- If a mutation would change governance rules, write the state pointer first and
  escalate the doc change separately.
- The knowledge/lesson corpus (`.uacp/lessons/`, `.uacp/knowledge/`) is owned
  exclusively by the Oracle engine and is NOT a uacp-state surface; never write
  it via `uacp_state_write`.

## Verification

After each mutation:

- parse the touched YAML files
- confirm the state history entry exists
- confirm the current pointer matches the target run
- confirm the mutation did not change doc authority
