# Example Usage Scenarios

## Scenario 1: Codebase Exploration with Dependencies

```yaml
tasks:
  # Wave 1: Independent base analysis
  - id: structure
    description: "Analyze directory structure"
    prompt: "Map out directory structure and file organization"
    depends_on: []

  # Wave 2: Depends on structure
  - id: tech-stack
    description: "Identify technologies"
    prompt: "Identify technologies, frameworks, and languages used"
    depends_on: [structure]

  - id: dependencies
    description: "Map dependencies"
    prompt: "Analyze package dependencies and imports"
    depends_on: [structure]

  # Wave 3: Depends on both structure and tech
  - id: architecture
    description: "Analyze architecture patterns"
    prompt: "Identify architectural patterns and design decisions"
    depends_on: [structure, tech-stack]

  - id: workflows
    description: "Trace workflows"
    prompt: "Trace request flows and data processing pipelines"
    depends_on: [structure, dependencies]

  # Wave 4: Final synthesis
  - id: synthesis
    description: "Synthesize findings"
    prompt: "Combine all findings into comprehensive report"
    depends_on: [architecture, workflows]
```

**Execution plan:**
```
Wave 1: [structure]                          (1 task)
Wave 2: [tech-stack, dependencies]           (2 tasks in parallel)
Wave 3: [architecture, workflows]            (2 tasks in parallel)
Wave 4: [synthesis]                          (1 task)
```

## Scenario 2: Multi-Stage Verification

```yaml
tasks:
  # Wave 1: Domain analysis
  - id: security-analysis
    prompt: "Analyze security aspects"
    depends_on: []

  - id: performance-analysis
    prompt: "Analyze performance aspects"
    depends_on: []

  # Wave 2: Integration analysis (needs domain findings)
  - id: integration-check
    prompt: "Check integration impact using domain findings"
    depends_on: [security-analysis, performance-analysis]

  - id: devils-advocate
    prompt: "Challenge assumptions from domain analysis"
    depends_on: [security-analysis, performance-analysis]

  # Wave 3: Final review (needs everything)
  - id: third-party-review
    prompt: "Fresh eyes review of all analysis"
    depends_on: [integration-check, devils-advocate]
```
