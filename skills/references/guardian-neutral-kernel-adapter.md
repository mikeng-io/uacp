# Guardian Neutral Kernel + Runtime Adapter Pattern

Use this reference when UACP Guardian/Heartgate work moves from planning into runtime implementation.

## Durable lesson

UACP Guardian must not become Hermes-core doctrine. The implementation shape should be:

```text
neutral Guardian kernel -> runtime adapter contract -> Hermes uacp_guardian plugin -> generic Hermes hook/tool seams
```

The neutral kernel owns policy evaluation and decision shape. Hermes owns only the runtime adapter surface: converting Hermes tool/session events into the kernel input contract and applying structured block/warn/allow decisions.

## Evidence source

The `agent-skills` repository has prior extraction work on branch `codex/guardian-agent-council-uacp` with this useful pattern:

- `skills/uacp-guardian/scripts/guardian.py` — neutral CLI/kernel with no runtime imports
- `skills/uacp-guardian/adapters/claude.py`
- `skills/uacp-guardian/adapters/opencode.py`
- `skills/uacp-guardian/adapters/kimi.py`
- `skills/uacp-guardian/hooks/guard-council.py`
- `skills/uacp-guardian/hooks/guard-output.py`
- `skills/uacp-guardian/references/preflight-pattern.md`

Treat that branch as pattern evidence, not UACP authority. Canonical UACP docs/config/state remain authoritative.

## Implementation checklist

1. Inventory current Hermes changes and classify them as:
   - generic Hermes seam
   - UACP plugin adapter
   - UACP policy/kernel logic
   - accidental UACP leakage into core
   - Kanban/governance-context propagation
2. Extract or shim the Guardian kernel so it has zero Hermes imports.
3. Keep UACP-specific policy and artifact rules inside `plugins/uacp_guardian/` or UACP artifacts/skills, not Hermes core.
4. Remove or generalize any hardcoded UACP fallback in core plugin plumbing. If fail-closed behavior is needed, express it as a generic required-policy-plugin mechanism.
5. Add guarded artifact writers in the plugin; keep state mutation on the governed `uacp_state_write` path.
6. Generalize Kanban propagation as `governance_context` where practical; project to UACP env vars only at the adapter boundary.
7. Verify both plugin-enabled and plugin-disabled behavior before live activation.

## Pitfalls

- Do not import Hermes runtime modules from the neutral kernel.
- Do not treat a skills branch as canonical UACP doctrine.
- Do not turn Hermes Kanban into hidden UACP lifecycle state; it is a coordination adapter.
- Do not activate live Guardian enforcement before the neutralization inventory and boundary checks are complete.
- Do not bury UACP-specific block messages or fallback policy inside generic core plugin dispatch code.
