# Phase 6: Determine Routing

Apply routing decision rules. Routing is **advisory** — the final decision belongs to `uacp-triage` or the user.

```yaml
routing_rules:
  direct:
    conditions:
      - artifact_type in [code, creative, marketing]
      - domains_count < 3
      - no high-stakes signals
      - no uacp_governance signals
      - no explicit "thorough" or "critical"
    description: "Lightweight handling, possibly outside UACP lifecycle"

  lightweight:
    conditions:
      - domains_count <= 5
      - no uacp_governance_core signals
      - no irreversible/high-stakes signals
    description: "UACP admission with lightweight governance"

  standard_uacp:
    conditions_any:
      - uacp_lifecycle artifact type
      - domains_count > 5
      - explicit council or review request
      - standard complexity implementation
    description: "Full UACP lifecycle with standard governance"

  full_governance:
    conditions_any:
      - uacp_governance_core signals
      - high-stakes signals: [production, incident, breach, compliance, audit, lawsuit, financial risk, irreversible]
      - explicit "thorough" or "critical"
      - granularity estimate >= 7
    description: "Maximum governance, council review likely required"

  block_or_clarify:
    conditions:
      - intent is unclear after signal extraction
      - no artifact identified
      - authority is ambiguous AND uacp_governance_core signals present
    description: "Stop and request clarification before proceeding"
```

**Council recommendation:**

```yaml
council_recommendation:
  recommended: true | false
  tier: 0 | 1 | 2 | 3
  mode: review | audit | brainstorm | design | research | synthesis
  reason: ""
```

Suggest council when:
- `full_governance` routing
- Granularity >= 7
- Governance-core work
- User explicitly requests multi-perspective review
- Confidence is medium or low
