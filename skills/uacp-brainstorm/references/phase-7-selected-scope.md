## Phase 7: Produce the Scope Package for TRIAGE

If `selected_scope.enter_uacp == true`, extract a concise scope package from the vault. This is the only artifact that crosses the brainstorm → TRIAGE boundary.

**Scope package path:** `.outputs/brainstorm/{session_id}/07-scope-package.yaml`

```yaml
kind: uacp.brainstorm_scope_package
session_id: "{session_id}"
run_id: ""  # populated by TRIAGE if admitted
timestamp: "{ISO-8601}"

source_vault: ".outputs/brainstorm/{session_id}/"

selected_scope:
  title: "..."
  description: "..."
  approach_id: "A1"
  in_scope:
    - "..."
  out_of_scope:
    - "..."

signals:
  artifact_type: code | docs | research | creative | mixed
  domains: []
  concerns: []
  constraints: []

estimated_governance:
  routing_advisory: direct | lightweight | standard_uacp | full_governance
  reasoning: "..."
  anticipated_phases:
    - triage
    - propose
    - plan
    - execute
    - verify
    - resolve

declared_side_effects:
  - "..."

authority:
  source: "User request via uacp-brainstorm"
  approved_by: []

human_involvement:
  required: true | false
  reason: ""

risks:
  - description: "..."
    severity: low | medium | high
```

If `selected_scope.enter_uacp == false`, skip this phase and stop.

### 7.1 Update manifest.yaml with selection

```yaml
selected_scope:
  title: "..."
  approach_id: "A1"
  enter_uacp: true | false
  rationale: "Why this scope was selected"
```

Also mark the selected approach in `approaches_sketched`:

```yaml
approaches_sketched:
  - id: "A1"
    selected: true
```

**Output of this phase:** `07-scope-package.yaml` ready for TRIAGE admission, and `manifest.yaml` updated with final selection.
