# Current Failure Analysis

## Observed structural failure

Current UACP skill layer under `/home/norty/.hermes/skills/devops/uacp` is dominated by global references and thin phase skills.

Observed earlier:

- `uacp-triage/`: 1 file
- `uacp-propose/`: 1 file
- `uacp-plan/`: 1 file
- `uacp-execute/`: 1 file
- `uacp-verify/`: several local references, closer but still not complete
- `uacp-resolve/`: minimal local references
- `uacp-state/`: some references, not full module
- shared `references/`: large flat pile of session notes, patterns, and quasi-SOPs

## Why this is broken

1. **Thin wrappers** — phase skills point outward instead of owning executable phase behavior.
2. **Shared-reference junk drawer** — too much content is accumulated in one global location.
3. **False coverage** — because something is documented somewhere, the system behaves as if the phase is covered.
4. **Context bloat** — loading shared references burns tokens and hides relevant detail.
5. **Poor recall** — future agents cannot know which detail matters for which phase.
6. **Self-hosting error** — using broken UACP to govern UACP repair creates circular validation.

## Ground truth from Trustless and Anthropic skills

Trustless ACP and Anthropic's official skills repo both show that serious skills are modular directories:

- `SKILL.md` is the conductor/entrypoint.
- supporting references are local to the skill.
- scripts/schemas/templates carry deterministic or structured behavior.
- shared material is small and primitive-level.

## Correction

Rebuild each UACP lifecycle skill as a modular skill package, one at a time.
