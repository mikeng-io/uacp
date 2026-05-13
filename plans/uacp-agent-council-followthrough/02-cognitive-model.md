# 02 — Cognitive Model

Status: active follow-through package  
Created: 2026-05-12T18:04:59.583598+00:00  
Authority root: `UACP_ROOT`  
Scope: preserve and execute the UACP Agent-Council integration context without relying on chat memory.  

---

## Core model

```text
UACP = governance cognition
Agent Council = deliberative orchestration
Kanban = coordination memory
Runtimes = bounded worker cognition / execution loops
Tools + evidence services = actuation / observation
Guardian + Heartgate = boundary enforcement
```

## Layer responsibilities

### UACP

Owns:

- authority,
- phase state,
- side-effect boundaries,
- phase-local/composite granularity,
- human involvement thresholds,
- evidence obligations,
- pass/warn/block phase transition decisions.

### Agent Council

Owns deliberation:

- strategy,
- role topology,
- decomposition,
- challenge / Devil's Advocate,
- integration critique,
- synthesis,
- council findings.

Agent Council is not review-only. It may orchestrate implementation when work is non-trivial.

### Kanban

Owns coordination memory:

- task graph,
- dependencies,
- status,
- ownership,
- handoffs,
- links to artifacts and evidence.

Kanban is not UACP phase state and not the deliberation engine.

### Runtimes / tools / evidence services

- Agent runtimes host autonomous or semi-autonomous workers.
- Tool adapters let workers act: browser, computer use, terminal, local scripts, Puppeteer/Playwright.
- Evidence services retrieve/process evidence: Firecrawl, Tavily, SearXNG, web search, scraping APIs, transcripts, OCR.

These surfaces need manifests and policy classification before production use.

## Category-error guard

- Do not use Kanban as policy authority.
- Do not use Agent Council as persistent state.
- Do not use tools/evidence services as autonomous authority.
- Do not let workers silently change UACP phase state.
- Do not claim runtime enforcement if Guardian/Heartgate only observe or can be bypassed.
