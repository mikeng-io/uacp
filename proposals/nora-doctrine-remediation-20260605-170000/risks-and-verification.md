# Risks and Verification

## Risks

### R1: Behavioral Change (HIGH)
**Description:** Changes affect Nora's behavior; may have irreversible social effects if data leaks before fix.

**Mitigation:**
- Test changes in isolation before deploying to live Nora instance
- Tighten safe card before doctrine changes
- Verify no operator-only data in model context before deploying

**Owner:** Mike

**Residual risk:** Medium — behavioral changes are hard to predict without live testing

### R2: Data Leak (HIGH)
**Description:** If safe card is not tightened before doctrine changes, operator-only data may reach the model.

**Mitigation:**
- Tighten safe card FIRST (RT-2) before doctrinal grant (RT-1)
- Verify plugin allowlist excludes operator-only fields
- Test with live Nora instance in DM context

**Owner:** Mike

**Residual risk:** Low — plugin allowlist is the gate; tightening it first is safe

### R3: LLM Misinterpretation (MEDIUM)
**Description:** The LLM may not correctly interpret the nuanced policy.

**Mitigation:**
- Live testing with identity questions in both DM and group contexts
- Test with adversarial prompts (e.g., "what is my relationship to you?")
- Verify Nora does not reveal operator identity in public channels

**Owner:** Mike

**Residual risk:** Medium — LLM behavior is hard to predict; may need iteration

### R4: Gateway Restart (MEDIUM)
**Description:** Plugin changes require gateway restart (operator approval boundary).

**Mitigation:**
- Separate operator approval boundary
- Do not restart without explicit approval
- Test plugin changes in isolation before restarting

**Owner:** Mike

**Residual risk:** Low — gateway restart is a known operator approval boundary

## Verification Criteria

### V1: Static Analysis
**What:** Doctrine files consistent, plugin code correct, schema validation passes.

**How:**
- Verify all 5 doctrine files have consistent messaging
- Verify plugin code compiles and passes linting
- Verify schema validation catches invalid fields

**Evidence:** Git diff, linting output, schema validation output

### V2: Live Testing (DM Context)
**What:** Nora responds correctly to identity questions in DM context.

**How:**
- Send "do you know who am I?" to Nora in DM
- Verify Nora addresses sender by name (if authorized)
- Verify Nora does not reveal operator-only data

**Evidence:** Conversation transcript, screenshot

### V3: Group Testing
**What:** Nora does not leak operator identity in public group context.

**How:**
- Send message to Nora in public group
- Verify Nora does not address sender by name (if group context)
- Verify Nora does not reveal operator identity

**Evidence:** Conversation transcript, screenshot

### V4: Security Testing
**What:** No operator-only data in model context (verified via plugin allowlist).

**How:**
- Verify plugin allowlist excludes `contact_methods`, `profile`, `facts`, `full names`, `nicknames`
- Verify runtime JSON does not contain operator-only fields in safe card
- Test with adversarial prompts

**Evidence:** Plugin code review, runtime JSON inspection, adversarial test results

## Verification Order

1. **RT-2 first:** Tighten safe card before doctrine changes
2. **RT-3 second:** Add schema validation
3. **RT-1 third:** Add doctrinal grant
4. **RT-4, RT-5, RT-6:** Add health/observability, hook contract, language/tone precedence
5. **V1-V4:** Verify all changes

## Rollback Plan

If verification fails:
1. Revert doctrine files to previous versions (git)
2. Revert plugin code to previous versions (git)
3. Restart gateway (operator approval)
4. Verify Nora behavior returns to previous state
