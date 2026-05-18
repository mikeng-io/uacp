# Artifacts Map

## Core rule

The proposal is **not** composed into a single YAML file.

The proposal is the human-reviewable package directory:

```text
proposals/uacp-adaptive-propose-docs-20260518/
```

The top-level YAML files are machine lifecycle envelopes/exports for current validator and Heartgate compatibility.

## Human-readable package

- `00-index.md` — conductor and reading order
- `proposal.md` — why/what/impact
- `authority-scope-containment.md` — authority, scope, containment
- `doctrine-delta.md` — doctrine change
- `adaptive-documentation-model.md` — adaptive documentation selection
- `package-selection-schema.md` — package-selection bridge contract
- `enforcement-surfaces.md` — skill/config/validator/Heartgate/Guardian wiring targets
- `risks-and-verification.md` — risk and verification cases
- `decision-journal.md` — operator corrections/rationale

## Machine package artifacts

- `machine/package-selection.yaml` — package-local mirror of adaptive package selection evidence

## Top-level validator compatibility artifacts

- `../uacp-adaptive-propose-docs-20260518-triage.yaml` — lifecycle triage record
- `../uacp-adaptive-propose-docs-20260518-proposal.yaml` — machine proposal envelope, not the full proposal
- `../uacp-adaptive-propose-docs-20260518-gate-selection.yaml` — gate selection record
- `../uacp-adaptive-propose-docs-20260518-package-selection.yaml` — canonical machine bridge between docs and gates

## Drift control

Top-level YAMLs exist for current validator/Heartgate compatibility. Package-local and top-level package-selection YAML must remain byte-equivalent or semantically equivalent with explicit export note.

Current intended source of truth for package selection:

```text
proposals/uacp-adaptive-propose-docs-20260518-package-selection.yaml
```

Package-local mirror:

```text
proposals/uacp-adaptive-propose-docs-20260518/machine/package-selection.yaml
```

Before PLAN/EXECUTE gates, verify both copies match or regenerate the mirror from the top-level export. Do not let two machine records drift silently.
