# Phase 9: Produce Context Report

Output the structured context report:

```yaml
context_report:
  skill: uacp-context
  session_id: "ctx-{YYYYMMDD-HHMMSS}-{random}"
  timestamp: "{ISO-8601}"

  artifact_type: code | uacp_lifecycle | financial | marketing | creative | research | mixed
  uacp_lifecycle_subtype: proposal | plan | verification | governance | null

  topics: []
  concerns: []
  domains: []
  domain_experts: []

  routing_advisory: direct | lightweight | standard | full_governance | block_or_clarify
  routing_rationale: ""

  council_recommendation:
    recommended: true | false
    tier: 0 | 1 | 2 | 3
    mode: ""
    reason: ""

  confidence: high | medium | low
  preflight_needed: true | false
  preflight_questions_asked: 0-3
  missing_signals: []

  uacp_state:
    active_run: "..." | null
    current_phase: "..." | null
    mode: "..." | null
    constraints_from_state: []

  governance_signals:
    governance_core: true | false
    cross_phase: true | false
    council_relevant: true | false
    state_mutation: true | false
    external_boundary: true | false

  enrichment:
    status: completed | skipped | failed
    backends_used: []
    findings_added: []

  signals_detected:
    files: []
    topics: []
    explicit_mentions: []
    uacp_signals: []

  assumptions: []
```

Display this report to the user and return it to the calling skill.

# Phase 10: Save Artifact

Save context report to `.uacp/context/{YYYYMMDD-HHMMSS}-context.md` with YAML frontmatter, plus JSON companion:

```yaml
---
skill: uacp-context
timestamp: {ISO-8601}
artifact_type: {artifact_type}
domains: [{domain1}, {domain2}]
routing_advisory: {routing}
confidence: {confidence}
context_summary: "{brief description of what was analyzed}"
session_id: "{session_id}"
---
```

**No symlinks.** To find the latest artifact:
```bash
ls -t .uacp/context/ | head -1
```

# Integration with Calling Skills

**`uacp-triage`** reads `context_report.routing_advisory`, `confidence`, `governance_signals`, and `domains` to inform admission and routing depth decisions.

**`uacp-council`** reads `context_report.domains`, `context_summary`, and `council_recommendation` to configure the council manifest.

**`uacp-propose`** reads `context_report.artifact_type`, `topics`, and `concerns` to frame the proposal scope.

**`uacp-brainstorm`** reads `context_report` as its starting point — if context is high-confidence, brainstorming skips questions and proceeds to approach generation.

# Notes

- **Pre-flight pattern:** Other skills can call this at the start to determine routing before spawning agents
- **Progressive enhancement:** If the domain registry is not found, fall back to basic artifact type detection
- **Non-blocking:** Always produces a result, even with low confidence
- **Model-agnostic:** Works in any Claude, Gemini, Codex, Kimi, or OpenCode context
- **Web enrichment is optional:** Only invoked when local signals are genuinely insufficient
- **UACP state awareness:** Distinguishes this from generic context skills — understands active runs, phase constraints, and governance implications
