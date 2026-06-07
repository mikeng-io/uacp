# Verification Strategy

## Deterministic Checks

### V1: Compile Check
**Command:** `python -m py_compile <file>.py`

**What:** Verify all modified Python files compile.

**Targets:**
- /home/norty/.hermes/profiles/nora/plugins/identity_registry/__init__.py
- /home/norty/.hermes/operator-data/nora/identity-registry/identity_registry.py

**Evidence:** Compile output (no errors)

### V2: Safe Card Leak Scan
**What:** Verify safe card no longer contains operator-only fields.

**Check fields that should NOT appear in safe card:**
- `trust_tier` (RT-2)
- `identity_id` (RT-2)
- `service_access` (RT-3)
- `facts` (RT-3)
- `full`, `english_full`, `chinese_full`, `nicknames` in names (RT-3)

**Method:** grep or AST parse of plugin _safe_card function

**Evidence:** grep output showing forbidden fields absent

### V3: Doctrine Consistency
**Command:** `grep -l "identity-registry" /home/norty/.hermes/profiles/nora/*.md`

**Expected:** 4+ files mention identity-registry:
- KERNEL.md
- SECURITY.md
- IDENTITY.md
- SOUL.md
- (PERSONALITY.md optional, for RT-6)

**Evidence:** File list from grep

### V4: Plugin Import
**Command:**
```bash
HERMES_HOME=/home/norty/.hermes/profiles/nora \
  python -c "import sys; sys.path.insert(0, '/home/norty/.hermes/profiles/nora/plugins/identity_registry'); import __init__; print('OK')"
```

**What:** Verify plugin still imports after changes.

**Evidence:** "OK" output

### V5: Runtime JSON Schema
**What:** Verify runtime JSON contains only schema-allowed fields.

**Method:** parse runtime JSON, check key set against schema

**Evidence:** JSON structure validation

## Live Testing (Deferred to Operator)

### L1: DM Identity Test
**What:** Send "do u know who am I" to Nora in DM.

**Expected behavior:**
- Nora addresses Mike by name (or preferred)
- Nora does not reveal operator-only data

**Evidence:** Conversation transcript, screenshot

### L2: Group Identity Test
**What:** Send message to Nora in public group.

**Expected behavior:**
- Nora does NOT address sender by name (group context)
- Nora does not reveal operator identity

**Evidence:** Conversation transcript, screenshot

## Council Review (Post-Implementation)

**Roles:**
1. implementation-completeness-reviewer — verify all 8 work packages complete
2. security-posture-reviewer — verify no operator-only data in model context
3. doctrine-consistency-reviewer — verify all 5 doctrine files consistent

**Timing:** After WP-1 through WP-7 complete, before VERIFY→RESOLVE

**Output:** `verification/nora-doctrine-remediation-20260605-170000-council-synthesis.yaml`

## Verification Order

1. WP-1 (inventory) — read-only, no verification needed
2. WP-2 (safe card) — V1, V2
3. WP-3 (schema) — V1, V5
4. WP-4 (doctrine) — V3
5. WP-5 (health) — V1
6. WP-6 (hook) — V1
7. WP-7 (language) — V3
8. WP-8 (verify) — V1, V2, V3, V4, V5, council review
