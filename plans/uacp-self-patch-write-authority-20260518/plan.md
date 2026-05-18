# Self-Patch Write Authority Plan

## Work packages

1. Patch Heartgate `_validate_scope_artifact` to recognize `self_patch_write_authority` for otherwise-unreachable UACP self-repair paths.
2. Add helper `_self_patch_authorizes_path` with strict required fields and path prefixes.
3. Patch the adaptive PLAN scope artifact to include explicit self-patch authority for skill/script/runtime-adapter paths.
4. Run AST parse and Heartgate check on the adaptive PLAN transition.
5. Record execution and verification evidence.

## Safety rules

- Do not add terminal/patch to tool path capabilities.
- Only paths under `skills/devops/uacp/`, `scripts/`, and `runtime-adapters/` may be covered.
- Config/docs/artifacts must still use existing governed writers.
- Authority block must include owner, authority artifact, rollback path, and verification obligations.
