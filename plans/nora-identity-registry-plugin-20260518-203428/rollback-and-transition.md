# Rollback and Transition Readiness

## Rollback path

Before gateway restart, rollback is file/config revert only:

1. Remove or disable `identity-registry` from Nora profile `plugins.enabled`.
2. Remove or quarantine the profile-local plugin directory if needed.
3. No live process rollback is required unless a restart has already occurred.

After a future approved restart, rollback requires disabling the plugin and restarting the Nora gateway again under separate authority.

## PLAN → EXECUTE readiness

Required evidence:

- PLAN and scope artifacts exist.
- PLAN validation ledger entry passes.
- Allowed write paths and forbidden paths are explicit.
- Restart boundary is recorded.

## EXECUTE → VERIFY readiness

Required evidence:

- plugin files written and enabled in config,
- deterministic tests pass,
- focused audit findings are synthesized and handled,
- no gateway restart performed,
- transition artifact records residual restart boundary.

## VERIFY → RESOLVE readiness

Required evidence:

- final verification synthesis exists,
- lifecycle gaps are either closed or recorded as residual risks with owner,
- restart decision is explicitly deferred or approved,
- no outbound/memory/source-YAML side effects occurred.
