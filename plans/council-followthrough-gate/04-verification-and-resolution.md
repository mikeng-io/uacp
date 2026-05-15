# Verification and Resolution Plan — Council Follow-Through Gate

Run: `council-followthrough-gate-20260514-201718`
Phase: PLAN

## PLAN verification before EXECUTE

- PLAN package exists and is internally consistent.
- Surface inventory marks each relevant surface as patch/defer/out_of_scope.
- PLAN council synthesis exists.
- PLAN council concerns are patched or carried as owned warnings/deferred items.
- UACP artifact validator passes on plan/council/transition artifacts.
- PLAN→EXECUTE Heartgate check passes or passes with accepted warnings.

## EXECUTE verification after canonical patches

### Static checks

- YAML parse for all changed config/artifacts.
- Markdown target sections exist and include the new rule without contradictory language.
- `scripts/validate_uacp_artifacts.py` runs successfully on known-good artifacts.

### Synthetic negative/regression checks

Create temporary or verification-only transition artifacts proving:

1. **Positive path:** handled material finding with required follow-up council + Heartgate-visible chain passes or warns with accepted warnings.
2. **Missing follow-up path:** material remediated/expanded/justified finding without required follow-up council blocks.
3. **Deferred ownership path:** deferred/accepted_warning/rejected finding without owner/residual risk/next-phase obligation blocks.
4. **Invariant vocabulary path:** non-waivable invariant represented as `warn` or `deferred` blocks.
5. **TRIAGE sequencing path:** high-granularity governance-core TRIAGE without required council/Heartgate evidence is at least warned/blocked according to the implemented policy.

### Council checks

- EXECUTE council reviews actual patches against the PLAN surface inventory.
- VERIFY council reviews evidence artifacts and confirms no lifecycle compression remains.

## Resolution criteria

- Canonical docs/config and validator/skills agree.
- Heartgate passes EXECUTE→VERIFY and VERIFY→RESOLVE transitions.
- Accepted warnings/deferred items are explicit and owned.
- No hidden state mutation or out-of-band canonical mutation remains unrecorded.

## Memory/skill decisions

- If the implementation discovers a reusable pattern for TRIAGE council correction or follow-through gate testing, update the relevant UACP skill immediately.
- Do not save transient artifact IDs to long-term memory.
