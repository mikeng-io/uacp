# Risks and Verification

## Risks
- PLAN/EXECUTE boundary collapse.
- OpenSpec clone regression.
- Trustless-specific leakage.
- YAML-only regression under new names.
- Proposal text overclaims enforcement that has not yet been implemented.
- Validator checks package-selection but Heartgate/live Guardian do not.
- Runtime plugin cache hides source changes until reload.

## Required verification
- Validator positive fixture passes.
- Validator negative fixture blocks.
- Current run plan-selection passes once PLAN package exists.
- Heartgate valid PLAN→EXECUTE dry-run passes/warns.
- Heartgate missing-package and YAML-only dry-runs block.
- Guardian policy recognizes adaptive PLAN package paths.
- Council audits actual artifacts and diffs.

## Council gates
PROPOSE council before PLAN. PLAN/pre-EXECUTE council before implementation. VERIFY council after patches.
