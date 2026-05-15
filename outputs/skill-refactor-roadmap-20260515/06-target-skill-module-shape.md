# Target Skill Module Shape

## Canonical structure

```text
uacp-<phase>/
  SKILL.md
  references/
  templates/
  schemas/
  scripts/
```

Not every skill needs every folder, but the Decision artifact must explain any omission.

## SKILL.md role

`SKILL.md` is the entrypoint/conductor. It should:

- say when the skill triggers
- state the phase purpose
- route to local support files
- define the minimal execution order
- name stop conditions
- avoid long embedded SOP detail

## references/ role

Local references hold detailed phase contracts, examples, reviewer prompts, routing logic, and operating rules.

## templates/ role

Templates hold copyable artifact skeletons: reports, transitions, findings, plans, residual-risk registers.

## schemas/ role

Schemas hold structured artifact validation rules where shape matters.

## scripts/ role

Scripts hold deterministic checks or helpers. They prevent relying solely on agent judgment.

## Shared references role

Shared references are only for primitive cross-phase vocabulary and contracts, not execution SOPs.
