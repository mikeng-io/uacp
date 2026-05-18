# Proposal

## What we are changing

Create a Nora profile-local Hermes plugin that performs inbound reverse lookup against the existing Nora Identity Registry runtime data and injects only the current sender's sanitized safe card into ephemeral prompt context.

## Why we are changing it

Nora operates in public/group contexts and needs enough identity context to answer coherently without borrowing private Norty memory. The identity registry is the public-safe boundary mechanism: it gives Nora current-sender context while preserving the Norty/Nora separation.

The rational intent is not to make Nora broadly stateful. It is to provide a narrow, event-local identity hint for the current sender only.

## Decision

Proceed with a bounded profile-local plugin implementation. Do not modify Hermes core, do not restart Nora's gateway, and do not enable outbound dispatch in this tranche.

## Invariants

- Current sender only: lookup must use the inbound event source, not broad session context.
- Sanitized fields only: no raw operator-only data, raw phone/email, or source YAML enters Nora prompt context.
- Profile-local scope: changes stay under Nora's profile plugin boundary unless a plugin seam blocker is proven.
- No live side effects: gateway restart and live sends remain explicit operator boundaries.
