# Measurement and Audit

## Structural measurements

For each skill, measure before and after:

- number of files in skill directory
- SKILL.md line count
- number of local references
- number of templates
- number of schemas
- number of scripts
- references to global `../references`

## Quality measurements

Check whether a fresh agent can answer:

- What phase is this?
- What are the inputs?
- What are the outputs?
- What should it read?
- What should it write?
- When should it stop?
- What requires review?
- What can be validated deterministically?

## Context hygiene measurements

- Does the skill load only local support files by default?
- Are historical/session notes archived and not default-loaded?
- Are shared references primitive-level only?
- Is SKILL.md concise enough to avoid context bloat?

## Pass/fail rule

A skill fails if its correct use requires reconstructing behavior from a large shared document pile.
