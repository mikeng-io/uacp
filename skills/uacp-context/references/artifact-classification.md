# Phase 3: Classify Artifact Type

Determine the primary artifact type from signals. UACP extends standard classification with lifecycle-aware types:

```yaml
artifact_type_rules:
  code:
    signals:
      - File extensions: .go, .py, .ts, .js, .rs, .java, .rb, .kt, .swift, .c, .cpp
      - Mentions of: function, class, module, API, endpoint, service, handler

  uacp_lifecycle:
    signals:
      - Files in: proposals/, plans/, verification/, state/, config/
      - Terms: proposal, plan, gate, ledger, artifact, fixture, validator
      - UACP phase labels: TRIAGE, PROPOSE, PLAN, EXECUTE, VERIFY, RESOLVE
    subtypes:
      - proposal      # Authority/scope declaration
      - plan          # Execution graph artifact
      - verification  # Evidence/audit artifact
      - governance    # Policy/config/schema change

  financial:
    signals:
      - Terms: P&L, revenue, profit, loss, budget, forecast, balance sheet, ROI, EBITDA
      - Spreadsheet files: .xlsx, .csv with financial column names
      - GAAP, IFRS, accounting mentions

  marketing:
    signals:
      - Terms: campaign, audience, conversion, CTR, CPC, funnel, brand, messaging, copywriting
      - Marketing channel names: email, social, PPC, SEO, content marketing

  research:
    signals:
      - Terms: literature, sources, evidence, citations, study, paper, methodology
      - Academic language patterns
      - Bibliography or reference mentions

  creative:
    signals:
      - Design files: .fig, .sketch, .psd, .ai, .xd
      - Terms: design, visual, layout, color, typography, UX, wireframe, mockup, copy

  mixed:
    signals:
      - Signals from 2+ categories above present simultaneously
```

Artifact type selection:
1. If signals from 2+ types → `mixed`
2. If dominant signals clearly point to one type → that type
3. If `uacp_lifecycle` signals present → `uacp_lifecycle` (takes precedence over `code` when both present)
4. Default → `code` (most common)
