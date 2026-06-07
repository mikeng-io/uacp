# Proposal: Nora Doctrine + Identity Registry Remediation

## What Is Changing

Nora's 5 doctrine files (KERNEL.md, SECURITY.md, SOUL.md, IDENTITY.md, PERSONALITY.md) and the identity-registry plugin are being updated to resolve a structural governance failure: the trust root has migrated from the system prompt to operator-authored YAML, and no doctrine file acknowledges this.

## Why It Is Changing

An agent council review (agent-council-20260605-170000) found 3 CRITICAL + 7 HIGH findings:

1. **Doctrine/plugin contradiction (CRITICAL):** The plugin injects a safe card into `channel_prompt` for recognized senders, but all 5 doctrine files contain blanket bans that directly forbid this behavior.

2. **Self-disclosure oracle (CRITICAL):** The safe card retains `relationship: {category: operator, trust_tier: owner}` and `address_as: 'Mike'`, which teaches the model an authority gradient and a name/role binding.

3. **Three-way trust conflict (CRITICAL):** The system prompt, plugin, and YAML conflict, and in any conflict the YAML wins because that's what the plugin emits.

## Remediation Tracks

### RT-1: Doctrinal Grant (CRITICAL)
**Findings:** SYN-CR1, SYN-CR3
**Changes:**
- Add to SECURITY.md: define runtime-injected `channel_prompt` as new authority tier
- Add to IDENTITY.md: carve out identity-registry context from blanket bans
- Add to KERNEL.md: authorize controlled mechanism for addressability
- Add to SOUL.md: update "must not reveal" rule to carve out authorized context

### RT-2: Tighten Safe Card (CRITICAL)
**Findings:** SYN-CR2, SYN-H6
**Changes:**
- Drop `relationship.trust_tier` from safe card in public/group channels
- Drop `identity_id` from safe card (stable handle defeats HMAC design)
- Gate `address_as` on chat type: DM = full card, group = tone + language_preference only
- Move `disclosure_policy` enforcement into plugin code, not LLM interpretation

### RT-3: Schema Validation (HIGH)
**Findings:** SYN-H2
**Changes:**
- Define single Card schema (e.g., `identity_registry/card_schema.py`)
- Have `compile_identity` produce only schema-allowed fields
- Add deny-by-default validation on YAML→runtime→plugin emission
- Move `service_access`, `facts`, `full names`, `nicknames` out of runtime JSON

### RT-4: Health/Observability (HIGH)
**Findings:** SYN-H4, SYN-M5
**Changes:**
- Add health check: verify runtime JSON exists, is readable, secret is loadable
- Add staleness check: compare mtime of source YAML vs. runtime JSON
- Add operator-visible logging: lookup success/fail, secret age, last refresh

### RT-5: Hook Contract (HIGH)
**Findings:** SYN-H1, SYN-H5
**Changes:**
- Document `pre_gateway_dispatch` event mutation in `hermes_cli/plugins.py`
- Add mutex for `channel_prompt` mutation in multi-plugin chain

### RT-6: Language/Tone Precedence (MEDIUM)
**Findings:** SYN-M1, SYN-M2
**Changes:**
- Define precedence: PERSONALITY.md thread-match rule > card language_preference
- Define tone as hint, not directive

## Authority
**Source:** Mike explicitly chose "C" — UACP-governed run.
**Status:** PASS
**Decision owner:** Mike

## Scope
**In scope:** Doctrine file changes, plugin code changes, security policy changes
**Out of scope:** Gateway restart, Honcho integration, persistent memory design, changes to Norty's profile

## Risks
1. **Behavioral change (HIGH):** Changes affect Nora's behavior; may have irreversible social effects
2. **Data leak (HIGH):** If safe card not tightened before doctrine changes, operator-only data may reach model
3. **LLM misinterpretation (MEDIUM):** LLM may not correctly interpret nuanced policy
4. **Gateway restart (MEDIUM):** Plugin changes require gateway restart (operator approval boundary)

## Verification Criteria
1. **Static analysis:** Doctrine files consistent, plugin code correct, schema validation passes
2. **Live testing (DM):** Nora responds correctly to identity questions in DM context
3. **Group testing:** Nora does not leak operator identity in public group context
4. **Security testing:** No operator-only data in model context

## Invariants
1. Doctrine consistency across all 5 files
2. Safe card must not leak operator-only data
3. Nora must correctly respond in both DM and group contexts
4. All changes reversible via git
