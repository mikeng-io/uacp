# Trustless / OpenSpec Distillation

## OpenSpec — distill
- Separate artifacts by concern so humans and agents can review intent/design/tasks independently.
- Use artifact dependency graphs rather than giant prompts.
- Support quick vs expanded workflows based on clarity.

## OpenSpec — do not copy
- Do not require fixed `proposal.md`, `design.md`, `specs/`, `tasks.md` for UACP PLAN.
- Do not treat OpenSpec validation as UACP approval.
- Do not reduce UACP PLAN to implementation checkboxes.

## Trustless ACP — distill
- PLAN is proposal-driven.
- PLAN is control-plane-only.
- Preconditions and validation artifacts matter.
- State/artifact handoff must be explicit and crash-resistant.
- Guardian/preflight checks should be blocking where authority requires.

## Trustless ACP — do not copy
- Do not inherit Trustless-specific worktrees, state paths, project modules, or application-code rules as universal UACP requirements.
- Do not make Trustless ACP the authority for UACP.

## UACP synthesis
UACP PLAN packages should select modules by execution topology, authority surfaces, and verification difficulty.
