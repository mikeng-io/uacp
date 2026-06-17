## Phase 2: Explore Possibilities and Constraints

Using the signals from Phase 1, explore the design space without committing to a direction.

**Activities:**

1. Read relevant project files, docs, or recent commits.
2. Identify what is technically possible given the current codebase or environment.
3. Identify hard constraints that will eliminate some approaches early.
4. Surface implicit assumptions that the user may not have stated.

**Questions to answer internally (not necessarily to ask the user yet):**

- What is the smallest version of this that could work?
- What is the largest version the user might accidentally be imagining?
- What existing systems, APIs, or invariants would this touch?
- What is explicitly out of scope based on constraints?

### 2.1 Record every search and read as structured evidence

Every tool invocation during exploration must leave a trace in `manifest.yaml`:

**File reads:**
```yaml
# manifest.yaml → exploration.files_read
- path: "config/phase-transitions.yaml"
  purpose: "Check if brainstorm->triage transition exists"
  key_findings:
    - "Valid transitions start at triage->propose"
    - "No pre-triage state modeled"
  phase: 2
  timestamp: "{ISO-8601}"
```

**Codebase searches (Grep, Glob, Bash):**
```yaml
# manifest.yaml → exploration.searches_performed
- tool: Grep
  pattern: "check-preflight"
  path: "skills/"
  result_count: 3
  key_findings:
    - "Referenced in uacp-brainstorm phase-8-admission.md"
    - "Guardian script at skills/uacp-core/scripts/guardian.py"
  phase: 2
  timestamp: "{ISO-8601}"
```

**Web queries (if uacp-web or bridge skills used):**
```yaml
# manifest.yaml → exploration.web_queries
- query: "pydantic v2 field_validator migration guide"
  source: tavily
  result_summary: "3 relevant docs found; @field_validator replaces @validator"
  phase: 2
  timestamp: "{ISO-8601}"
```

### 2.2 Update references/ YAML files

Mirror the manifest entries into discrete files for external tooling:

- `references/files-read.yaml` — all `files_read` entries
- `references/searches.yaml` — all `searches_performed` entries
- `references/web-queries.yaml` — all `web_queries` entries

**Output of this phase:** candidate directions, early eliminations, and populated `manifest.yaml` + `references/` evidence files.
