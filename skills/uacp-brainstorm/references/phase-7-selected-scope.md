## Phase 7: Produce the Scope Package for TRIAGE

If `selected_scope.enter_uacp == true`, extract a concise scope package from the vault. This is the only artifact that crosses the brainstorm → TRIAGE boundary.

**Scope package path:** `.uacp/brainstorm/{run_id}/07-scope-package.yaml` — written via `uacp_entity_write` (kind `uacp.brainstorm_scope_package`); the writer computes this run-keyed path and injects `run_id` into the document, so you supply `kind` + `fields` + `uacp_run_id`, not the path.

```yaml
kind: uacp.brainstorm_scope_package
# run_id is injected by the entity-writer (do not hand-author it).
timestamp: "{ISO-8601}"
source_vault: ".uacp/brainstorm/{run_id}/"

# Admission-contract fields are FLAT at the root — this is the written artifact's shape, which the
# entity-writer schema validates. (The vault manifest's `selected_scope` in §7.1 below is SEPARATE
# working state, not this package; don't confuse the two.)
title: "..."
description: "..."
in_scope:
  - "..."
declared_side_effects:
  - "..."
authority:
  source: "User request via uacp-brainstorm"
  approved_by: []
routing_advisory: direct | lightweight | standard | full_governance

# Optional richer context (open-world; NOT part of the required admission contract):
approach_id: "A1"
out_of_scope:
  - "..."
signals:
  artifact_type: code | docs | research | creative | mixed
  domains: []
  concerns: []
  constraints: []
governance_reasoning: "..."
anticipated_phases: [triage, propose, plan, execute, verify, resolve]
human_involvement:
  required: true | false
  reason: ""
risks:
  - description: "..."
    severity: low | medium | high
```

If `selected_scope.enter_uacp == false`, skip this phase and stop. Stopping is itself a recorded decision, not a silent exit — close the brainstorm run via the `aborted`-status path (the vault remains as recorded evidence). Do not leave the run silently parked at `phase: brainstorm`.

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
