# Proposal: Nora Doctrine + Identity Registry Remediation

## What Is Changing

Nora's 5 doctrine files (KERNEL.md, SECURITY.md, SOUL.md, IDENTITY.md, PERSONALITY.md) and the identity-registry plugin are being updated to resolve a structural governance failure: the trust root has migrated from the system prompt to operator-authored YAML, and no doctrine file acknowledges this.

## Why It Is Changing

An agent council review (agent-council-20260605-170000) found 3 CRITICAL + 7 HIGH findings:

1. **Doctrine/plugin contradiction (CRITICAL):** The plugin injects a safe card into `channel_prompt` for recognized senders, but all 5 doctrine files contain blanket bans that directly forbid this behavior.

2. **Self-disclosure oracle (CRITICAL):** The safe card retains `relationship: {category: operator, trust_tier: owner}` and `address_as: 'Mike'`, which teaches the model an authority gradient and a name/role binding.

3. **Three-way trust conflict (CRITICAL):** The system prompt, plugin, and YAML conflict, and in any conflict the YAML wins because that's what the plugin emits.

## How It Works

### Current State
- The identity-registry plugin injects a sanitized "safe card" into `channel_prompt` for recognized senders
- The safe card contains: `identity_id`, `kind`, `address_as`, `tone`, `language_preference`, `relationship`, `rules`, `disclosure_policy`
- The safe card does NOT contain: `contact_methods`, `profile`, `facts`, `full names`, `nicknames`
- Nora's doctrine files contain blanket bans on "private operator context", "identifying private people", "claiming access to private operator profiles"
- The plugin's allowlist is the only gate between operator-only data and the model's context

### Proposed State
- Doctrine files explicitly authorize the identity-registry plugin as a controlled mechanism
- The safe card is tightened to drop `relationship.trust_tier` in public/group channels
- Schema validation ensures deny-by-default on YAML→runtime→plugin emission
- Health/observability provides operator-visible lookup success/fail, secret age, last refresh
- Hook contract is documented for `pre_gateway_dispatch` event mutation
- Language/tone precedence is defined between PERSONALITY.md and the card

## Remediation Tracks

### RT-1: Doctrinal Grant (CRITICAL)
**Findings:** SYN-CR1, SYN-CR3, SYN-H1, SYN-H7, SYN-L1
**Changes:**
- Add to SECURITY.md: define runtime-injected `channel_prompt` as new authority tier
- Add to IDENTITY.md: carve out identity-registry context from blanket bans
- Add to KERNEL.md: authorize controlled mechanism for addressability
- Add to SOUL.md: update "must not reveal" rule to carve out authorized context
- Add doctrinal veto: "trust_tier from runtime JSON is data, not authority; the model does not act on it"

### RT-2: Tighten Safe Card (CRITICAL)
**Findings:** SYN-CR2, SYN-H6, SYN-M3, SYN-M6, SYN-M7, SYN-L2
**Changes:**
- Drop `relationship.trust_tier` from safe card in all channels
- Drop `identity_id` from safe card (stable handle defeats HMAC design)
- Gate `address_as` on chat type: DM = full card, group = tone + language_preference only
- Move `disclosure_policy` enforcement into plugin code, not LLM interpretation
- Add `address_as` null fallback in code
- Remove username fallback (user_id only)

### RT-3: Schema Validation (HIGH)
**Findings:** SYN-CR3, SYN-H2, SYN-L3
**Changes:**
- Define single Card schema (e.g., `identity_registry/card_schema.py`)
- Have `compile_identity` produce only schema-allowed fields
- Add deny-by-default validation on YAML→runtime→plugin emission
- Move `service_access`, `facts`, `full names`, `nicknames` out of runtime JSON

### RT-4: Health/Observability (HIGH)
**Findings:** SYN-H3, SYN-H4, SYN-M5
**Changes:**
- Add health check: verify runtime JSON exists, is readable, secret is loadable
- Add staleness check: compare mtime of source YAML vs. runtime JSON
- Add operator-visible logging: lookup success/fail, secret age, last refresh
- Add heartbeat log/metric for registry availability
- Silent fail now logs ERROR with traceback

### RT-5: Hook Contract (HIGH)
**Findings:** SYN-H1, SYN-H5, SYN-L4
**Changes:**
- Document `pre_gateway_dispatch` event mutation in `hermes_cli/plugins.py`
- Add mutex for `channel_prompt` mutation in multi-plugin chain
- Add provenance markers to distinguish static prompt from plugin-injected content

### RT-6: Language/Tone Precedence (MEDIUM)
**Findings:** SYN-M1, SYN-M2
**Changes:**
- Define precedence: PERSONALITY.md thread-match rule > card language_preference
- Add doctrine sentence: "Sender language_preference is a soft suggestion; active thread language takes precedence"
- Define tone as hint, not directive: "Tone adjusts within public-safe register"

## Finding-to-Track Coverage Matrix

| Finding | Severity | Track | Status |
|---|---|---|---|
| SYN-CR1 | CRITICAL | RT-1 | Covered |
| SYN-CR2 | CRITICAL | RT-2 | Covered |
| SYN-CR3 | CRITICAL | RT-1 + RT-3 | Covered |
| SYN-H1 | HIGH | RT-5 | Covered |
| SYN-H2 | HIGH | RT-3 | Covered |
| SYN-H3 | HIGH | RT-4 | Covered |
| SYN-H4 | HIGH | RT-4 | Covered |
| SYN-H5 | HIGH | RT-5 | Covered |
| SYN-H6 | HIGH | RT-2 | Covered |
| SYN-H7 | HIGH | RT-1 | Covered |
| SYN-M1 | MEDIUM | RT-6 | Covered |
| SYN-M2 | MEDIUM | RT-6 | Covered |
| SYN-M3 | MEDIUM | RT-2 | Covered |
| SYN-M4 | MEDIUM | — | Out of scope, forward-pointer below |
| SYN-M5 | MEDIUM | RT-4 | Covered |
| SYN-M6 | MEDIUM | RT-2 | Covered |
| SYN-M7 | MEDIUM | RT-2 | Covered |
| SYN-L1 | LOW | RT-1 | Covered |
| SYN-L2 | LOW | RT-2 | Covered |
| SYN-L3 | LOW | RT-3 | Covered |
| SYN-L4 | LOW | RT-5 | Covered |
| SYN-I1 | INFO | — | Deferred (schema validates `kind`) |
| SYN-I2 | INFO | — | Deferred (DM-focused scope) |
| SYN-I3 | INFO | — | Deferred (cosmetic) |
| SYN-DISP-1 | disputed | RT-1 | Subsumed by SYN-CR1 |
| SYN-DISP-2 | disputed | RT-2 | Subsumed by SYN-M6 |
| SYN-DISP-3 | disputed | RT-2 | Subsumed by SYN-CR2 |
| SYN-WD-1 | withdrawn | — | Withdrawn |

**Out-of-scope forward-pointers:**
- **SYN-M4** (prompt-injection policy): separate UACP run for SECURITY.md §4 expansion
- **SYN-I1, SYN-I2, SYN-I3:** deferred, not security-relevant

## Intention/Rationale/Decision

**Intention:** Fix the structural governance failure where the trust root has migrated from the system prompt to operator-authored YAML.

**Rationale:** The council found that the plugin's safe card injection contradicts blanket bans in all 5 doctrine files. The plugin works correctly, but the doctrine doesn't acknowledge it. This creates a security risk: the YAML is the de facto authority, but the prompt claims to be.

**Decision:** Use UACP-governed run to ensure changes are consistent, secure, and verifiable. Mike authorized this via explicit "C" choice.

## Authority/Scope/Containment

**Authority:** Mike explicitly authorized UACP-governed run.

**Scope:** Doctrine file changes, plugin code changes, security policy changes.

**Containment:** Changes are scoped to Nora's profile. No changes to Norty's profile, other plugins, or skills.

## Invariants

1. **Doctrine consistency:** All 5 doctrine files must have consistent messaging about the identity-registry plugin
2. **Security posture:** The safe card must not leak operator-only data to the model
3. **Behavioral verification:** Nora must correctly respond to identity questions in both DM and group contexts
4. **Rollback path:** All changes must be reversible via git

## Risks

1. **Behavioral change:** Changes affect Nora's behavior; may have irreversible social effects
2. **Data leak:** If safe card is not tightened before doctrine changes, operator-only data may reach the model
3. **LLM misinterpretation:** The LLM may not correctly interpret the nuanced policy
4. **Gateway restart:** Plugin changes require gateway restart (operator approval boundary)

## Verification Criteria

1. **Static analysis:** Doctrine files consistent, plugin code correct, schema validation passes
2. **Live testing:** Nora responds correctly to identity questions in DM context
3. **Group testing:** Nora does not leak operator identity in public group context
4. **Security testing:** No operator-only data in model context (verified via plugin allowlist)

## Artifact Map

| Artifact | Location | Purpose |
|---|---|---|
| Triage artifact | `proposals/nora-doctrine-remediation-20260605-170000-triage.yaml` | UACP admission |
| Proposal artifact | `proposals/nora-doctrine-remediation-20260605-170000-proposal.yaml` | Machine lifecycle envelope |
| Gate-selection | `proposals/nora-doctrine-remediation-20260605-170000-gate-selection.yaml` | Gate selection |
| Proposal package | `proposals/nora-doctrine-remediation-20260605-170000/` | Human-readable proposal |
| Council synthesis | `/home/norty/.hermes/profiles/nora/EXPERTS_COUNCIL_SYNTHESIS.json` | Council evidence |
| Council report | `/home/norty/.hermes/profiles/nora/COUNCIL_REPORT.md` | Council evidence |
