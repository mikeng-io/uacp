# Authority, Scope, and Containment

## Authority

Mike selected UACP for this work because it touches public/private profile identity boundaries and runtime prompt context.

## In scope

- Nora profile-local plugin for inbound identity lookup.
- Existing identity registry runtime engine and sanitized runtime JSON.
- Safe-card injection into ephemeral channel/system context for the current event.
- Synthetic tests, import checks, and leak scans.

## Out of scope

- Outbound live dispatch.
- Gateway restart without explicit approval.
- Hermes core changes unless the plugin seam proves insufficient.
- Memory writes or session-search enablement.
- Reading or injecting raw operator-only source fields.

## Containment

The work must remain reversible by removing/disabling the Nora profile-local plugin. Before any gateway restart, rollback is file/config revert only. After any separately approved restart, rollback requires removing the plugin/config and restarting again.
