# UACP MEMEX + BES Context Capture — Index

Date: 2026-05-15
Source: Discord dispatch thread `#46 — UACP vs Trustless ACP Retrieval Systems`
Purpose: preserve the full design discussion before context is lost. This is a working capture, not canonical UACP doctrine.

## Files

1. `01-question-and-status.md` — Original question: whether current UACP has Trustless-style knowledge base / BES / hybrid retrieval.
2. `02-naming-and-nortrix-correction.md` — Naming debate: EVIDENCE vs MEMEX vs Recall; Nortrix correction.
3. `03-agent-council-results.md` — Agent Council dispatch summary and audit outcomes.
4. `04-memex-bes-architecture.md` — Architecture model: MEMEX as connective memory, BES as learning/weighting signal.
5. `05-extraction-retrieval-creation.md` — The three flows: extraction, retrieval, creation.
6. `06-enforcement-bootstrap-guardian.md` — Enforcement model and why MEMEX implementation cannot initially be a normal UACP proposal.
7. `07-memory-context-dump.md` — Full recalled memory-context provided by Mike in the thread.
8. `08-open-decisions-and-next-steps.md` — Open decisions, risks, and immediate next actions.

## Key conclusion

MEMEX + BES should be treated as UACP control-plane connective memory infrastructure:

```text
MEMEX retrieves and structures governed memory.
BES ranks and learns what mattered.
Guardian enforces presence/provenance/write boundaries.
Heartgate validates adequacy at transitions.
RESOLVE/governed writers create/update durable MEMEX/BES state.
```

But **implementation of MEMEX itself cannot initially be a normal UACP proposal**, because it touches the governance documents/config/runtime policy that Guardian is designed to protect. It needs a narrow bootstrap lane first.
