# Adaptive Proposal Documentation Lifecycle

Use this note when UACP PROPOSE itself is being repaired, or when a proposal is serious enough that YAML lifecycle records are not sufficient.

## Core lesson

UACP documentation selection is adaptive and context-driven:

```text
granularity scales rigor;
context/work-heart selects documents;
package-selection.yaml bridges human docs to machine enforcement.
```

Do not map granularity directly to a fixed document checklist. Two high-granularity runs may need different artifacts because their risks, authority surfaces, and verification hearts differ.

## Proposal package shape

For serious PROPOSE work, create both:

- human-readable Markdown surfaces for reasoning/review;
- machine-readable YAML surfaces for validator/Heartgate/Guardian enforcement.

Recommended topology:

```text
proposals/<run_id>/
  00-index.md
  proposal.md
  authority-scope-containment.md
  doctrine-delta.md              # when doctrine changes
  adaptive-documentation-model.md # when documentation model changes
  package-selection-schema.md     # when package-selection semantics change
  enforcement-surfaces.md         # when skill/config/validator/Heartgate/Guardian wiring is affected
  risks-and-verification.md
  decision-journal.md
  artifacts.md
  machine/
    package-selection.yaml

proposals/<run_id>-proposal.yaml
proposals/<run_id>-gate-selection.yaml
proposals/<run_id>-package-selection.yaml
```

Top-level YAML may exist for validator compatibility. `artifacts.md` must identify the source of truth and prevent package-local/top-level drift.

## `package-selection.yaml` contract

The bridge artifact should declare:

- `work_heart.primary` and secondary concerns;
- universal core coverage: `intent`, `authority`, `scope`, `containment`, `risk`, `verification`, `transition`, `artifact_map`;
- selected domain modules with `reason`, `artifact`, and `required_for_plan`;
- not-applicable modules with `reason`, `accepted_by`, `owner`, `residual_risk`, and `revisit_phase`;
- `plan_readiness.status`.

Weak blanket omission is invalid. `not_applicable` means evaluated, owned, and assigned a revisit point.

## Lifecycle for patching UACP PROPOSE itself

Use UACP rhythm without recursive paralysis:

1. **TRIAGE** — classify as governance-core/lifecycle semantics patch; freeze any downstream proving-case (e.g. LEXA) as evidence only.
2. **PROPOSE** — create adaptive proposal package and package-selection bridge.
3. **Council** — review selected docs, omissions, phase boundaries, and enforcement surfaces.
4. **PLAN** — convert accepted proposal into patch tranches.
5. **EXECUTE** — apply bounded patches.
6. **VERIFY** — run fixtures, validator checks, Heartgate dry-run/council.
7. **RESOLVE** — archive lessons and only then unblock proving-case regeneration.

## Council pitfall

If council returns CONCERNS only because the package still says `blocked_until_council_pass`, do not loop forever. Patch remediations, record follow-up council, then update package readiness to `ready_for_plan_with_conditions` when remaining enforcement work is properly owned by PLAN.

## Enforcement pitfall

Skill prose is not enough. PLAN must include explicit tranches for:

- `config/phase-transitions.yaml` package-readiness gate;
- `scripts/validate_uacp_artifacts.py` package-selection validation;
- Heartgate transition-readiness expectation;
- Guardian artifact containment clarification;
- pass/block fixtures.
