# Work Packages

## WP-1: Inventory (wu1)

**Description:** Verify target files exist; record git HEAD; read all 5 doctrine files and plugin/registry code.

**Dependencies:** None

**Target files:**
- /home/norty/.hermes/profiles/nora/KERNEL.md
- /home/norty/.hermes/profiles/nora/SECURITY.md
- /home/norty/.hermes/profiles/nora/SOUL.md
- /home/norty/.hermes/profiles/nora/IDENTITY.md
- /home/norty/.hermes/profiles/nora/PERSONALITY.md
- /home/norty/.hermes/profiles/nora/plugins/identity_registry/__init__.py
- /home/norty/.hermes/operator-data/nora/identity-registry/identity_registry.py

**Obligations:**
- Git HEAD recorded for all 8 target files
- All 5 doctrine files read and analyzed
- Plugin __init__.py and identity_registry.py read

**Evidence type:** file_read + git_log

## WP-2: Tighten Safe Card (wu2) — RT-2

**Description:** Tighten safe card: drop trust_tier, drop identity_id, gate address_as, add null fallback, remove username fallback.

**Dependencies:** WP-1

**Target file:** /home/norty/.hermes/profiles/nora/plugins/identity_registry/__init__.py

**Obligations:**
- Plugin __init__.py modified with _safe_card changes
- Compile check passes
- Leak scan: safe card no longer contains trust_tier or identity_id

**Evidence type:** file_patch + python_compile + grep

## WP-3: Schema Validation (wu3) — RT-3

**Description:** Add deny-by-default schema validation; move service_access/facts/names out of runtime JSON.

**Dependencies:** WP-1

**Target files:**
- /home/norty/.hermes/operator-data/nora/identity-registry/identity_registry.py
- /home/norty/.hermes/operator-data/nora/identity-registry/identity_registry.runtime.json

**Obligations:**
- identity_registry.py has schema validation function
- compile_identity produces only schema-allowed fields
- Runtime JSON regenerated, new schema

**Evidence type:** file_patch + python_compile + regenerate_json

## WP-4: Doctrinal Grant (wu4) — RT-1

**Description:** Add doctrinal grant to SECURITY.md, IDENTITY.md, KERNEL.md, SOUL.md; add trust_tier veto.

**Dependencies:** WP-2, WP-3

**Target files:**
- /home/norty/.hermes/profiles/nora/SECURITY.md
- /home/norty/.hermes/profiles/nora/IDENTITY.md
- /home/norty/.hermes/profiles/nora/KERNEL.md
- /home/norty/.hermes/profiles/nora/SOUL.md

**Obligations:**
- SECURITY.md has identity-registry authority tier
- IDENTITY.md has identity-registry carve-out
- KERNEL.md authorizes controlled mechanism
- SOUL.md updates 'must not reveal' rule
- grep for 'identity-registry' shows 4+ doctrine files

**Evidence type:** file_patch + grep

## WP-5: Health/Observability (wu5) — RT-4

**Description:** Add health check, staleness check, operator-visible logging, ERROR-level on silent fail.

**Dependencies:** WP-2

**Target file:** /home/norty/.hermes/profiles/nora/plugins/identity_registry/__init__.py

**Obligations:**
- Plugin __init__.py has health_check() function
- Silent fail now logs ERROR with traceback
- Compile check passes

**Evidence type:** file_patch + python_compile

## WP-6: Hook Contract (wu6) — RT-5

**Description:** Document pre_gateway_dispatch event mutation in plugin comment.

**Dependencies:** WP-2

**Target file:** /home/norty/.hermes/profiles/nora/plugins/identity_registry/__init__.py

**Obligations:**
- Plugin __init__.py has hook contract comment

**Evidence type:** file_patch

## WP-7: Language/Tone Precedence (wu7) — RT-6

**Description:** Add language/tone precedence to PERSONALITY.md.

**Dependencies:** WP-4

**Target file:** /home/norty/.hermes/profiles/nora/PERSONALITY.md

**Obligations:**
- PERSONALITY.md has language precedence rule
- PERSONALITY.md has tone hint-not-directive rule

**Evidence type:** file_patch + grep

## WP-8: Verification (wu8)

**Description:** Static verification: compile, leak scan, doctrine consistency, plugin import.

**Dependencies:** WP-2 through WP-7

**Obligations:**
- All .py files compile
- Safe card leak scan passes
- Doctrine grep shows identity-registry in 4+ files
- Plugin imports successfully under HERMES_HOME

**Evidence type:** terminal_commands
