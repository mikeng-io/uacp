# Guardian Neutral Kernel + Runtime Adapter Pattern

Use when UACP Guardian/Heartgate work moves from planning into runtime implementation across any host runtime (Hermes, Codex, OpenCode, etc.).

## Durable Principle

UACP Guardian must not become host-runtime doctrine. The correct implementation shape is:

```text
neutral Guardian kernel -> runtime adapter contract -> host runtime plugin -> generic hook/tool seams
```

The neutral kernel owns policy evaluation and decision shape. The host runtime owns only the adapter surface: converting its tool/session events into the kernel input contract and applying structured block/warn/allow decisions.

## 7-Step Neutralization Checklist

1. Inventory current host-runtime changes and classify them as:
   - generic runtime seam
   - UACP plugin adapter
   - UACP policy/kernel logic
   - accidental UACP leakage into core
   - governance-context propagation
2. Extract or shim the Guardian kernel so it has zero host-runtime imports.
3. Keep UACP-specific policy and artifact rules inside the UACP plugin package, not the runtime core.
4. Remove or generalize any hardcoded UACP fallback in core plugin plumbing. If fail-closed behavior is needed, express it as a generic required-policy-plugin mechanism.
5. Add guarded artifact writers in the plugin; keep state mutation on the governed `uacp_state_write` path.
6. Generalize governance context propagation where practical; project to UACP env vars only at the adapter boundary.
7. Verify both plugin-enabled and plugin-disabled behavior before live activation.

## Pitfalls

- Do not import host-runtime modules (`hermes_cli`, `model_tools`, `PluginManager`, etc.) from the neutral kernel.
- Do not treat a skills branch as canonical UACP doctrine.
- Do not turn the host runtime's coordination adapter (e.g., Kanban) into hidden UACP lifecycle state; it is a coordination adapter.
- Do not activate live Guardian enforcement before the neutralization inventory and boundary checks are complete.
- Do not bury UACP-specific block messages or fallback policy inside generic core plugin dispatch code.

## Cross-Reference

See `docs/runtime/runtime-enforcement.md` for the canonical runtime enforcement design and the distinction between Guardian policy evaluation and host-runtime containment provision.
