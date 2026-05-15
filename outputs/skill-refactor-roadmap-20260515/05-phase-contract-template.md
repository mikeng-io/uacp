# Phase Contract Template

Each skill refactor must produce the following before implementation.

## Explore artifact

Must answer:

- What files currently exist?
- What does SKILL.md currently claim?
- What does the skill actually need to do?
- What global references does it rely on?
- What details are missing or misplaced?
- Which remembered/session facts are relevant?

## Determine artifact

Must classify:

- keep in SKILL.md
- move to local `references/`
- move to local `templates/`
- move to local `schemas/`
- move to local `scripts/`
- defer
- reject

## Decision artifact

Must define:

- final file tree for this skill
- exact responsibility of `SKILL.md`
- exact responsibility of each support file
- allowed tools and forbidden tools
- entry condition
- output condition
- stop conditions
- review expectations

## Review artifact

Must answer:

- Does this avoid mega-SOP centralization?
- Can a fresh agent use the skill without global junk?
- Does it preserve UACP semantics?
- Is the scope narrow enough?

## Audit artifact

Must include pass/fail checks:

- SKILL.md has frontmatter
- SKILL.md is concise conductor
- local references exist
- templates/schemas/scripts exist where decided
- no unapproved cross-skill edits
- no hidden dependency on current broken UACP state

## Implement artifact

Must record:

- changed files
- verification commands
- review outcome
- remaining risks
