# Fail-Closed Containment Proof Pattern

Use this pattern when UACP work reaches the containment-hardening boundary and you need to prove that shell/code execution remains blocked until a real filesystem sandbox or readonly mount exists.

## What to verify

- `exec.shell` is blocked for UACP-bound actions when `filesystem_guard_verified` is false.
- `exec.code_with_tool_proxy` is blocked for UACP-bound actions when containment is unavailable.
- The block reason explicitly names containment, not just a generic policy refusal.
- Heartgate and canonical writer tools still pass their own positive/negative probes.

## Probe shape used in this session

- Run the live Guardian probe against a temporary isolated UACP root.
- Include positive checks for:
  - `uacp_doc_write`
  - `uacp_config_write`
  - `uacp_heartgate_check`
- Include negative checks for:
  - absolute path escape
  - `.` / `..` path traversal
  - root target
  - directory target
  - symlink escape
- Add explicit fail-closed checks for:
  - `exec.shell`
  - `exec.code_with_tool_proxy`

## Verification result shape

Record a verification artifact that states:

- probe status and check count
- the exact containment blocker surfaced by Guardian
- any remaining deferred item, usually full filesystem sandbox/readonly mount containment
- whether the current session was stale and required direct guarded-handler invocation for the artifact write

## Pitfall

Do not treat "blocked because containment is missing" as a bug once the goal is to keep UACP-bound execution fail-closed. The bug is the opposite: allowing execution before containment exists.
