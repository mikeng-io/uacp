# Authority, Scope, and Containment

## Authority

**Source:** Mike explicitly chose "C" — UACP-governed run for Nora doctrine remediation.

**Status:** PASS

**Decision owner:** Mike

**Authorization chain:**
1. Mike asked "do u think u need one?" about NanoKVM-Pro
2. Discussion evolved to Nora's identity registry
3. Mike asked "why NOT KERNAL.md?" for the doctrinal grant
4. Mike suggested "release the gate of 'do not expose any private or personal information'"
5. Mike chose "C" — UACP-governed run for the remediation

## Scope

### In Scope

1. **Doctrinal grant (RT-1):** Add to SECURITY.md and IDENTITY.md defining runtime-injected `channel_prompt` as new authority tier
2. **Tighten safe card (RT-2):** Drop `relationship.trust_tier` and operator-acknowledgeable facts in public/group channels
3. **Schema validation (RT-3):** Deny-by-default validation on YAML→runtime→plugin emission
4. **Health/observability (RT-4):** Operator-visible lookup success/fail, secret age, last refresh
5. **Hook contract (RT-5):** Document `pre_gateway_dispatch` event mutation
6. **Language/tone precedence (RT-6):** Define between PERSONALITY.md and the card

### Out of Scope

1. **Gateway restart:** Separate operator approval boundary
2. **Honcho integration:** `peerName` fixed, doesn't fit multi-person design
3. **Persistent memory design:** Separate UACP run
4. **Changes to Norty's profile:** Out of scope
5. **Changes to other plugins/skills:** Out of scope

## Containment

**Profile boundary:** Changes are scoped to Nora's profile (`/home/norty/.hermes/profiles/nora/`).

**No cross-profile leakage:** Changes do not affect Norty's profile, other profiles, or the root Hermes installation.

**No external side effects:** Changes do not affect external services, platforms, or users beyond Nora's current conversation surfaces.

**Rollback path:** All changes are reversible via git. Doctrine files and plugin code can be reverted to previous versions.

## Invariants

1. **Doctrine consistency:** All 5 doctrine files must have consistent messaging about the identity-registry plugin
2. **Security posture:** The safe card must not leak operator-only data to the model
3. **Behavioral verification:** Nora must correctly respond to identity questions in both DM and group contexts
4. **Rollback path:** All changes must be reversible via git

## Human Involvement

**Required:** Yes

**Reason:** Doctrine file changes are high-impact identity changes. Plugin code changes need operator approval before deployment. Gateway restart is operator approval boundary.

**Authority needed:** Approval for doctrine changes, plugin code changes, and gateway restart.

**Decision owner:** Mike
