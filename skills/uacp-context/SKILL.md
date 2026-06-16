---
name: uacp-context
description: >
  Deep context analyzer for UACP. Extracts conversation signals, classifies artifacts,
  detects domains from domain-registry, reads active UACP run state, optionally enriches
  via web backends (Tavily/Firecrawl/Context7), assesses confidence, and produces a
  structured context report. Includes inline preflight questioning when confidence is low.
  Every major UACP operation should start here.
location: managed
dependencies:
  - uacp-council-taxonomy
  - domain-registry
  - uacp-web
  - uacp-state
  - uacp-bridge
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(ls *)
  - Bash(cat *)
  - Bash(git log *)
  - Bash(git diff *)
  - Bash(git remote -v)
  - Task
  - Write
  - Bash(mkdir *)
---

# UACP Context: Deep Context Analyzer + Smart Router

Execute this skill to analyze the current conversation and project state, classify what is being discussed, detect relevant domains, assess UACP governance implications, and determine the optimal routing strategy.

**This is the recommended first skill to run before any major UACP operation.** It feeds `uacp-triage`, `uacp-council`, `uacp-propose`, and downstream phases.

## Quick Start

Before executing, verify required skills are present:

```
[skills-root]/domain-registry/README.md
[skills-root]/uacp-council-taxonomy/SKILL.md
[skills-root]/uacp-bridge/SKILL.md
```

If `uacp-web` is present, web enrichment is available. If `uacp-state` is present, active-run context is available. Neither is blocking — the skill degrades gracefully.

If `domain-registry` is missing → stop immediately and emit an install advisory.

## Execution Flow

Run these phases in order. Read each referenced guide inline and apply its instructions to build the `context_report`.

1. **Phase 1: Extract Conversation Signals** — Read `references/signal-extraction.md`
2. **Phase 2: Read Active UACP State** — Read `references/uacp-state-integration.md`
3. **Phase 3: Classify Artifact Type** — Read `references/artifact-classification.md`
4. **Phase 4: Enrich Context via Web Backends** — Read `references/web-enrichment.md`
5. **Phase 5: Select Domains from Domain-Registry** — Read `references/domain-selection.md`
6. **Phase 6: Determine Routing** — Read `references/routing-rules.md`
7. **Phase 7: Determine Confidence and Missing Signals** — Read `references/confidence-assessment.md`
8. **Phase 8: Preflight Questioning** — Read `references/preflight-questioning.md`
9. **Phase 9: Produce Context Report & Phase 10: Save Artifact** — Read `references/context-report-schema.md`

After Phase 9, display the final report to the user and return it to the calling skill.
