## Phase 6: Write the Obsidian Vault

Dump the raw thinking material into `.outputs/brainstorm/` as an Obsidian-style vault. This is disposable documentation, not canonical state.

**Vault path:**

```
.outputs/brainstorm/{YYYYMMDD-HHMMSS}-{session_id}/
├── 00-index.md
├── 01-signals.md
├── 02-exploration.md
├── 03-questions.md
├── 04-approaches.md
├── 05-selected-scope.md
└── 06-next-steps.md
```

Each file should have YAML frontmatter and use Obsidian-style backlinks:

```yaml
---
title: Selected Scope
session_id: "{session_id}"
timestamp: "{ISO-8601}"
tags: [brainstorm, scope, uacp-candidate]
---

# Selected Scope

See also: [[00-index]], [[04-approaches]]

## What we agreed to explore

{description}

## Why this scope

{rationale}

## What is explicitly out of scope

{out_of_scope}

## UACP admission decision

- Enter UACP: true | false
- If true: hand off to TRIAGE with [[07-scope-package]]
- If false: stop here; vault remains for reference
```

**Output of this phase:** a complete Obsidian vault under `.outputs/brainstorm/`.
