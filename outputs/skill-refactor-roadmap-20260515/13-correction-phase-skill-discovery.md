# Correction — Phase Means One Skill, Not Predefined Structure

## Source correction

Mike clarified that the roadmap was still too eager to predefine the future directory/file shape for each skill.

The correct interpretation is:

```text
Each phase of this refactor targets one skill.
For that skill, do not assume the final directory/file structure upfront.
First explore the skill's original intent, concept, variants, and possible compositions.
Then determine what structure is actually needed.
```

## Problem with the previous roadmap language

The previous roadmap included candidate trees such as:

```text
uacp-plan/
  SKILL.md
  references/
  templates/
  schemas/
  scripts/
```

This was useful as a possible modular pattern, but it was too close to premature design. It risks making the refactor mechanical instead of understanding-driven.

Mike's questions that must guide each skill:

1. Is that many files really needed?
2. Is the original intent satisfied by those files?
3. What is the underlying concept of the skill?
4. Has the design space been brainstormed enough?
5. Should Agent Council help brainstorm, then justify, normalize, and serialize the result?

## Corrected operating rule

For every skill, the loop remains:

```text
Explore → Determine → Decision → Review → Audit → Implement
```

But the meaning is sharpened:

- **Explore**: understand current files, historical intent, conceptual role, and existing failure modes.
- **Determine**: brainstorm possible module shapes and variants; do not select yet.
- **Decision**: choose the smallest sufficient structure and justify why.
- **Review**: use human review and/or Agent Council to challenge whether the chosen structure fits the intent.
- **Audit**: convert the decision into measurable checks.
- **Implement**: write only the decided files.

## Agent Council role

Agent Council is not mandatory for every tiny change, but it should be considered when a skill's concept is ambiguous, governance-critical, or likely to benefit from adversarial brainstorming.

Recommended council use for each skill:

```text
Brainstorm → challenge variants → justify selected structure → normalize vocabulary → serialize into files/templates/schemas only after decision
```

Council output should not become authority by itself. It is input to the Decision/Review phase.

## Consequence

Any previously listed file tree is now treated as a candidate pattern, not a target. The final file set for each skill must be discovered and justified inside that skill's own Explore/Determine/Decision chain.
