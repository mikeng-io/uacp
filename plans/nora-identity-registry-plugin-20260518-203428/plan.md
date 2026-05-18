# Plan — Nora Identity Registry Plugin

## Execution topology

Norty remains the orchestrator. Implementation occurs locally through bounded file edits under the Nora profile and deterministic local tests. A focused post-implementation audit reviews privacy and runtime behavior before any restart boundary is crossed.

## Planned implementation path

1. Inspect Nora plugin discovery/config state and existing identity registry runtime engine.
2. Create a profile-local plugin under `/home/norty/.hermes/profiles/nora/plugins/identity_registry/`.
3. Register `pre_gateway_dispatch` to resolve only the active inbound sender.
4. Inject only minimized current-sender safe-card context into `event.channel_prompt`.
5. Enable the plugin in Nora profile config only after deterministic tests pass.
6. Run synthetic known/unknown sender tests and leak checks.
7. Run focused privacy/runtime audit.
8. Hold gateway restart for explicit operator approval.

## Runtime/plugin design constraints

- Wrap existing `identity_registry.py`; do not rewrite registry semantics.
- Use runtime JSON/engine only; do not load source YAML.
- Do not expose private/contact/raw fields.
- Unknown senders must produce no identity context.
- Plugin should not mutate memory or dispatch outbound messages.

## Council/review topology

Selected post-implementation audit roles:

- privacy boundary reviewer
- Hermes runtime plugin reviewer
- identity policy coherence reviewer

Council findings must be classified and handled before restart or RESOLVE.
