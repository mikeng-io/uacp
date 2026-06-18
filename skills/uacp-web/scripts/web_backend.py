"""UACP web backend abstraction.

Provides a unified interface over Tavily and Firecrawl (and future backends)
for web search, scraping, extraction, and crawling.  Used by the triage and
propose phases for evidence collection and context enrichment.

Runtime-neutral — contains no Hermes or framework-specific imports.
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from typing import Any

# Prefer Pydantic v2; fall back to v1 for compatibility.
try:
    from pydantic import BaseModel, Field
except Exception as exc:  # pragma: no cover
    raise ImportError("Pydantic is required for web_backend") from exc


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class SearchResult(BaseModel):
    """A single search result item."""

    title: str
    url: str
    content: str = ""
    snippet: str = ""
    source: str = "unknown"
    relevance_score: float | None = None
    timestamp: str | None = None


class ScrapeResult(BaseModel):
    """Result of scraping a single URL."""

    url: str
    markdown: str = ""
    html: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str = "unknown"


class ExtractResult(BaseModel):
    """Result of structured extraction from a URL."""

    url: str
    structured_data: dict[str, Any] = Field(default_factory=dict)
    raw_content: str = ""
    source: str = "unknown"


class CrawlResult(BaseModel):
    """Result of crawling a site."""

    urls_found: list[str] = Field(default_factory=list)
    pages: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    completed: int = 0
    source: str = "unknown"


# ---------------------------------------------------------------------------
# Abstract backend
# ---------------------------------------------------------------------------

class WebBackend(ABC):
    """Unified interface for web evidence backends."""

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("api_key is required")
        self.api_key = api_key.strip()
        self.base_url = base_url

    @abstractmethod
    def search(self, query: str, max_results: int = 5, **kwargs: Any) -> list[SearchResult]:
        """Search the web and return a list of results."""
        ...

    @abstractmethod
    def extract(self, url: str, schema: dict[str, Any] | None = None, **kwargs: Any) -> ExtractResult:
        """Extract structured data from a single URL."""
        ...

    def health_check(self) -> bool:
        """Probe the backend for connectivity.  Defaults to a lightweight search.
        Subclasses may override with a cheaper endpoint."""
        try:
            self.search("__health_probe__", max_results=1)
            return True
        except Exception:
            return False

    # Optional surface — not all backends support it.
    def scrape(self, url: str, **kwargs: Any) -> ScrapeResult:
        raise NotImplementedError(f"{self.__class__.__name__} does not support scrape")

    def crawl(self, url: str, limit: int = 10, **kwargs: Any) -> CrawlResult:
        raise NotImplementedError(f"{self.__class__.__name__} does not support crawl")


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _http_json(method: str, url: str, headers: dict[str, str], body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Make an HTTP request and return parsed JSON."""
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as resp:
        if resp.getcode() >= 400:
            raise RuntimeError(f"HTTP {resp.getcode()}: {url}")
        raw = resp.read()
    parsed = json.loads(raw.decode("utf-8"))
    return parsed


# ---------------------------------------------------------------------------
# Tavily backend
# ---------------------------------------------------------------------------

class TavilyBackend(WebBackend):
    """Tavily search + extract backend.

    Docs: https://docs.tavily.com/documentation/api-reference/introduction
    """

    DEFAULT_BASE_URL = "https://api.tavily.com"

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        super().__init__(api_key, base_url or self.DEFAULT_BASE_URL)

    def search(self, query: str, max_results: int = 5, **kwargs: Any) -> list[SearchResult]:
        url = f"{self.base_url}/search"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "query": query,
            "max_results": max_results,
            "include_answer": kwargs.get("include_answer", False),
            "search_depth": kwargs.get("search_depth", "basic"),
        }
        if "include_raw_content" in kwargs:
            payload["include_raw_content"] = kwargs["include_raw_content"]
        resp = _http_json("POST", url, headers, payload)
        results = resp.get("results") or []
        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", ""),
                snippet=r.get("snippet", ""),
                source="tavily",
                relevance_score=r.get("score"),
                timestamp=_iso_now(),
            )
            for r in results
        ]

    def extract(self, url: str, schema: dict[str, Any] | None = None, **kwargs: Any) -> ExtractResult:
        api_url = f"{self.base_url}/extract"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload: dict[str, Any] = {"urls": [url]}
        if schema:
            payload["extract_schema"] = schema
        if kwargs.get("include_images"):
            payload["include_images"] = True
        resp = _http_json("POST", api_url, headers, payload)
        results = resp.get("results") or {}
        return ExtractResult(
            url=url,
            raw_content=results.get("raw_content", ""),
            structured_data=results.get("structured_data") or {},
            source="tavily",
        )

    def health_check(self) -> bool:
        """Use a lightweight search as the health probe."""
        try:
            self.search("health check", max_results=1)
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Firecrawl backend
# ---------------------------------------------------------------------------

class FirecrawlBackend(WebBackend):
    """Firecrawl search + scrape + crawl + extract backend.

    Docs: https://docs.firecrawl.dev
    """

    DEFAULT_BASE_URL = "https://api.firecrawl.dev/v1"

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        super().__init__(api_key, base_url or self.DEFAULT_BASE_URL)

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def search(self, query: str, max_results: int = 5, **kwargs: Any) -> list[SearchResult]:
        url = f"{self.base_url}/search"
        payload = {
            "query": query,
            "limit": max_results,
        }
        if kwargs.get("scrape"):
            payload["scrapeOptions"] = {"formats": ["markdown"]}
        resp = _http_json("POST", url, self._headers(), payload)
        data = resp.get("data") or []
        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("markdown", r.get("description", "")),
                snippet=r.get("description", ""),
                source="firecrawl",
                timestamp=_iso_now(),
            )
            for r in data
        ]

    def scrape(self, url: str, **kwargs: Any) -> ScrapeResult:
        api_url = f"{self.base_url}/scrape"
        payload: dict[str, Any] = {"url": url}
        formats = kwargs.get("formats", ["markdown"])
        if formats:
            payload["formats"] = formats
        if kwargs.get("only_main_content") is not None:
            payload["onlyMainContent"] = kwargs["only_main_content"]
        resp = _http_json("POST", api_url, self._headers(), payload)
        data = resp.get("data") or {}
        return ScrapeResult(
            url=url,
            markdown=data.get("markdown", ""),
            html=data.get("html", ""),
            metadata=data.get("metadata") or {},
            source="firecrawl",
        )

    def crawl(self, url: str, limit: int = 10, **kwargs: Any) -> CrawlResult:
        api_url = f"{self.base_url}/crawl"
        payload: dict[str, Any] = {"url": url, "limit": limit}
        if kwargs.get("include_paths"):
            payload["includePaths"] = kwargs["include_paths"]
        if kwargs.get("exclude_paths"):
            payload["excludePaths"] = kwargs["exclude_paths"]
        formats = kwargs.get("formats", ["markdown"])
        if formats:
            payload["scrapeOptions"] = {"formats": formats}

        # Start crawl job
        resp = _http_json("POST", api_url, self._headers(), payload)
        job_id = resp.get("id")
        if not job_id:
            raise RuntimeError("crawl job did not return an id")

        # Poll for completion (simplified — production may want async + webhook)
        status_url = f"{self.base_url}/crawl/{job_id}"
        max_polls = kwargs.get("max_polls", 30)
        poll_interval = kwargs.get("poll_interval", 2)
        for _ in range(max_polls):
            time.sleep(poll_interval)
            status = _http_json("GET", status_url, self._headers())
            if status.get("status") == "completed":
                pages = status.get("data") or []
                urls = [p.get("metadata", {}).get("sourceURL", "") for p in pages]
                return CrawlResult(
                    urls_found=urls,
                    pages=pages,
                    total=status.get("total", len(pages)),
                    completed=status.get("completed", len(pages)),
                    source="firecrawl",
                )
            if status.get("status") in {"failed", "cancelled"}:
                raise RuntimeError(f"crawl job {job_id} {status.get('status')}")
        raise RuntimeError(f"crawl job {job_id} did not complete within poll limit")

    def extract(self, url: str, schema: dict[str, Any] | None = None, **kwargs: Any) -> ExtractResult:
        api_url = f"{self.base_url}/scrape"
        payload: dict[str, Any] = {"url": url}
        if schema:
            payload["extract"] = {"schema": schema}
        resp = _http_json("POST", api_url, self._headers(), payload)
        data = resp.get("data") or {}
        extracted = data.get("extract") or {}
        return ExtractResult(
            url=url,
            structured_data=extracted if extracted else {},
            raw_content=data.get("markdown", ""),
            source="firecrawl",
        )

    def health_check(self) -> bool:
        """Use a lightweight scrape as the health probe."""
        try:
            self.scrape("https://example.com")
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Devin backend
# ---------------------------------------------------------------------------

class DevinBackend(WebBackend):
    """Devin REST API v3 backend.

    Devin is a session-based AI agent platform.  Rather than direct web
    search/scrape, operations are mapped to Devin sessions that perform
    research tasks.  The session response is parsed into the unified
    WebBackend result types.

    Docs: https://docs.devin.ai/api-reference/v3/overview
    """

    DEFAULT_BASE_URL = "https://api.devin.ai/v3"

    def __init__(self, api_key: str, org_id: str, base_url: str | None = None) -> None:
        if not org_id or not org_id.strip():
            raise ValueError("org_id is required")
        super().__init__(api_key, base_url or self.DEFAULT_BASE_URL)
        self.org_id = org_id.strip()

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _org_url(self, path: str) -> str:
        return f"{self.base_url}/organizations/{self.org_id}{path}"

    def create_session(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        """Create a new Devin session."""
        url = self._org_url("/sessions")
        payload: dict[str, Any] = {"prompt": prompt}
        if kwargs.get("title"):
            payload["title"] = kwargs["title"]
        if kwargs.get("playbook_id"):
            payload["playbook_id"] = kwargs["playbook_id"]
        if kwargs.get("tags"):
            payload["tags"] = kwargs["tags"]
        return _http_json("POST", url, self._headers(), payload)

    def _get_session(self, devin_id: str) -> dict[str, Any]:
        url = self._org_url(f"/sessions/{devin_id}")
        return _http_json("GET", url, self._headers())

    def _get_messages(self, devin_id: str) -> list[dict[str, Any]]:
        url = self._org_url(f"/sessions/{devin_id}/messages")
        resp = _http_json("GET", url, self._headers())
        return resp.get("messages") or []

    def _poll_until_settled(
        self,
        devin_id: str,
        max_polls: int = 60,
        poll_interval: int = 5,
    ) -> dict[str, Any]:
        """Poll session status until it reaches a settled state."""
        settled = {"stopped", "errored", "sleeping", "waiting"}
        for _ in range(max_polls):
            status = self._get_session(devin_id)
            if status.get("status") in settled:
                return status
            time.sleep(poll_interval)
        raise RuntimeError(f"session {devin_id} did not settle within poll limit")

    def _assistant_content(self, devin_id: str) -> str:
        """Return the latest assistant message content from a session."""
        messages = self._get_messages(devin_id)
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                return str(msg.get("content") or "")
        return ""

    def search(self, query: str, max_results: int = 5, **kwargs: Any) -> list[SearchResult]:
        """Create a research session and return the answer as a SearchResult."""
        prompt = (
            f"Research the following topic and provide a comprehensive summary.\n\n"
            f"Topic: {query}\n\n"
            f"Please include key findings, relevant URLs, and sources."
        )
        session = self.create_session(prompt, title=f"UACP Research: {query}")
        devin_id = session.get("devin_id")
        if not devin_id:
            raise RuntimeError("Devin session creation did not return a devin_id")

        self._poll_until_settled(
            devin_id,
            max_polls=kwargs.get("max_polls", 60),
            poll_interval=kwargs.get("poll_interval", 5),
        )
        content = self._assistant_content(devin_id)
        return [
            SearchResult(
                title=f"Devin Research: {query}",
                url=session.get("url", f"https://app.devin.ai/sessions/{devin_id}"),
                content=content,
                snippet=content[:200],
                source="devin",
                timestamp=_iso_now(),
            ),
        ]

    def scrape(self, url: str, **kwargs: Any) -> ScrapeResult:
        """Create a session to analyze a URL and return markdown."""
        prompt = (
            f"Analyze the following URL and provide its content in clean markdown format.\n\n"
            f"URL: {url}\n\n"
            f"Include the page title, main content, and any relevant metadata."
        )
        session = self.create_session(prompt, title=f"UACP Scrape: {url}")
        devin_id = session.get("devin_id")
        if not devin_id:
            raise RuntimeError("Devin session creation did not return a devin_id")

        self._poll_until_settled(devin_id)
        content = self._assistant_content(devin_id)
        return ScrapeResult(
            url=url,
            markdown=content,
            metadata={"devin_session_id": devin_id, "devin_url": session.get("url", "")},
            source="devin",
        )

    def extract(self, url: str, schema: dict[str, Any] | None = None, **kwargs: Any) -> ExtractResult:
        """Create a session for structured extraction from a URL."""
        schema_hint = ""
        if schema:
            schema_hint = f"\n\nExtract the data according to this JSON schema:\n{json.dumps(schema, indent=2)}"
        prompt = (
            f"Extract structured data from the following URL.\n\n"
            f"URL: {url}"
            f"{schema_hint}\n\n"
            f"Return ONLY valid JSON matching the schema."
        )
        session = self.create_session(prompt, title=f"UACP Extract: {url}")
        devin_id = session.get("devin_id")
        if not devin_id:
            raise RuntimeError("Devin session creation did not return a devin_id")

        self._poll_until_settled(devin_id)
        content = self._assistant_content(devin_id)
        structured: dict[str, Any] = {}
        try:
            structured = json.loads(content)
        except Exception:
            pass
        return ExtractResult(
            url=url,
            structured_data=structured,
            raw_content=content,
            source="devin",
        )

    def crawl(self, url: str, limit: int = 10, **kwargs: Any) -> CrawlResult:
        """Create a session to discover URLs on a site."""
        prompt = (
            f"Explore the following website and list up to {limit} relevant URLs.\n\n"
            f"Start URL: {url}\n\n"
            f"Return the URLs as a bullet list, one per line."
        )
        session = self.create_session(prompt, title=f"UACP Crawl: {url}")
        devin_id = session.get("devin_id")
        if not devin_id:
            raise RuntimeError("Devin session creation did not return a devin_id")

        self._poll_until_settled(devin_id)
        content = self._assistant_content(devin_id)
        urls = _parse_url_list(content)
        return CrawlResult(
            urls_found=urls[:limit],
            pages=[{"url": u, "source": "devin"} for u in urls[:limit]],
            total=len(urls),
            completed=len(urls),
            source="devin",
        )

    def list_sessions(self, **filters: Any) -> list[dict[str, Any]]:
        """List Devin sessions for this organization."""
        url = self._org_url("/sessions")
        # Devin API uses cursor pagination; for simplicity fetch first page.
        resp = _http_json("GET", url, self._headers())
        return resp.get("sessions") or []

    def health_check(self) -> bool:
        """Probe by listing sessions."""
        try:
            self.list_sessions()
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Context7 backend
# ---------------------------------------------------------------------------

class Context7Backend(WebBackend):
    """Context7 documentation retrieval backend.

    Context7 fetches current, version-specific library documentation.
    Unlike web search, it retrieves structured doc snippets from indexed
    libraries (FastAPI, Next.js, React, etc.).

    Auth is optional — works without API key at lower rate limits.

    Docs: https://context7.com
    """

    DEFAULT_BASE_URL = "https://context7.com/api/v2"

    def __init__(self, api_key: str = "", base_url: str | None = None) -> None:
        # Context7 allows empty api_key (anonymous access).
        # Bypass the parent check by setting the attr directly.
        self.api_key = api_key
        self.base_url = base_url or self.DEFAULT_BASE_URL

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _resolve_library_meta(self, name: str) -> dict[str, Any]:
        """Resolve a library name and return the full API response."""
        url = f"{self.base_url}/resolve"
        params = {"libraryName": name}
        query = urllib.parse.urlencode(params)
        full_url = f"{url}?{query}"
        return _http_json("GET", full_url, self._headers())

    def resolve_library(self, name: str) -> str | None:
        """Convert a library name to a Context7-compatible library ID."""
        resp = self._resolve_library_meta(name)
        return resp.get("libraryId")

    def query_docs(
        self,
        library_id: str,
        query: str = "",
        tokens: int = 4000,
    ) -> list[dict[str, Any]]:
        """Fetch documentation snippets for a library."""
        url = f"{self.base_url}/context"
        params: dict[str, str] = {"libraryId": library_id}
        if query:
            params["query"] = query
        if tokens:
            params["tokens"] = str(tokens)
        query_str = urllib.parse.urlencode(params)
        full_url = f"{url}?{query_str}"
        resp = _http_json("GET", full_url, self._headers())
        return resp.get("snippets") or []

    def search(self, query: str, max_results: int = 5, **kwargs: Any) -> list[SearchResult]:
        """Resolve library from query and fetch documentation snippets.

        The query is expected to be of the form ``library_name topic``,
        e.g. "fastapi async endpoints".  The first word is used as the
        library name; the remainder is the doc topic.
        """
        parts = query.split(None, 1)
        library_name = parts[0] if parts else query
        topic = parts[1] if len(parts) > 1 else ""

        meta = self._resolve_library_meta(library_name)
        library_id = meta.get("libraryId")
        if not library_id:
            return []
        resolved_name = meta.get("libraryName") or library_name

        snippets = self.query_docs(
            library_id,
            query=topic,
            tokens=kwargs.get("tokens", 4000),
        )

        results: list[SearchResult] = []
        for snippet in snippets[:max_results]:
            results.append(
                SearchResult(
                    title=f"{resolved_name}: {snippet.get('title', 'Docs')}",
                    url=snippet.get("sourceUrl", ""),
                    content=f"{snippet.get('description', '')}\n\n{snippet.get('code', '')}".strip(),
                    snippet=snippet.get("description", ""),
                    source="context7",
                    timestamp=_iso_now(),
                )
            )
        return results

    def scrape(self, query: str, **kwargs: Any) -> ScrapeResult:
        """Fetch full documentation for a library as markdown."""
        parts = query.split(None, 1)
        library_name = parts[0] if parts else query
        topic = parts[1] if len(parts) > 1 else ""

        meta = self._resolve_library_meta(library_name)
        library_id = meta.get("libraryId")
        if not library_id:
            return ScrapeResult(url=query, markdown="", source="context7")
        resolved_name = meta.get("libraryName") or library_name

        snippets = self.query_docs(
            library_id,
            query=topic,
            tokens=kwargs.get("tokens", 8000),
        )

        lines: list[str] = []
        for s in snippets:
            lines.append(f"## {s.get('title', 'Untitled')}\n")
            if s.get("description"):
                lines.append(f"{s['description']}\n")
            if s.get("code"):
                lines.append(f"```\n{s['code']}\n```\n")
            lines.append(f"Source: {s.get('sourceUrl', '')}\n")

        return ScrapeResult(
            url=library_id,
            markdown="\n".join(lines),
            metadata={"library_id": library_id, "library_name": resolved_name, "snippet_count": len(snippets)},
            source="context7",
        )

    def extract(self, query: str, schema: dict[str, Any] | None = None, **kwargs: Any) -> ExtractResult:
        """Extract structured doc data for a library + topic."""
        parts = query.split(None, 1)
        library_name = parts[0] if parts else query
        topic = parts[1] if len(parts) > 1 else ""

        meta = self._resolve_library_meta(library_name)
        library_id = meta.get("libraryId")
        if not library_id:
            return ExtractResult(url=query, structured_data={}, source="context7")
        resolved_name = meta.get("libraryName") or library_name

        snippets = self.query_docs(
            library_id,
            query=topic,
            tokens=kwargs.get("tokens", 4000),
        )

        structured: dict[str, Any] = {
            "library": resolved_name,
            "library_id": library_id,
            "topic": topic,
            "snippets": snippets,
        }
        raw = json.dumps(structured, indent=2)
        return ExtractResult(
            url=library_id,
            structured_data=structured,
            raw_content=raw,
            source="context7",
        )

    def crawl(self, query: str, limit: int = 10, **kwargs: Any) -> CrawlResult:
        """List available libraries in Context7."""
        url = f"{self.base_url}/libraries"
        query_params: dict[str, str] = {}
        if query:
            query_params["search"] = query
        if query_params:
            full_url = f"{url}?{urllib.parse.urlencode(query_params)}"
        else:
            full_url = url
        resp = _http_json("GET", full_url, self._headers())
        libraries = resp.get("libraries") or []
        return CrawlResult(
            urls_found=[lib.get("libraryId", "") for lib in libraries[:limit]],
            pages=[{"library_id": lib.get("libraryId"), "name": lib.get("libraryName")} for lib in libraries[:limit]],
            total=len(libraries),
            completed=len(libraries),
            source="context7",
        )

    def health_check(self) -> bool:
        """Probe by resolving a well-known library."""
        try:
            self.resolve_library("fastapi")
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class BackendFactory:
    """Create a WebBackend by name."""

    _registry: dict[str, type[WebBackend]] = {
        "tavily": TavilyBackend,
        "firecrawl": FirecrawlBackend,
        "devin": DevinBackend,
        "context7": Context7Backend,
    }

    @classmethod
    def create(cls, name: str, api_key: str | None = None, **config: Any) -> WebBackend:
        """Instantiate a backend.

        *name* must be a registered backend key (see ``available_backends``).
        *api_key* is optional; if omitted the factory looks up the
        environment variable declared by the backend class.

        Devin-specific: pass ``org_id`` or set ``DEVIN_ORG_ID`` env var.
        Context7-specific: auth is optional; pass empty string for anonymous.
        """
        backend_cls = cls._registry.get(name)
        if backend_cls is None:
            raise ValueError(f"Unknown backend '{name}'. Available: {sorted(cls._registry)}")

        # Context7 allows empty api_key (anonymous access)
        if backend_cls is Context7Backend:
            if api_key is None:
                api_key = os.environ.get("CONTEXT7_API_KEY", "")
            base_url = config.get("base_url")
            return Context7Backend(api_key=api_key, base_url=base_url)

        if api_key is None:
            env_var = config.get("api_key_env") or cls._default_env_var(name)
            api_key = os.environ.get(env_var, "")

        if not api_key:
            raise ValueError(f"api_key is required for backend '{name}' (set {cls._default_env_var(name)} or pass api_key=)")

        base_url = config.get("base_url")

        # Devin requires org_id
        if backend_cls is DevinBackend:
            org_id = config.get("org_id") or os.environ.get("DEVIN_ORG_ID", "")
            if not org_id:
                raise ValueError("org_id is required for Devin backend (set DEVIN_ORG_ID or pass org_id=)")
            return DevinBackend(api_key=api_key, org_id=org_id, base_url=base_url)

        return backend_cls(api_key=api_key, base_url=base_url)

    @classmethod
    def available_backends(cls) -> list[str]:
        return sorted(cls._registry)

    @classmethod
    def register(cls, name: str, backend_cls: type[WebBackend]) -> None:
        cls._registry[name] = backend_cls

    @classmethod
    def _default_env_var(cls, name: str) -> str:
        return f"{name.upper()}_API_KEY"


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _parse_url_list(text: str) -> list[str]:
    """Extract URLs from a bullet-list or plain text response."""
    urls: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Strip common bullet markers
        for prefix in ("- ", "* ", "• ", "→ ", "> "):
            if line.startswith(prefix):
                line = line[len(prefix):]
                break
        line = line.strip()
        if line.startswith(("http://", "https://")):
            urls.append(line)
    return urls
