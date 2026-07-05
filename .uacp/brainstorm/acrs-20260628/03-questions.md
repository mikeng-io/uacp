# Phase 3 — Clarifying questions (resolved with operator)

## Q1: Is YAML-alone enough for an agent/council to comprehend an artifact?
**Operator: no — "1000% not enough."** An agent cannot understand intent/risk/scope
from scalars + prose-field-presence. Comprehension needs the prose.

## Q2: What is the intended division of labor between the two surfaces?
**Operator's principle (locked):**
> "markdown does the content / semantic things; yaml does the relation / deterministic things."

This is the CMS core principle applied to the artifact layer:
- **Markdown = semantic surface** → the `comprehend` input (agent + council read it)
- **YAML = relations surface** → the `measure` substrate (the gate computes on it)

## Q3: Scope of change — was blast radius measured before committing?
Yes (operator asked for it first). Measured: 2 load-bearing engine files
(projection.py, schema.py) + 3 peripheral refs + 2 schema/validator files + ~6
lifecycle skills + 18 test files + on-disk run migration. Precedent exists
(`uacp.intent`, `evidence_disposition` are already MARKDOWN kinds).

## Open question carried into the design (must resolve EARLY)
Do `heartgate.py` / `adaptive_gates.py` read scope **content** or only **structure**?
If structure-only, they are untouched and the radius shrinks. This gates the
additive-vs-cutover sizing and must be answered before PLAN.
