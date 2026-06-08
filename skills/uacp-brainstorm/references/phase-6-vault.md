## Phase 6: Write the Obsidian Vault

Dump the raw thinking material into `.outputs/brainstorm/` as an Obsidian-style vault. This is disposable documentation, not canonical state.

**Anti-collapse rule:** One phase = one markdown file. Never merge phases into a single document. The vault exists so each phase's reasoning remains separable and inspectable.

**Vault path:**

```
.outputs/brainstorm/{YYYYMMDD-HHMMSS}-{session_id}/
├── manifest.yaml              # Machine-readable index of the entire brainstorm
├── 00-index.md                # Human-readable map of the vault
├── 01-signals.md              # Phase 1: what the user signaled
├── 02-exploration.md          # Phase 2: what was discovered
├── 03-questions.md            # Phase 3: clarifying Q&A
├── 04-approaches.md           # Phase 4: candidate sketches
├── 05-selected-scope.md       # Phase 5: agreed scope
├── 06-next-steps.md           # Phase 6+: handoff notes
└── references/
    ├── files-read.yaml        # Every file read during exploration
    ├── searches.yaml          # Every search command and result summary
    └── web-queries.yaml       # Every web query and result summary
```

### 6.1 Machine-readable manifest (`manifest.yaml`)

This file is the structured backbone. Every markdown file narrates; `manifest.yaml` records.

```yaml
kind: uacp.brainstorm_manifest
session_id: "{session_id}"
timestamp: "{ISO-8601}"
phases_completed: [1, 2, 3, 4, 5, 6]

signals:
  topics: []
  concerns: []
  goals: []
  constraints: []
  explicit_domains: []
  artifact_type: ""
  uacp_likely: false
  ambiguity_level: high | medium | low

exploration:
  files_read:
    - path: "docs/policy/constitution.md"
      purpose: "Understand authority chain"
      phase: 1
      timestamp: "{ISO-8601}"
  searches_performed:
    - tool: Grep
      pattern: "brainstorm"
      path: "skills/"
      result_count: 12
      phase: 2
      timestamp: "{ISO-8601}"
    - tool: Bash
      command: "git log --oneline -5"
      purpose: "Recent codebase context"
      phase: 2
      timestamp: "{ISO-8601}"
  web_queries:
    - query: "..."
      source: tavily | firecrawl | devin | context7
      result_summary: "..."
      phase: 2
      timestamp: "{ISO-8601}"

approaches_sketched:
  - id: "A1"
    title: "..."
    complexity: low | medium | high
    selected: true | false

selected_scope:
  title: "..."
  approach_id: "A1"
  enter_uacp: true | false
  rationale: "..."

admission:
  guardian_status: pass | warn | block
  heartgate_status: coherent | incoherent | skipped
  findings: []
```

**Rule:** Update `manifest.yaml` after every phase. Do not wait until the end.

### 6.2 Human-readable markdown files

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

### 6.3 References subdirectory

Every search, file read, and web query during Phases 1–2 must leave a trace in `references/`:

- **`files-read.yaml`** — path, purpose, key takeaway, timestamp
- **`searches.yaml`** — tool, pattern/command, path, result count, timestamp
- **`web-queries.yaml`** — query string, source backend, result summary, timestamp

**Output of this phase:** a complete Obsidian vault under `.outputs/brainstorm/` with both human narrative (markdown) and machine-readable evidence (YAML).
