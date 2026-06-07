---
kind: uacp.proposal_package.index
run_id: lexa-executable-contract-bootstrap-20260521
phase: PROPOSE
status: draft
---

# LEXA Executable Contract Bootstrap — Proposal Package

## Conclusion

This proposal selects an integrated UACP lifecycle for a minimal LEXA bootstrap/init.

It is not documentation-first and not runtime-first. It is a governed convergence loop where docs, schemas, fixtures, validator code, and a bounded reference packet builder co-evolve until VERIFY can say what is actually proven.

## Intent

LEXA currently exists as a reviewed Vault draft packet. That is useful, but insufficient: docs without executable pressure tests risk architecture theatre, while uncontrolled code-first implementation risks turning unresolved governance assumptions into accidental runtime truth.

The intent of this lifecycle is to create a small executable contract surface that tests the draft architecture without deploying or integrating LEXA.

## Scope

In scope:

- governed staging/project surface for LEXA bootstrap;
- architecture docs imported as draft input;
- JSON/YAML schemas for source registry, context packet, event, entity, relation, and common enums;
- valid fixtures for Nora public-safe and Cortex editorial packets;
- invalid fixtures for leakage, missing provenance, cross-workspace denial, advisory draft treated as canonical, and implied source mutation;
- local validator;
- bounded mock-source reference packet builder if PLAN selects it;
- doc patches based on executable findings.

Out of scope:

- daemon;
- API service;
- live Nora integration;
- live Cortex integration;
- private memory ingestion;
- shared private-memory index;
- standalone SEF/SGRN services;
- production source registry state;
- push/external publication without explicit operator authorization.

## Containment

Initial staging target:

```text
/home/norty/.hermes/uacp/.outputs/lexa-executable-contract-bootstrap-20260521/
```

Input evidence:

```text
/home/norty/vault/02-architecture/LEXA/
```

The Vault packet remains draft input. The bootstrap output is not canonical until VERIFY/RESOLVE records what passed and Mike chooses a promotion surface.

## Artifact Map

Machine lifecycle artifacts:

- `proposals/lexa-executable-contract-bootstrap-20260521-triage.yaml`
- `proposals/lexa-executable-contract-bootstrap-20260521-proposal.yaml`
- `proposals/lexa-executable-contract-bootstrap-20260521-gate-selection.yaml`

Human proposal package:

- `proposals/lexa-executable-contract-bootstrap-20260521/00-index.md`

Expected PLAN/EXECUTE artifacts later:

- staging `README.md` and docs index;
- `schemas/`;
- `fixtures/valid/` and `fixtures/invalid/`;
- validator script;
- optional reference packet builder;
- verification summary.

## Verification Requirements

VERIFY must prove convergence, not merely file existence:

- schemas parse and references resolve;
- valid fixtures pass;
- invalid fixtures fail for the right reason;
- public/private leakage guard is executable;
- source provenance is executable;
- cross-workspace authorization is executable;
- advisory Vault drafts cannot become canonical facts without explicit promotion;
- reference packet builder outputs validate if builder is selected;
- docs are patched where executable behavior disproves or sharpens draft claims;
- no live runtime integration occurred.

## Decision

Proceed to PLAN if Mike accepts this proposal framing.

PLAN must define exact work packages, staging path, validation commands, whether a reference packet builder is included in the first iteration, and rollback/cleanup behavior.
