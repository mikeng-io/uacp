---
name: uacp-web
description: Unified web evidence backend for UACP phases — selects and invokes the right data provider (Tavily, Firecrawl, Devin, Context7) to collect live web evidence during triage, propose, plan, and verify phases.
---

# uacp-web — Web Evidence Backend

Reference document for UACP web evidence retrieval.  Orchestrating skills (triage,
propose, etc.) read this file and embed relevant sections into their prompts.

## Purpose

Provide a **unified, swappable abstraction** over web data backends so that UACP
phases can collect live web evidence without hard-coding a specific provider.

Current backends:
- **Tavily** — search + extract (lightweight, fast)
- **Firecrawl** — search + scrape + crawl + extract (deep, full-site)
- **Devin** — session-based AI agent research (deep reasoning, code-aware, private repos)
- **Context7** — library documentation retrieval (version-specific, code-snippet focused)

Future backends (plug-in via `BackendFactory.register`):
- SearXNG (self-hosted)
- Exa / Metaphor
- Custom internal indexes

## Architecture

```
Orchestrating skill (triage / propose)
           │
           ▼
   BackendFactory.create("tavily" | "firecrawl" | "devin" | "context7")
           │
    ┌──────┼──────┬──────────┐
    ▼      ▼      ▼          ▼
 Tavily  Firecrawl  Devin   Context7
    │      │      │          │
    ▼      ▼      ▼          ▼
 api.tavily.com  api.firecrawl.dev  api.devin.ai/v3  context7.com/api/v2
```

## When to Use Which Backend

| Phase | Goal | Recommended Backend | Rationale |
|-------|------|---------------------|-----------|
| **Triage** | Quick scope validation, risk classification, routing | **Tavily** | Fast search, low latency, good for "does this exist / what is the landscape" |
| **Triage** | Code-aware intake, private repo docs, complex reasoning | **Devin** | Deep reasoning over codebases; private repo access via wiki tools |
| **Propose** | Deep context enrichment, competitive analysis, full evidence corpus | **Firecrawl** | Scrape + crawl for comprehensive coverage; structured extraction for schema-driven data |
| **Propose** | Agent-driven research, multi-step investigation, PR/code review context | **Devin** | Session-based research with persistent reasoning; can analyze GitHub repos end-to-end |
| **Plan** | Evidence cluster selection, verification proof matrix | **Firecrawl** | Crawl to build the corpus that bridges will analyze |
| **Verify** | Cross-check claims against live sources | **Tavily** | Quick freshness checks; compare against cached crawl data |
| **Verify** | Re-run Devin sessions to validate prior research conclusions | **Devin** | Session replay and message history for audit trails |
| **Any** | Library API docs, framework syntax, version-specific references | **Context7** | Up-to-date indexed docs with code snippets; prevents stale training-data hallucinations |

## Configuration

API keys are read from environment variables (never committed):

```bash
export TAVILY_API_KEY="tvly-..."
export FIRECRAWL_API_KEY="fc-..."
export DEVIN_API_KEY="cog-..."      # Devin service user key
export DEVIN_ORG_ID="org-..."       # Devin organization ID
export CONTEXT7_API_KEY="ctx7sk-..." # Context7 API key (optional — works without)
```

Optional: override base URLs for self-hosted or enterprise endpoints:

```python
backend = BackendFactory.create(
    "firecrawl",
    api_key="fc-...",
    base_url="https://enterprise.firecrawl.dev/v1",
)
```

## Python API

### Quick Start

```python
from web_backend import BackendFactory

# Triage — quick search
backend = BackendFactory.create("tavily")
results = backend.search("Python async best practices 2026", max_results=5)
for r in results:
    print(f"{r.title} ({r.relevance_score}): {r.url}")

# Propose — deep crawl
backend = BackendFactory.create("firecrawl")
crawl = backend.crawl("https://docs.python.org/3/library/asyncio.html", limit=20)
for page in crawl.pages:
    print(page["metadata"]["sourceURL"])

# Propose — agent-driven research (Devin)
backend = BackendFactory.create("devin", org_id="your-org-id")
results = backend.search("Analyze the codebase architecture of github.com/vercel/next.js")
print(results[0].content)  # Full research report from Devin session

# Any phase — library docs (Context7)
backend = BackendFactory.create("context7")  # no API key needed for light use
results = backend.search("fastapi async endpoints")
print(results[0].content)  # Current FastAPI docs with code snippets
```

### Operations

#### `search(query, max_results=5, **kwargs)` → `list[SearchResult]`

All backends support search.

- **Tavily**: scored results with content snippets.
- **Firecrawl**: SERP + optional markdown scrape per result.
- **Devin**: creates a research session, polls until settled, returns the assistant's full research report as a single `SearchResult`.

Common kwargs:
- `search_depth` — `"basic"` (default) or `"advanced"` (Tavily only)
- `include_raw_content` — include full page text (Tavily only)
- `scrape` — `True` to scrape each result (Firecrawl only)
- `max_polls` / `poll_interval` — Devin session polling (Devin only, defaults 60 × 5s)

#### `scrape(url, **kwargs)` → `ScrapeResult`

**Firecrawl and Devin.** Convert a single URL to clean markdown.

- **Firecrawl**: direct HTTP scrape with format options.
- **Devin**: creates a session to analyze the URL, returns assistant's markdown summary.

Kwargs:
- `formats` — `["markdown"]`, `["html"]` (Firecrawl only)
- `only_main_content` — strip nav/footers (Firecrawl only, default `True`)

#### `crawl(url, limit=10, **kwargs)` → `CrawlResult`

**Firecrawl and Devin.** Walk a site starting from a URL.

- **Firecrawl**: async BFS crawl with job polling.
- **Devin**: creates a session to discover URLs, parses bullet-list response.

Kwargs:
- `include_paths` / `exclude_paths` — glob patterns (Firecrawl only)
- `max_polls` / `poll_interval` — polling config (both)

#### `extract(url, schema=None, **kwargs)` → `ExtractResult`

All backends. Extract structured data from a URL.

- **Tavily**: uses `/extract` endpoint.
- **Firecrawl**: uses `/scrape` with `extract` option.
- **Devin**: creates a session with schema prompt, attempts to parse assistant response as JSON.

#### `health_check()` → `bool`

Lightweight probe. Returns `True` if the backend is reachable and authenticated.

### Data Models

```python
class SearchResult:
    title: str
    url: str
    content: str       # full content if available
    snippet: str       # short description
    source: str        # "tavily" | "firecrawl"
    relevance_score: float | None
    timestamp: str | None

class ScrapeResult:
    url: str
    markdown: str
    html: str
    metadata: dict
    source: str

class ExtractResult:
    url: str
    structured_data: dict
    raw_content: str
    source: str

class CrawlResult:
    urls_found: list[str]
    pages: list[dict]
    total: int
    completed: int
    source: str
```

## Devin-Specific Operations

Devin is a **session-based AI agent platform**, not a direct web search engine.
All web operations (`search`, `scrape`, `crawl`, `extract`) are mapped to Devin
sessions that perform the research task.  The session response is parsed into
unified result types.

### Session Management

```python
backend = BackendFactory.create("devin", org_id="your-org-id")

# Create a standalone research session
session = backend.create_session(
    "Refactor the authentication module to use JWT",
    title="Auth refactor",
    playbook_id="my-playbook",
    tags=["urgent", "security"],
)
print(session["devin_id"])   # devin-abc123
print(session["url"])        # https://app.devin.ai/sessions/devin-abc123

# List existing sessions
sessions = backend.list_sessions()
for s in sessions:
    print(f"{s['devin_id']}: {s['status']} — {s.get('prompt', '')[:50]}")
```

### Devin vs DeepWiki

| Feature | DeepWiki MCP | Devin MCP (preferred) |
|---------|--------------|----------------------|
| Authentication | None | API key required (`cog_` prefix) |
| Repository access | Public only | Public + private |
| Platform mgmt | None | Sessions, playbooks, knowledge, schedules |
| Cost | Free | Requires Devin account |

UACP uses **Devin MCP** (not DeepWiki) for all agent-driven research.

## Context7-Specific Operations

Context7 is a **library documentation retrieval** backend, not a general web
search engine.  It indexes official docs for popular libraries and returns
version-specific code snippets with syntax highlighting.

### When to Use Context7

| Situation | Why Context7 |
|-----------|-------------|
| Implementing with a library whose training data is stale | Returns current docs, not outdated memorized APIs |
| Need exact function signatures / parameter lists | Snippets include precise code examples |
| Working with rapidly evolving frameworks (Next.js, FastAPI, etc.) | Version-aware retrieval prevents deprecated-pattern bugs |
| Verifying API compatibility during triage/propose | Quick lookup without full web crawl |

### Two-Step Flow

```python
backend = BackendFactory.create("context7")

# Step 1: resolve library name → Context7 ID
lib_id = backend.resolve_library("fastapi")
print(lib_id)  # /tiangolo/fastapi

# Step 2: query docs with topic filter
snippets = backend.query_docs(
    "/tiangolo/fastapi",
    query="dependency injection",
    tokens=4000,  # control response size
)
for s in snippets:
    print(f"{s['title']}: {s['description'][:80]}...")
```

### Query Format

Context7 `search` expects queries of the form ``library_name topic``:

```python
backend.search("fastapi async endpoints")      # ✓ correct
backend.search("nextjs middleware")            # ✓ correct
backend.search("how do I use react hooks")     # ✗ ambiguous — first word treated as library
```

### Auth Note

Context7 works **without an API key** at reduced rate limits.  Set
`CONTEXT7_API_KEY` for production/heavy usage.

## Guardian Classification

Web backend operations are classified as `external.network_read`.

Policy defaults (in `config/uacp.toml [guardian]`):

```yaml
protected_categories:
  external.network_read:
    default_decision: allow_with_audit
```

All web calls are logged to the gate ledger with:
- `tool_name`: `uacp_web_search` | `uacp_web_scrape` | `uacp_web_crawl` | `uacp_web_extract`
- `declared_side_effects`: `["external.network_read"]`

## Output Artifacts

Web evidence is stored under `.uacp/evidence/{run_id}/`:

```
.uacp/evidence/uacp-2026-0607-fix-router/
  search-triage-001.jsonl      # SearchResult items
  search-triage-001.md         # Markdown summary
  crawl-propose-001.jsonl      # CrawlResult pages
  crawl-propose-001.md         # Markdown summary
```

The orchestrating skill is responsible for writing these artifacts; the
`web_backend` module returns pure Python objects.

## Extending with New Backends

```python
from web_backend import WebBackend, SearchResult, ExtractResult, BackendFactory

class SearxngBackend(WebBackend):
    def search(self, query, max_results=5, **kwargs):
        # ... implementation ...
        return [SearchResult(...)]

    def extract(self, url, schema=None, **kwargs):
        # ... implementation ...
        return ExtractResult(...)

BackendFactory.register("searxng", SearxngBackend)
backend = BackendFactory.create("searxng", api_key="...")
```

## Dependencies

- Python ≥ 3.10
- Pydantic v2
- Standard library only (`urllib.request`, `json`)

No external HTTP libraries required.
