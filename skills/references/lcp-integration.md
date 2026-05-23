# LCP Integration Pattern

LCP (Liaison Control Plane) is a UACP-adjacent governance layer for public-facing assistant profiles. It governs what a public assistant may observe, remember, share, and do on the operator's behalf.

## Relationship to UACP

- **UACP** governs agent work, execution, mutation, verification
- **LCP** governs public context, social memory, consent, delegated authority
- LCP implementation is UACP-governed; LCP runtime is not UACP

## Design Artifacts

Canonical design doc: `~/.hermes/plans/lcp/LCP_REQUIREMENTS_AND_ARCHITECTURE.md`
Phase 0 artifacts: `~/.hermes/liaison/` (20 files: schemas, policies, SQLite schema, templates)

## Key Pattern: Claude Code as Design Reviewer

For design/architecture documents, use Claude Code print mode (`-p`) with `--effort high` for adversarial review. Pipe the document via stdin:

```bash
cat design-doc.md | claude -p 'Review this document for [specific focus areas]...' --max-turns 1 --effort high
```

This found 6 critical issues and 13 gaps in the LCP design — far more thorough than a quick read-through. Use for:
- Security/threat model review
- Architecture consistency checks
- Schema completeness validation
- Guard/policy gap detection

## Key Pattern: Multi-Model Delegation for Design Work

Mike's preferred model routing for large design tasks:
- **MiMo V2.5 Pro (Xiaomi direct)**: Drafting, breadth, taxonomy, first-pass docs
- **MiniMax-M2.7 (delegation)**: Bounded subtasks, schemas, file creation via `delegate_task`
- **Claude Code**: Security review, adversarial analysis, architecture critique
- **GPT-5.5**: Final governance review, UACP phase decisions, security approval

Never use OpenRouter for MiMo — use direct Xiaomi provider (XIAOMI_API_KEY + XIAOMI_BASE_URL in .env).

## LCP Architecture Summary

- 10 abstractions: Space, Actor, Capsule, Fact, Claim, Request, Approval, Task, Digest, AuditEvent
- 8 guards: PI, Ingestion, Authority, Action, Retrieval, Sharing, Retention, Egress
- Authority levels: L0 Observe → L4 Commit (always requires Mike approval)
- File-based bridge: `~/.hermes/liaison/bridge/{pending,approved,rejected,revoked}/`
- 11 SQLite tables + 14 indexes
- Deterministic guards (code, not LLM) — LLM output hard-floored at `observed`/`claimed`
