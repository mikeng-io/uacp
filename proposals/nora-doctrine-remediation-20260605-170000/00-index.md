# Nora Doctrine + Identity Registry Remediation — Proposal Package

## Overview

This proposal addresses 3 CRITICAL + 7 HIGH findings from an agent council review of Nora's doctrine files and identity-registry plugin. The council found that the trust root has migrated from the system prompt to operator-authored YAML, and no doctrine file acknowledges this.

## Documents

| Document | Purpose |
|---|---|
| [proposal.md](proposal.md) | Main proposal: what is changing and why |
| [authority-scope-containment.md](authority-scope-containment.md) | Authority, scope, and containment |
| [risks-and-verification.md](risks-and-verification.md) | Risks and verification criteria |
| [artifacts.md](artifacts.md) | Artifact map and transition meaning |

## Council Evidence

- **Review ID:** agent-council-20260605-170000
- **Verdict:** FAIL
- **Critical findings:** 3
- **High findings:** 7
- **Synthesis artifact:** `/home/norty/.hermes/profiles/nora/EXPERTS_COUNCIL_SYNTHESIS.json`
- **Report artifact:** `/home/norty/.hermes/profiles/nora/COUNCIL_REPORT.md`

## Remediation Tracks

1. **RT-1: Doctrinal grant** — Add to SECURITY.md and IDENTITY.md
2. **RT-2: Tighten safe card** — Drop relationship.trust_tier in public/group channels
3. **RT-3: Schema validation** — Deny-by-default on YAML→runtime→plugin
4. **RT-4: Health/observability** — Operator-visible lookup success/fail
5. **RT-5: Hook contract** — Document pre_gateway_dispatch event mutation
6. **RT-6: Language/tone precedence** — Define between PERSONALITY.md and card

## Status

- **Phase:** PROPOSE
- **Run ID:** nora-doctrine-remediation-20260605-170000
- **Decision owner:** Mike
