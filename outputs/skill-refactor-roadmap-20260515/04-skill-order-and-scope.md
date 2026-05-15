# Skill Order and Scope

## Execution order

0. `uacp` router
1. `uacp-triage`
2. `uacp-propose`
3. `uacp-plan`
4. `uacp-execute`
5. `uacp-verify`
6. `uacp-resolve`
7. `uacp-state`
8. shared references cleanup

## Why this order

- Router first so loading behavior stops forcing a central doctrine blob.
- TRIAGE before PROPOSE because previous work incorrectly compressed TRIAGE into PROPOSE.
- PROPOSE before PLAN because plan must consume proposal package outputs.
- PLAN before EXECUTE because execution must be based on a concrete plan package.
- EXECUTE before VERIFY because verification needs declared mutation boundaries and outputs.
- VERIFY before RESOLVE because resolution depends on verified findings and residual risk.
- STATE later because state contract must reflect the final phase contracts.
- Shared cleanup last because ownership can only be known after phase modules are created.

## Scope boundary

During each skill phase, only that skill directory may be changed unless the Decision artifact explicitly authorizes a narrow exception.
