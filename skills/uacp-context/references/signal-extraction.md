# Phase 1: Extract Conversation Signals

Analyze the current conversation and extract structured signals:

```yaml
conversation_signals:
  files_mentioned: []        # File paths referenced (e.g., "src/auth.go")
  artifacts_mentioned: []    # UACP lifecycle artifacts (proposals, plans, verification reports)
  topics: []                 # Key topics discussed
  concerns: []               # What the user is worried about
  explicit_domains: []       # Domains explicitly named by user
  explicit_routing: ""       # If user said "multi-model", "debate", "thorough", etc.
  intent: ""                 # review | audit | verify | research | implement | plan | explore | brainstorm
  uacp_signals: []           # UACP-specific signals (see below)
```

### UACP-specific signal detection

Detect signals that indicate governance relevance:

```yaml
uacp_signal_rules:
  governance_core:
    signals:
      - "lifecycle", "phase", "gate", "transition", "authority"
      - "Guardian", "Heartgate", "policy", "protected state"
      - "artifact schema", "validator", "fixture", "runtime enforcement"
    implication: "Work touches UACP governance core — likely requires full_governance routing"

  cross_phase:
    signals:
      - "PROPOSE", "PLAN", "EXECUTE", "VERIFY", "RESOLVE"
      - "triage", "admission", "routing", "granularity"
    implication: "Work spans multiple UACP phases — needs lifecycle-aware context"

  council_relevant:
    signals:
      - "council", "review", "audit", "debate", "verify", "deep"
      - "multi-model", "cross-runtime", "adversarial"
    implication: "Work involves Agent Council — detect optimal tier and mode"

  state_mutation:
    signals:
      - "state write", "state change", " Kanban", "run registry", "transition"
      - "modify files", "edit code", "implement", "build"
    implication: "Work may modify project state — capability_profile may be 'modify'"

  external_boundary:
    signals:
      - "public", "private", "registry", "API", "external", "deploy"
      - "Nora", "Cortex", "LEXA", "MEMEX", "BES"
    implication: "Work touches external/public boundary — may need authority verification"
```
