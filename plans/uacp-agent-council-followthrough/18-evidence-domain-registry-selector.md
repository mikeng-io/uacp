# 18 — Evidence-Domain Registry Selector Design

Status: design-complete; not runtime-active

## Decision

The Evidence-Domain Registry remains `implementation_status: not_runtime_active` until a selector exists and is verified. This document defines the selector design only.

## Selector inputs

- phase
- artifact types
- domains
- risk level
- authority and side effects
- reversibility
- runtime context
- council mode/tier
- phase-local granularity
- unresolved findings or warnings

## Selector output

```yaml
selected_domains: []
selected_cluster_families: []
suggested_council_roles: []
verification_requirements: []
escalation_triggers: []
not_applicable_clusters: []
reasoning: []
```

## Domain examples

### Software
Clusters: `architecture_design`, `execution_strategy`, `verification_strategy`, `risk`.  
Roles: `implementation_reviewer`, `verification_reviewer`, `devils_advocate`.

### Governance
Clusters: `authority`, `side_effects`, `traceable_state`, `risk`, `verification_strategy`.  
Roles: `integrator_critic`, `operator_proxy`, `devils_advocate`.

### Research
Clusters: `grounding`, `context`, `verification_strategy`.  
Roles: `domain_expert`, `verification_reviewer`, `integrator_critic`.

### Infra
Clusters: `risk`, `write_containment`, `privacy_safety`, `verification_strategy`.  
Roles: `operator_proxy`, `verification_reviewer`, `devils_advocate`.

## Runtime activation criteria

The selector can become runtime-active only when:

1. Config schema is stable.
2. At least four domain fixtures pass: software, governance, research, infra.
3. Heartgate can consume selector output in a transition dry run.
4. VERIFY confirms no artifact claims active implementation before proof exists.

## Current verification requirement

Any verification artifact in this phase must state: Evidence-Domain Registry is design-only and not runtime-active.
