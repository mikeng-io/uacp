---
name: uacp-brainstorm
description: >
  Pre-TRIAGE exploration and scope-clarification skill. Helps the user understand
  what they actually want before UACP admission control. Writes rough notes,
  design sketches, and candidate scopes into an Obsidian-style vault under
  .uacp/brainstorm/. Only the trimmed selected scope transitions into TRIAGE.
location: managed
dependencies:
  - uacp-context
  - uacp-council-taxonomy
  - uacp-guardian
  - uacp-heartgate
  - domain-registry
  - bridge-commons
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(ls *)
  - Bash(git log *)
  - Bash(git diff *)
  - Task
  - Write
  - Bash(mkdir *)
---

# UACP Brainstorm: Pre-TRIAGE Exploration

Use this skill when the user has a vague idea, ambiguous scope, or multiple possible directions. Brainstorming happens **before** UACP admission control. Its job is to help the user understand what they actually want and trim it down to a bounded scope that can be handed to TRIAGE.

**This skill is informal.** It does not write formal UACP proposals, state records, or lifecycle artifacts. It writes rough notes to an Obsidian-style vault under `.uacp/brainstorm/`. Only the final selected scope transitions into TRIAGE.

**Hard rule:** do not invoke implementation skills during brainstorming. Exploration only.

---

## Skill-Level Exploration Gate

Read: references/exploration-gate.md

---

## Quick-Start

1. Read: references/phase-1-context.md — Gather signals and classify intent
2. Read: references/phase-2-explore.md — Explore possibilities and constraints
3. Read: references/phase-3-questions.md — Ask clarifying questions one at a time
4. Read: references/phase-4-approaches.md — Sketch 2–3 candidate approaches
5. Read: references/phase-5-trim.md — Trim scope with the user
6. Read: references/phase-6-vault.md — Write rough notes to Obsidian vault
7. Read: references/phase-7-selected-scope.md — Produce the scope package for TRIAGE
8. Read: references/phase-8-admission.md — Guardian + Heartgate check before entering TRIAGE
9. Read: references/phase-9-triage.md — Hand off to TRIAGE

---

## Lifecycle Position

```text
BRAINSTORM → TRIAGE → PROPOSE → PLAN → EXECUTE → VERIFY → RESOLVE
 ^
 informal Obsidian vault    ^
                            formal UACP state begins here
```

- Brainstorm outputs live in `.uacp/brainstorm/` (local notes).
- TRIAGE receives a **selected-scope package**, not the whole vault.
- If the user declines UACP governance, the vault remains as documentation and the process stops.

---

## Notes

- **One question at a time** — never overwhelm the user with bundled questions
- **YAGNI ruthlessly** — the goal is to trim scope, not expand it
- **Explore alternatives** — always sketch 2-3 approaches before settling
- **The vault is disposable** — it is raw thinking material, not canonical state
- **Only selected scope enters TRIAGE** — Guardian checks the admission boundary
- **Anti-collapse** — one phase = one markdown file. Never merge phases. Every search and file read must be recorded in `manifest.yaml` and `references/`. The vault is both human narrative (markdown) and machine-readable evidence (YAML).
