---
type: adr
title: Treat UACP package Markdown as semantic substrate
description: Mandate that adaptive PROPOSE and PLAN package directories contain semantically recoverable Markdown, not placeholder stubs, so future agents can recover intent without chat history.
tags: [markdown, semantic-substrate, packages, recoverability]
timestamp: 2026-05-19
status: accepted
---

# ADR 0011: Treat UACP Package Markdown as Semantic Substrate

Status: accepted
Date: 2026-05-19

## What changed

UACP adaptive package Markdown is now a required semantic substrate when a proposal or plan package is selected. It is not optional presentation material.

Validator behavior is tightened so package-selection artifacts must point universal-core concerns at readable Markdown documents with enough semantic content for future agent recovery. Placeholder files, one-line stubs, non-Markdown artifacts, or files that do not carry the required concern semantics are blockers.

The active PROPOSE and PLAN skills are updated to state that YAML proposal/plan files are machine lifecycle envelopes only. They are not sufficient for standard/full governance work when the package gate applies.

## Why

A future agent or operator must be able to return to a run one month later and recover:

1. Why the work exists.
2. How the mechanism or execution topology works.
3. The intention, rationale, and decision.
4. The authority, scope, containment, risks, verification strategy, rollback, review topology, and transition boundary.

YAML can carry structured state, but it is usually too compressed to preserve the semantic reasoning needed for durable governance. Markdown packages provide recoverable meaning for agents and humans.

## Decision

When an adaptive PROPOSE or PLAN package is selected:

- The package directory is mandatory.
- The package-selection YAML must map universal-core concerns to Markdown artifacts.
- Each mapped Markdown artifact must contain heading structure and enough explanatory prose to support semantic recovery.
- A package artifact must not be treated as valid merely because the path exists.

## Invariants

- YAML remains the machine lifecycle envelope.
- Markdown packages are the semantic review and future-retrieval surface.
- This does not require fixed OpenSpec/Trustless document lists; package selection remains adaptive.
- The validator enforces minimum semantic recoverability, not literary style.
- Evidence completeness and operator presentation rules remain separate concerns.

## Verification

- `scripts/validate_uacp_artifacts.py` enforces semantic Markdown checks for proposal and plan package-selection artifacts.
- Positive adaptive package fixtures contain meaningful Markdown and pass.
- Existing repository validation still passes.
