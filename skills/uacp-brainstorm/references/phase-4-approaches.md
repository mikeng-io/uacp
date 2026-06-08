## Phase 4: Sketch Candidate Approaches

Produce 2–3 candidate approaches. These are sketches, not final designs.

For each approach provide:

```yaml
approach:
  id: "A1" | "A2" | "A3"
  title: "Short name"
  description: "One-paragraph sketch"
  scope_guess: "What this probably includes"
  complexity: low | medium | high
  risk: low | medium | high
  key_tradeoffs:
    pros: []
    cons: []
  likely_phases_if_uacp:
    - triage
    - propose
    - plan
    - execute
    - verify
    - resolve
```

### 4.1 Record in manifest.yaml

After sketching, update `manifest.yaml`:

```yaml
approaches_sketched:
  - id: "A1"
    title: "Minimal fix"
    complexity: low
    risk: low
    selected: false
  - id: "A2"
    title: "Medium refactor"
    complexity: medium
    risk: medium
    selected: false
  - id: "A3"
    title: "Full redesign"
    complexity: high
    risk: high
    selected: false
```

Present them conversationally. The user does not need to pick one yet — Phase 5 is about trimming together.

**Output of this phase:** 2–3 approach sketches in conversation, plus `manifest.yaml` updated.
