# 15 — Guardian/Heartgate Validator Wiring Design

Status: design-complete  
Depends on: `14-validator-hardening-and-fixtures.md`

## Decision

Keep `scripts/validate_uacp_artifacts.py` as a manual and CI-style drill helper now. Do **not** make it a hard Guardian/Heartgate dependency yet.

## Rationale

Guardian and Heartgate must fail closed from canonical docs/config/state, but the current validator is intentionally lightweight. If it becomes a runtime dependency too early, it could either:

- create false confidence by validating only a partial schema, or
- block valid future artifacts because the validator lags behind doctrine.

## Integration path

1. Current: manual validator invoked during VERIFY and council review.
2. Next: CI/preflight wrapper invokes validator for proposed UACP artifact changes.
3. Later: Heartgate calls a stabilized schema validator before phase transition acceptance.
4. Production: Guardian/Heartgate use a stricter schema package or JSON Schema-derived validator, with this script retained as a developer-friendly smoke tool.

## Exact future integration points

- Heartgate pre-transition: validate transition artifact, gate-selection artifact, council synthesis artifact, and required evidence clusters before allowing phase advance.
- Guardian pre-tool-call: require UACP context fields for protected actions; do not call this script synchronously for every tool call.
- Guardian post-tool-call: audit whether produced artifacts pass lightweight validation when the action claims to create UACP artifacts.
- Kanban control-plane guard: validate UACP context payload shape before dispatching UACP-bound workers.

## Fail-open / fail-closed behavior

- Runtime protected action classification: fail closed.
- Phase transition with missing required artifact: fail closed.
- Manual validator unavailable in developer drill: warn and require explicit reviewer acceptance, not silent pass.
- Schema evolution mismatch: block production Heartgate only after the stricter schema package exists; until then record as WARN/accepted risk.

## Bypass risk recording

Any state mutation or execution path that bypasses `uacp_state_write` or guarded dispatch must be recorded in verification as HIGH accepted risk or blocker. It must not be normalized as expected production behavior.
