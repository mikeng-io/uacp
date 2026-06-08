## Phase 1: Gather Signals

Before proposing anything, understand what the user is actually trying to do.

If `uacp-context` is available, invoke it:

```
Skill("uacp-context")
```

If `uacp-context` is not available, perform inline signal extraction.

### 1.1 Extract signals

```yaml
brainstorm_signals:
  topics: []                 # What the user is talking about
  concerns: []               # What worries them
  goals: []                  # What success looks like
  constraints: []            # Hard limits (time, budget, technology)
  explicit_domains: []       # Domains they mention
  artifact_type: ""          # code | docs | research | creative | mixed | unknown
  uacp_likely: false         # Does this look like it needs UACP governance?
  ambiguity_level: high | medium | low
```

Record ambiguity_level honestly. Brainstorm exists specifically because ambiguity is high. If it is already low, the user may not need this skill at all — route directly to TRIAGE.

### 1.2 Record evidence of context gathering

Every file read to understand context must be logged:

```yaml
# In manifest.yaml → exploration.files_read
- path: "docs/policy/constitution.md"
  purpose: "Understand current authority chain"
  phase: 1
  timestamp: "{ISO-8601}"
```

**Output of this phase:** a `brainstorm_signals` block and the first entries in `manifest.yaml`.
