# Verification Strategy

## Deterministic checks
- Validate top-level proposal package selection: PASS.
- Validate PLAN package selection after creation: PASS.
- Validate positive adaptive-plan fixture: PASS.
- Validate negative adaptive-plan fixture: BLOCK.
- Local Heartgate PLAN→EXECUTE valid dry-run: pass/warn.
- Local Heartgate missing package dry-run: block.
- Local Heartgate YAML-only dry-run: block.
- AST parse `validate_uacp_artifacts.py` and `kernel.py` with `PYTHONDONTWRITEBYTECODE=1`.

## Council checks
After EXECUTE, run focused council against actual diffs and evidence.

## Reporting split
Report separately:
- validator behavior,
- Heartgate source behavior,
- Heartgate live-runtime/reload status,
- Guardian policy recognition,
- Guardian hard-interception proof or caveat.
