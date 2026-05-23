# UACP Lifecycle Hardening Pattern — Session Reference

Use this reference when patching UACP's own lifecycle semantics, validators, or phase gates.

## Durable workflow lesson

For ordinary missing-package/validator gaps, implementation-first followed by council can be acceptable. For VERIFY or other truth/authority boundary work, use pre-design council before implementation.

Recommended sequence for governance-core phase gates:

1. Load relevant lifecycle skills.
2. Retrieval-led gap audit from repo ground truth and current skills.
3. Pre-design council when the phase is VERIFY, RESOLVE, Heartgate, Guardian, public/private boundary, or self-approval sensitive.
4. Patch docs/config/validator/fixtures/skills together.
5. Run deterministic validation.
6. Run post-implementation council and adversarial audit.
7. Patch findings and rerun focused follow-up.
8. Commit and push only when repo is clean, validator passes, and material audit findings are closed.

## Design principle

Do not create doctrine-only patches for UACP lifecycle behavior. A real UACP lifecycle patch should usually include:

- architecture/reference doc updates,
- config gate updates,
- validator/schema updates,
- positive and negative fixtures,
- lifecycle skill updates,
- council/audit artifact when risk warrants it.

## Granularity principle

Keep artifacts modular and class-level:

- ADR for the concept,
- config for selection/gates,
- validator functions for machine checks,
- fixture directory for regression protection,
- references/ files in skills for session-specific learnings.

## Pitfall

A lifecycle patch is incomplete if it only improves the current phase's prose. The next phase boundary must be checked too: EXECUTE needed VERIFY consumption; VERIFY needed RESOLVE readiness.
