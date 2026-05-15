# Variants and Decision Space

## Acceptable variants

### Small skill variant

A simple skill may have only:

```text
SKILL.md
references/
```

if no templates/schemas/scripts are useful yet.

### Medium skill variant

```text
SKILL.md
references/
templates/
```

for phases that primarily produce human-readable artifacts.

### Structured skill variant

```text
SKILL.md
references/
templates/
schemas/
scripts/
```

for PLAN, VERIFY, STATE, and any phase with machine-checkable artifacts.

## Rejected variants

### One mega-roadmap
Rejected because it repeats the current failure.

### One mega-SOP in shared references
Rejected because phase ownership is lost.

### Giant SKILL.md per phase
Rejected because it moves context bloat into phase files.

### UACP-governed refactor
Rejected because UACP is currently the broken system being repaired.

### Bulk enrichment
Rejected because details get lost and ownership becomes unclear.
