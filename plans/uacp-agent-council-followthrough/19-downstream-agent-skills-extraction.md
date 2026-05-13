# 19 — Downstream Agent-Skills Extraction Plan

Status: design-complete; extraction deferred

## Decision

Do not extract downstream `agent-skills` doctrine until UACP stabilizes. UACP remains canonical; downstream skills are implementation views.

## Mapping

- UACP lifecycle docs/config -> lifecycle skills and validators.
- `docs/orchestration-model.md` -> Agent Council / bridge / deep-* compatibility skills.
- `config/review-routing.yaml` -> review/council routing helpers.
- `config/evidence-clusters.yaml` -> evidence-domain registry and domain templates.
- `docs/runtime-enforcement.md` + `config/guardian-policy.yaml` -> Guardian/Heartgate adapter skills.

## Deprecated / compatibility-only wrappers

The `deep-*` family should be compatibility wrappers when UACP phases already cover the role:

- `deep-review` -> Agent Council `review` or `verify` mode.
- `deep-audit` -> Agent Council `audit` mode.
- `deep-research` -> Agent Council `research` mode.
- `deep-verify` -> UACP VERIFY plus selected evidence clusters.
- `deep-council` -> higher council tier, not separate doctrine.

## Drift checks

Before extraction:

1. Read UACP canonical docs/config first.
2. Confirm generated skills do not redefine UACP phase semantics.
3. Confirm Guardian/Heartgate status is not overstated.
4. Confirm Evidence-Domain Registry remains design-only until selector proof.
5. Confirm downstream wrappers use canonical finding states.
6. Run validator on UACP artifacts before publishing downstream skill changes.

## Recommended extraction order

1. Stabilize current UACP follow-through artifacts.
2. Run final Agent Council and resolve findings.
3. Create a dedicated extraction proposal.
4. Generate skills from UACP doctrine.
5. Validate against drift checklist.
6. Only then update downstream `agent-skills` branch/repo.
