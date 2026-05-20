---
type: index
tags: [index, guide, human-readable, agent-readable]
status: living-document
---

# Guides — Index

Guides are curated reading paths for humans and agents. They explain how to read and operate UACP without replacing canonical policy, lifecycle, runtime, reference, or ADR documents.

## Available guides

| Guide | Purpose | Start here when |
|---|---|---|
| [lifecycle-hardening/](lifecycle-hardening/00-index.md) | Human and agent guide to the semantic package, PIV, VERIFY, RESOLVE, Guardian, Heartgate, and audit-remediation hardening series. | You need to understand why the recent lifecycle changes exist, how the pieces fit, or how to avoid fracturing documentation. |

## Guide rules

- A guide is a navigation and explanation layer, not a new authority layer.
- Every substantial guide must have a `00-index.md` conductor with reading order, canonical sources, and update boundaries.
- Do not scatter phase rules across guide pages. Link to the canonical file that owns the rule.
- If a guide changes an invariant, it is no longer a guide change; route it to ADR/config/validator/runtime updates.
