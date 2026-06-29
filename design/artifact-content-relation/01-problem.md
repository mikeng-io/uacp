---
type: analysis
title: "The Problem — as-built split and boundary violation"
description: "Grounds the content/relation misalignment in code: why the gate measures only YAML while the review surface is split across YAML and Markdown, and the consequence of that boundary violation."
tags: [artifact, content-relation, gate, field_present, analysis, grounded]
timestamp: 2026-06-30
edges: []
---
# 01 — The problem (as-built, grounded)

## The gate never opens the Markdown
Every generative-gate check binds to a **YAML field path**. Concretely
(`hnp-20260628-check-1-field_present.yaml`):
```yaml
bind:
  ref:
    artifact: proposals/hnp-20260628-proposal.yaml   # YAML
    field: scope.in_scope[0]                          # a YAML field path
```
And `projection.py:141-145` builds the `scope_item` graph nodes from
`proposal.yaml → scope.in_scope[]`. The Markdown package contributes **zero graph nodes
and zero check targets**. The gate computes entirely on YAML.

## Substance is split three ways, not two
| Category | Lives in | Read by | Examples |
|---|---|---|---|
| 1. Machine spine | YAML only | validator, Heartgate, projection, replay | proposal_id, phase, granularity, check.bind, ledger, watermarks |
| 2. **Duplicated** | **both YAML + MD** | gate reads YAML half; council reads MD half | objective, scope.in_scope, authority{}, declared_side_effects |
| 3. Council substance | MD only | humans + council only | risk (R1/R2/R3), containment, verification plan, transition reasoning, artifact map |

## The violation, in one sentence
The surface council **reviews** (cat 2-MD + cat 3) and the surface the gate **measures**
(cat 1 + cat 2-YAML) barely overlap. So:
- **Duplication (cat 2)** → two copies drift; nothing reconciles them.
- **Gate-invisibility (cat 3)** → council's main material is unmeasured; a finding fixed
  (or not) in Markdown is seen by no check, lens, or replay.
- **Weak proxy** → `field_present` proving a YAML prose field is non-empty proves nothing
  about whether the intent is *real*. That is exactly the proxy the CMS principle forbids
  ("a grep standing in for 'the feature works' is not a measurement"). Semantic adequacy is
  a *semantic* judgment → it belongs to council, not a presence check.

## Consequence for the agent (the symptom that surfaced this)
After council there is no coherent "update" contract: cat 2 must be hand-synced across two
surfaces, cat 3 edits are ungated. The agent has no single home to edit and no gate that
confirms the edit landed.
