---
type: adr
title: Web backends remain separate from bridge-* runtime adapters
description: Keep web-evidence backends (Tavily, Firecrawl, Devin, Context7) in a dedicated uacp-web skill rather than embedding them inside each bridge-* runtime adapter.
tags: [web-backends, bridge, uacp-web, separation-of-concerns]
timestamp: 2026-06-08
status: accepted
---

# Web Backends Remain Separate from Bridge-* Runtime Adapters

## Metadata

- **Status**: accepted
- **Date**: 2026-06-08
- **Decision Makers**: UACP maintainer
- **Consulted**: `bridge-commons` skill, `uacp-web` skill, `uacp-context` skill
- **Informed**: All lifecycle and bridge skills

## Context and Problem Statement

UACP needs web-evidence capabilities (search, scrape, extract, docs retrieval, session-based AI research). The user explicitly requested Tavily, Firecrawl, Devin, and Context7 as web backends. A question arose: should these backends live inside each `bridge-*` runtime adapter skill (e.g., `bridge-claude`, `bridge-codex`), or should they be a separate shared skill?

The risk of putting them in bridges:
- Conflates AI-runtime dispatch (Claude Code, Kimi Code, Codex CLI, etc.) with general web/data retrieval.
- Duplicates backend logic across 5+ bridge skills.
- Makes it harder to add new backends or switch providers.

The risk of a separate skill:
- Adds one more dependency for skills that need web enrichment.
- Requires a clear boundary contract with bridges.

## Decision Drivers

- `bridge-*` skills are **runtime dispatch adapters**, not general tool adapters.
- Tavily/Firecrawl are web services; Context7 is docs retrieval; Devin is a session-based AI platform — none are local AI runtimes.
- Lifecycle skills (`uacp-context`, `uacp-triage`, `uacp-propose`) need web enrichment **before** deciding which bridges to dispatch.
- A unified `WebBackend` abstraction with a `BackendFactory` registry is simpler to maintain than N bridge-specific integrations.

## Considered Options

1. **Integrate into each `bridge-*` skill** — each bridge implements its own Tavily/Firecrawl/Devin/Context7 invocation.
2. **Separate `uacp-web` skill with unified abstraction** — lifecycle skills call `uacp-web`; bridges receive enriched context.
3. **Hybrid** — both a shared skill and per-bridge integrations.
4. **MCP-only** — require all web access to go through runtime-specific MCP servers.

## Decision Outcome

Chosen option: **2 — Separate `uacp-web` skill**.

`uacp-web` owns the unified `WebBackend` interface and backend registry. Lifecycle skills call `uacp-web` to gather evidence, then pass summarized, validated context into bridge inputs. Bridges do not fetch web evidence themselves.

### Positive Consequences

- Single place to add new backends via `BackendFactory.register(...)`.
- Bridge skills stay focused on AI-runtime dispatch.
- Web enrichment can run during context analysis and triage, before any bridge is selected.
- Easier to test, mock, and audit web calls independently.

### Negative Consequences

- Adds one dependency (`uacp-web`) for skills that need enrichment.
- Requires explicit boundary: bridges must accept enriched context via `runtime_input.context_summary` rather than fetching their own.

## Validation

- `skills/uacp-web/scripts/web_backend.py` implements the unified abstraction.
- `skills/uacp-context/SKILL.md` lists `uacp-web` as a dependency and uses it in Phase 4 enrichment.
- `skills/bridge-commons/SKILL.md` defines bridge inputs to receive `context_summary`; it does not define web-fetch behavior.

## Related ADRs

- Related: [0012](0012-phase-intent-verification.md) — context quality affects phase intent verification.

## References

- Implementation: `skills/uacp-web/scripts/web_backend.py`
- Consumer: `skills/uacp-context/SKILL.md`
- Boundary contract: `skills/bridge-commons/SKILL.md`
