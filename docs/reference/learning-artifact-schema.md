# Learning Artifact Schema

Preserved from `config/memory-policy.yaml` (Slice 3 config-collapse). Operational
storage boundaries moved to `config/uacp.toml [memory]`. This document is the
canonical reference for the learning artifact schema and example.

## Schema

```yaml
learning_artifact_schema:
  kind: uacp.learning_artifact
  required_fields:
    - scenario_id
    - created_at
    - domains
    - artifact_types
    - risk_level
    - selected_clusters
    - not_applicable
    - outcome
    - ranking_signals
    - lessons
    - storage_policy
  fields:
    scenario_id: string
    created_at: string
    domains:
      type: list
      item_type: string
    artifact_types:
      type: list
      item_type: string
    risk_level:
      type: enum
      values: [low, medium, high, critical]
    selected_clusters:
      type: list
      item_type: string
    not_applicable:
      type: list
      item_type: map
      fields:
        cluster_id: string
        reason: string
    outcome:
      type: map
      fields:
        transition_result: "pass|warn|block"
        verification_result: "pass|warn|block|not_applicable"
        incidents_or_rework: string
    ranking_signals:
      type: map
      fields:
        useful_clusters: list
        unnecessary_clusters: list
        missing_clusters: list
        notes: list
    lessons:
      type: list
      item_type: string
    storage_policy:
      type: map
      fields:
        local_artifact_path: string
        honcho_memory: "never|summary_only|operator_preference_only"
        knowledge_bank_ingest: "pending|sent|not_applicable"
```

## Example Artifact

```yaml
example_artifact:
  kind: uacp.learning_artifact
  scenario_id: uacp-run-2026-05-10-001
  created_at: "2026-05-10T00:00:00+08:00"
  domains: [governance, hermes-agent]
  artifact_types: [config, docs, directory_structure]
  risk_level: medium
  selected_clusters:
    - scope
    - context
    - authority
    - write_containment
    - memory_lessons
  not_applicable:
    - cluster_id: runtime_validation
      reason: "No runtime service changed."
    - cluster_id: marketing_brand_fit
      reason: "No marketing asset changed."
  outcome:
    transition_result: pass
    verification_result: pass
    incidents_or_rework: none
  ranking_signals:
    useful_clusters:
      - write_containment
      - memory_lessons
    unnecessary_clusters: []
    missing_clusters: []
    notes:
      - "For UACP bootstrap docs, containment and schema clarity matter more than software runtime checks."
  lessons:
    - "Bootstrap stages should keep Knowledge Bank artifacts local before service extraction."
  storage_policy:
    local_artifact_path: "knowledge/scenarios/uacp-run-2026-05-10-001.yaml"
    honcho_memory: summary_only
    knowledge_bank_ingest: pending
```
