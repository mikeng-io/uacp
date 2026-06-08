## Step 8: Save Artifact

Write to `.outputs/council/{YYYYMMDD-HHMMSS}-tier{N}-{session_id}.md` with frontmatter:

```yaml
---
skill: uacp-council
tier: 0 | 1 | 2 | 3
ic_tier: 0 | 1 | 2 | 3                  # null outside finding-driven; equals tier unless IC-hoist ran
session_id: "{session_id}"
timestamp: "{ISO-8601}"
mode: review | audit | brainstorm | design | research | synthesis | finding-driven
task_type: ""
verdict: PASS | FAIL | CONCERNS | null
domains: []
diversity_sources: []
runtimes_used: []        # populated for tier >= 2
models_used: []          # populated when model diversity is active
debate_rounds: 0
tier_history: []         # if escalation occurred
prior_session_id: ""     # populated when mode == finding-driven and a prior council artifact was passed in
context_summary: ""
---
```

Also save JSON companion: `{YYYYMMDD-HHMMSS}-tier{N}-{session_id}.json` with the full report.

### Council report schema

```json
{
  "type": "uacp-council",
  "tier": 0,
  "ic_tier": null,
  "session_id": "...",
  "mode": "review",
  "task_type": "review",
  "verdict": "PASS",
  "intensity": "standard",
  "domains_covered": [],
  "diversity_sources": [],
  "runtimes_used": [],
  "models_used": [],
  "debate_rounds": 0,
  "tier_history": [],
  "outputs": [],
  "withdrawn_outputs": [],
  "disputed_outputs": [],
  "shared_bias_warnings": [],
  "auto_skipped_halted_runtimes": [],
  "partial_coverage": false,
  "context_summary": "...",
  "confidence": "high | medium | low",

  "prior_session_id": null,
  "input_findings_count": null
}
```

**For brainstorm/design/research modes:** replace `outputs` with `proposals` or `observations` arrays as defined in `bridge-commons`.

**For finding-driven mode:** the four finding-driven output types (`resolution`, `regression-finding`, `design-drift-finding`, `cross-domain-impact`, `fix-interaction-finding`) live in the standard `outputs[]` array, filterable by `type` — they do NOT get their own top-level arrays (the schema previously listed `regression_findings` / `design_drift_findings` / `fix_interaction_findings` as parallel arrays; this duplicated `outputs[]` semantics and has been removed). Consumers should filter `outputs[]` by `type` when they need a specific category. Resolution items additionally carry `resolution_status` and `target_finding_id` fields — see `bridge-commons` "Finding-driven-mode types".

`ic_tier` is non-null whenever finding-driven mode runs; it equals `tier` unless Step 6.IC (IC-hoist) elevated it. `prior_session_id` is populated when a prior council artifact was passed in as the `findings` source.