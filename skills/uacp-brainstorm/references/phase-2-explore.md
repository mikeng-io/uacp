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
- path: "skills/uacp-core/scripts/engines/domain/phase_graph.py"
  purpose: "Confirm the brainstorm->triage transition is codified"
  key_findings:
    - "LIFECYCLE_GRAPH models brainstorm with sole onward edge brainstorm->triage"
    - "brainstorm is a registered phase, not a pre-triage informal state"
  phase: 2
  timestamp: "{ISO-8601}"
```

**Codebase searches (Grep, Glob):**
```yaml
# manifest.yaml → exploration.searches_performed
- tool: Grep
  pattern: "STAGE_PHASE_EXIT_INVARIANTS"
  path: "skills/uacp-core/scripts/engines/domain/"
  result_count: 1
  key_findings:
    - "brainstorm exit invariant requires brainstorm/*/07-scope-package.yaml"
    - "Codified grammar lives in engines/domain/phase_transitions.py"
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

### 2.2 Update the session-vault references YAML files

Mirror the manifest entries into discrete files in the session vault's references directory `.uacp/brainstorm/{run_id}/references/` (the per-session vault, NOT this skill's own `references/` docs):

- `.uacp/brainstorm/{run_id}/references/files-read.yaml` — all `files_read` entries
- `.uacp/brainstorm/{run_id}/references/searches.yaml` — all `searches_performed` entries
- `.uacp/brainstorm/{run_id}/references/web-queries.yaml` — all `web_queries` entries

**Output of this phase:** candidate directions, early eliminations, and populated `manifest.yaml` + `.uacp/brainstorm/{run_id}/references/` evidence files.
