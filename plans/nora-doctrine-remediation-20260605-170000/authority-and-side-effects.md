# Authority, Write Paths, and Side Effects

## Authority

**Source:** Mike chose "C" (UACP-governed run) on 2026-06-05.

**Decision owner:** Mike

**Human involvement:** REQUIRED
- Doctrine file changes require operator approval
- Plugin code changes require operator approval
- Gateway restart is separate operator boundary

## Write Paths

### Allowed Write Paths (within scope)

| File | Purpose |
|---|---|
| /home/norty/.hermes/profiles/nora/SECURITY.md | Doctrinal grant (RT-1) |
| /home/norty/.hermes/profiles/nora/IDENTITY.md | Doctrinal grant (RT-1) |
| /home/norty/.hermes/profiles/nora/KERNEL.md | Doctrinal grant (RT-1) |
| /home/norty/.hermes/profiles/nora/SOUL.md | Doctrinal grant (RT-1) |
| /home/norty/.hermes/profiles/nora/PERSONALITY.md | Language/tone precedence (RT-6) |
| /home/norty/.hermes/profiles/nora/plugins/identity_registry/__init__.py | Safe card, health, hook contract |
| /home/norty/.hermes/operator-data/nora/identity-registry/identity_registry.py | Schema validation |
| /home/norty/.hermes/operator-data/nora/identity-registry/identity_registry.runtime.json | Data regeneration |

### Forbidden Write Paths

- hermes_cli/plugins.py (out of scope; core change)
- Other profiles (Norty, default, etc.)
- Other plugins/skills
- /private/ directory

## Side Effects

1. **Doctrine file changes (5 files):** Affect Nora's behavior in DM and group contexts
2. **Plugin code changes (1 file):** Affect runtime behavior of identity-registry plugin
3. **Registry engine code changes (1 file):** Affect schema validation and runtime JSON generation
4. **Runtime JSON regeneration:** Data only, no schema change to operator data

## Blast Radius

**HIGH** — changes affect:
- 5 doctrine files (Nora's identity model)
- 1 plugin (identity-registry)
- 1 registry engine
- 1 runtime JSON data file

**Containment:** All changes scoped to Nora's profile. No cross-profile leakage.

## Risk Acknowledgement

1. **Behavioral changes may have irreversible social effects** if data leaks before fix
2. **LLM behavior verification requires live testing** (deferred to operator)
3. **Gateway restart is separate operator boundary** (plugin changes take effect only after restart)

## Rollback Authority

- `git revert` for all modified files
- Reverse-order rollback specified in `rollback-and-transition.md`
- Gateway restart for plugin code to take effect (operator boundary)
