---
type: index
tags: [index, guide, human-readable, agent-readable]
status: living-document
---

# Guides — Index

Guides are curated reading paths for humans and agents. They explain how to read and operate UACP without replacing canonical policy, lifecycle, runtime, reference, or ADR documents.

## Available guides

| File | Title | Description |
|---|---|---|
| [lifecycle-hardening/00-index.md](lifecycle-hardening/00-index.md) | Lifecycle Hardening Guide — Reading Order | Conductor index for the UACP lifecycle-hardening series: reading order, canonical sources, and anti-fracture rules. |
| [lifecycle-hardening/01-human-overview.md](lifecycle-hardening/01-human-overview.md) | Human Overview — What Changed and Why | Human-readable explanation of the UACP lifecycle-hardening series: what changed, why, and what coherence means. |
| [lifecycle-hardening/02-agent-operating-guide.md](lifecycle-hardening/02-agent-operating-guide.md) | Agent Operating Guide — How to Work in This Area | Operating posture, required workflow, and completion standard for agents modifying UACP lifecycle gates, Heartgate, Guardian, or validator behavior. |
| [lifecycle-hardening/03-artifact-and-gate-map.md](lifecycle-hardening/03-artifact-and-gate-map.md) | Artifact and Gate Map | Shows where meaning and enforcement live per phase: machine envelopes, semantic packages, key enforcement files, fixtures, and critical invariants. |
| [lifecycle-hardening/04-audit-and-remediation-history.md](lifecycle-hardening/04-audit-and-remediation-history.md) | Audit and Remediation History | Preserves the reasoning shape of the lifecycle-hardening audit loop: why external audits were required, themes, material remediations, and lessons learned. |

## Guide rules

- A guide is a navigation and explanation layer, not a new authority layer.
- Every substantial guide must have a `00-index.md` conductor with reading order, canonical sources, and update boundaries.
- Do not scatter phase rules across guide pages. Link to the canonical file that owns the rule.
- If a guide changes an invariant, it is no longer a guide change; route it to ADR/config/validator/runtime updates.
