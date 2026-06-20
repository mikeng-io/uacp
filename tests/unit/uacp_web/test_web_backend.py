"""TDD tests for uacp-web backend abstraction (Tavily + Firecrawl)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills" / "uacp-web" / "scripts"))

from web_backend import (
    BackendFactory,
    Context7Backend,
    CrawlResult,
    DevinBackend,
    ExtractResult,
    FirecrawlBackend,
    ScrapeResult,
    SearchResult,
    TavilyBackend,
    WebBackend,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(status: int, body: dict) -> MagicMock:
    """Build a mock urllib.response object."""
    mock = MagicMock()
    mock.getcode.return_value = status
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.read.return_value = json.dumps(body).encode("utf-8")
    return mock


# ---------------------------------------------------------------------------
# Schema / Data-model tests
# ---------------------------------------------------------------------------

class TestSearchResult:
    def test_valid_result(self):
        r = SearchResult(title="Test", url="https://example.com", content="hello")
        assert r.title == "Test"
        assert r.url == "https://example.com"
        assert r.content == "hello"
        assert r.source == "unknown"

    def test_defaults(self):
        r = SearchResult(title="T", url="https://x.com")
        assert r.relevance_score is None
        assert r.timestamp is None


class TestScrapeResult:
    def test_valid_result(self):
        r = ScrapeResult(url="https://example.com", markdown="# Hello", metadata={"title": "Ex"})
        assert r.markdown == "# Hello"
        assert r.metadata["title"] == "Ex"


class TestExtractResult:
    def test_valid_result(self):
        r = ExtractResult(url="https://example.com", structured_data={"name": "Ex"})
        assert r.structured_data["name"] == "Ex"


class TestCrawlResult:
    def test_valid_result(self):
        r = CrawlResult(
            urls_found=["https://a.com", "https://b.com"],
            pages=[{"url": "https://a.com", "markdown": "A"}],
        )
        assert len(r.urls_found) == 2
        assert r.pages[0]["markdown"] == "A"


# ---------------------------------------------------------------------------
# TavilyBackend tests
# ---------------------------------------------------------------------------

class TestTavilyBackend:
    def test_init_requires_api_key(self):
        with pytest.raises(ValueError, match="api_key"):
            TavilyBackend(api_key="")

    def test_search_success(self):
        backend = TavilyBackend(api_key="tvly-test")
        resp_body = {
            "results": [
                {"title": "T1", "url": "https://a.com", "content": "hello", "score": 0.9},
                {"title": "T2", "url": "https://b.com", "content": "world", "score": 0.8},
            ],
        }
        with patch("urllib.request.urlopen", return_value=_mock_response(200, resp_body)):
            results = backend.search("test query", max_results=2)
        assert len(results) == 2
        assert results[0].title == "T1"
        assert results[0].relevance_score == 0.9
        assert results[0].source == "tavily"

    def test_search_empty_results(self):
        backend = TavilyBackend(api_key="tvly-test")
        with patch("urllib.request.urlopen", return_value=_mock_response(200, {"results": []})):
            results = backend.search("no match")
        assert results == []

    def test_search_http_error(self):
        backend = TavilyBackend(api_key="tvly-test")
        with patch("urllib.request.urlopen", return_value=_mock_response(401, {"error": "unauthorized"})):
            with pytest.raises(RuntimeError):
                backend.search("test")

    def test_extract_success(self):
        backend = TavilyBackend(api_key="tvly-test")
        resp_body = {
            "results": {
                "raw_content": "extracted text",
                "images": ["https://img.com/a.png"],
            },
        }
        with patch("urllib.request.urlopen", return_value=_mock_response(200, resp_body)):
            result = backend.extract("https://example.com")
        assert result.url == "https://example.com"
        assert "extracted text" in result.raw_content
        assert result.source == "tavily"

    def test_health_check_success(self):
        backend = TavilyBackend(api_key="tvly-test")
        with patch("urllib.request.urlopen", return_value=_mock_response(200, {"results": []})):
            assert backend.health_check() is True

    def test_health_check_failure(self):
        backend = TavilyBackend(api_key="tvly-test")
        with patch("urllib.request.urlopen", side_effect=Exception("network error")):
            assert backend.health_check() is False


# ---------------------------------------------------------------------------
# FirecrawlBackend tests
# ---------------------------------------------------------------------------

class TestFirecrawlBackend:
    def test_init_requires_api_key(self):
        with pytest.raises(ValueError, match="api_key"):
            FirecrawlBackend(api_key="")

    def test_search_success(self):
        backend = FirecrawlBackend(api_key="fc-test")
        resp_body = {
            "success": True,
            "data": [
                {"url": "https://a.com", "title": "T1", "description": "desc"},
                {"url": "https://b.com", "title": "T2", "description": "desc2"},
            ],
        }
        with patch("urllib.request.urlopen", return_value=_mock_response(200, resp_body)):
            results = backend.search("test query")
        assert len(results) == 2
        assert results[0].title == "T1"
        assert results[0].source == "firecrawl"

    def test_scrape_success(self):
        backend = FirecrawlBackend(api_key="fc-test")
        resp_body = {
            "success": True,
            "data": {
                "markdown": "# Title\nContent",
                "metadata": {"title": "Title", "sourceURL": "https://example.com"},
            },
        }
        with patch("urllib.request.urlopen", return_value=_mock_response(200, resp_body)):
            result = backend.scrape("https://example.com")
        assert result.markdown == "# Title\nContent"
        assert result.url == "https://example.com"
        assert result.metadata["title"] == "Title"

    def test_crawl_success(self):
        backend = FirecrawlBackend(api_key="fc-test")
        resp_body = {
            "success": True,
            "id": "job-123",
            "url": "https://api.firecrawl.dev/v1/crawl/job-123",
        }
        status_body = {
            "status": "completed",
            "total": 2,
            "completed": 2,
            "data": [
                {"markdown": "# A", "metadata": {"sourceURL": "https://a.com"}},
                {"markdown": "# B", "metadata": {"sourceURL": "https://b.com"}},
            ],
        }
        call_count = 0

        def _side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _mock_response(200, resp_body)
            return _mock_response(200, status_body)

        with patch("urllib.request.urlopen", side_effect=_side_effect):
            result = backend.crawl("https://example.com", limit=10)
        assert len(result.pages) == 2
        assert result.urls_found == ["https://a.com", "https://b.com"]

    def test_extract_success(self):
        backend = FirecrawlBackend(api_key="fc-test")
        resp_body = {
            "success": True,
            "data": {
                "extract": {"founders": [{"name": "Alice", "role": "CEO"}]},
            },
        }
        with patch("urllib.request.urlopen", return_value=_mock_response(200, resp_body)):
            result = backend.extract(
                "https://example.com",
                schema={"type": "object", "properties": {"founders": {"type": "array"}}},
            )
        assert result.structured_data["founders"][0]["name"] == "Alice"

    def test_health_check_success(self):
        backend = FirecrawlBackend(api_key="fc-test")
        with patch("urllib.request.urlopen", return_value=_mock_response(200, {"success": True})):
            assert backend.health_check() is True

    def test_health_check_failure(self):
        backend = FirecrawlBackend(api_key="fc-test")
        with patch("urllib.request.urlopen", side_effect=Exception("timeout")):
            assert backend.health_check() is False


# ---------------------------------------------------------------------------
# BackendFactory tests
# ---------------------------------------------------------------------------

class TestBackendFactory:
    def test_create_tavily(self):
        backend = BackendFactory.create("tavily", api_key="tvly-test")
        assert isinstance(backend, TavilyBackend)

    def test_create_firecrawl(self):
        backend = BackendFactory.create("firecrawl", api_key="fc-test")
        assert isinstance(backend, FirecrawlBackend)

    def test_create_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown backend"):
            BackendFactory.create("unknown", api_key="x")

    def test_create_from_env_tavily(self):
        with patch.dict("os.environ", {"TAVILY_API_KEY": "tvly-env"}):
            backend = BackendFactory.create("tavily")
        assert isinstance(backend, TavilyBackend)

    def test_create_from_env_firecrawl(self):
        with patch.dict("os.environ", {"FIRECRAWL_API_KEY": "fc-env"}):
            backend = BackendFactory.create("firecrawl")
        assert isinstance(backend, FirecrawlBackend)

    def test_create_missing_key_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="api_key"):
                BackendFactory.create("tavily")

    def test_create_devin(self):
        backend = BackendFactory.create("devin", api_key="cog-test", org_id="org-test")
        assert isinstance(backend, DevinBackend)

    def test_create_devin_from_env(self):
        with patch.dict("os.environ", {"DEVIN_API_KEY": "cog-env", "DEVIN_ORG_ID": "org-env"}):
            backend = BackendFactory.create("devin")
        assert isinstance(backend, DevinBackend)

    def test_available_backends(self):
        names = BackendFactory.available_backends()
        assert "tavily" in names
        assert "firecrawl" in names
        assert "devin" in names


# ---------------------------------------------------------------------------
# Unified interface / protocol tests
# ---------------------------------------------------------------------------

class TestUnifiedInterface:
    """Both backends implement the same protocol."""

    @pytest.mark.parametrize("backend", [
        TavilyBackend(api_key="tvly-test"),
        FirecrawlBackend(api_key="fc-test"),
    ])
    def test_all_have_search(self, backend: WebBackend):
        assert hasattr(backend, "search")

    @pytest.mark.parametrize("backend", [
        TavilyBackend(api_key="tvly-test"),
        FirecrawlBackend(api_key="fc-test"),
    ])
    def test_all_have_extract(self, backend: WebBackend):
        assert hasattr(backend, "extract")

    @pytest.mark.parametrize("backend", [
        TavilyBackend(api_key="tvly-test"),
        FirecrawlBackend(api_key="fc-test"),
    ])
    def test_all_have_health_check(self, backend: WebBackend):
        assert hasattr(backend, "health_check")

    def test_firecrawl_has_scrape_and_crawl(self):
        backend = FirecrawlBackend(api_key="fc-test")
        assert hasattr(backend, "scrape")
        assert hasattr(backend, "crawl")



# ---------------------------------------------------------------------------
# DevinBackend tests
# ---------------------------------------------------------------------------

class TestDevinBackend:
    def test_init_requires_api_key(self):
        with pytest.raises(ValueError, match="api_key"):
            DevinBackend(api_key="", org_id="org-test")

    def test_init_requires_org_id(self):
        with pytest.raises(ValueError, match="org_id"):
            DevinBackend(api_key="cog-test", org_id="")

    def test_search_creates_session_and_polls(self):
        backend = DevinBackend(api_key="cog-test", org_id="org-test")

        create_resp = {
            "devin_id": "devin-123",
            "status": "running",
            "url": "https://app.devin.ai/sessions/devin-123",
        }
        status_running = {"devin_id": "devin-123", "status": "running"}
        status_settled = {"devin_id": "devin-123", "status": "stopped"}
        messages_resp = {
            "messages": [
                {"role": "assistant", "content": "Python async best practices include using asyncio.gather for concurrent tasks."},
            ],
        }

        call_order = []
        def _side_effect(req, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else req
            call_order.append(url)
            if "sessions" in url and url.endswith("/sessions"):
                return _mock_response(200, create_resp)
            if "devin-123/messages" in url:
                return _mock_response(200, messages_resp)
            # Status polling
            if "devin-123" in url:
                if sum("devin-123" in c for c in call_order) < 3:
                    return _mock_response(200, status_running)
                return _mock_response(200, status_settled)
            return _mock_response(200, {})

        with patch("urllib.request.urlopen", side_effect=_side_effect):
            with patch("time.sleep"):  # skip poll delays
                results = backend.search("Python async best practices", max_results=1)

        assert len(results) == 1
        assert results[0].title == "Devin Research: Python async best practices"
        assert "asyncio.gather" in results[0].content
        assert results[0].source == "devin"

    def test_search_empty_messages(self):
        backend = DevinBackend(api_key="cog-test", org_id="org-test")
        create_resp = {"devin_id": "devin-456", "status": "stopped"}
        status_resp = {"devin_id": "devin-456", "status": "stopped"}
        messages_resp = {"messages": []}

        def _side_effect(req, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else req
            if url.endswith("/sessions"):
                return _mock_response(200, create_resp)
            if "messages" in url:
                return _mock_response(200, messages_resp)
            return _mock_response(200, status_resp)

        with patch("urllib.request.urlopen", side_effect=_side_effect):
            with patch("time.sleep"):
                results = backend.search("test query")

        assert len(results) == 1
        assert results[0].content == ""

    def test_extract_via_session(self):
        backend = DevinBackend(api_key="cog-test", org_id="org-test")
        create_resp = {"devin_id": "devin-789", "status": "stopped"}
        status_resp = {"devin_id": "devin-789", "status": "stopped"}
        messages_resp = {
            "messages": [
                {"role": "assistant", "content": '{"founders": [{"name": "Alice", "role": "CEO"}]}'},
            ],
        }

        def _side_effect(req, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else req
            if url.endswith("/sessions"):
                return _mock_response(200, create_resp)
            if "messages" in url:
                return _mock_response(200, messages_resp)
            return _mock_response(200, status_resp)

        with patch("urllib.request.urlopen", side_effect=_side_effect):
            with patch("time.sleep"):
                result = backend.extract(
                    "https://example.com",
                    schema={"type": "object", "properties": {"founders": {"type": "array"}}},
                )

        assert result.structured_data["founders"][0]["name"] == "Alice"
        assert result.source == "devin"

    def test_scrape_via_session(self):
        backend = DevinBackend(api_key="cog-test", org_id="org-test")
        create_resp = {"devin_id": "devin-abc", "status": "stopped"}
        status_resp = {"devin_id": "devin-abc", "status": "stopped"}
        messages_resp = {
            "messages": [
                {"role": "assistant", "content": "# Title\n\nPage content here."},
            ],
        }

        def _side_effect(req, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else req
            if url.endswith("/sessions"):
                return _mock_response(200, create_resp)
            if "messages" in url:
                return _mock_response(200, messages_resp)
            return _mock_response(200, status_resp)

        with patch("urllib.request.urlopen", side_effect=_side_effect):
            with patch("time.sleep"):
                result = backend.scrape("https://example.com")

        assert result.markdown == "# Title\n\nPage content here."
        assert result.url == "https://example.com"
        assert result.source == "devin"

    def test_crawl_via_session(self):
        backend = DevinBackend(api_key="cog-test", org_id="org-test")
        create_resp = {"devin_id": "devin-def", "status": "stopped"}
        status_resp = {"devin_id": "devin-def", "status": "stopped"}
        messages_resp = {
            "messages": [
                {"role": "assistant", "content": "Found URLs:\n- https://a.com\n- https://b.com\n- https://c.com"},
            ],
        }

        def _side_effect(req, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else req
            if url.endswith("/sessions"):
                return _mock_response(200, create_resp)
            if "messages" in url:
                return _mock_response(200, messages_resp)
            return _mock_response(200, status_resp)

        with patch("urllib.request.urlopen", side_effect=_side_effect):
            with patch("time.sleep"):
                result = backend.crawl("https://example.com", limit=3)

        assert len(result.urls_found) == 3
        assert "https://a.com" in result.urls_found
        assert result.source == "devin"

    def test_create_session_direct(self):
        backend = DevinBackend(api_key="cog-test", org_id="org-test")
        create_resp = {"devin_id": "devin-xyz", "status": "running"}

        with patch("urllib.request.urlopen", return_value=_mock_response(200, create_resp)):
            session = backend.create_session("Implement feature X")

        assert session["devin_id"] == "devin-xyz"
        assert session["status"] == "running"

    def test_health_check_success(self):
        backend = DevinBackend(api_key="cog-test", org_id="org-test")
        with patch("urllib.request.urlopen", return_value=_mock_response(200, {"devin_id": "h-1", "status": "stopped"})):
            assert backend.health_check() is True

    def test_health_check_failure(self):
        backend = DevinBackend(api_key="cog-test", org_id="org-test")
        with patch("urllib.request.urlopen", side_effect=Exception("timeout")):
            assert backend.health_check() is False

    def test_list_sessions(self):
        backend = DevinBackend(api_key="cog-test", org_id="org-test")
        resp = {
            "sessions": [
                {"devin_id": "s1", "status": "stopped", "prompt": "Task 1"},
                {"devin_id": "s2", "status": "running", "prompt": "Task 2"},
            ],
        }
        with patch("urllib.request.urlopen", return_value=_mock_response(200, resp)):
            sessions = backend.list_sessions()
        assert len(sessions) == 2
        assert sessions[0]["devin_id"] == "s1"


# ---------------------------------------------------------------------------
# Updated unified interface tests
# ---------------------------------------------------------------------------

class TestUnifiedInterfaceAllBackends:
    """All three backends implement the same protocol."""

    @pytest.mark.parametrize("backend", [
        TavilyBackend(api_key="tvly-test"),
        FirecrawlBackend(api_key="fc-test"),
        DevinBackend(api_key="cog-test", org_id="org-test"),
    ])
    def test_all_have_search(self, backend: WebBackend):
        assert hasattr(backend, "search")

    @pytest.mark.parametrize("backend", [
        TavilyBackend(api_key="tvly-test"),
        FirecrawlBackend(api_key="fc-test"),
        DevinBackend(api_key="cog-test", org_id="org-test"),
    ])
    def test_all_have_extract(self, backend: WebBackend):
        assert hasattr(backend, "extract")

    @pytest.mark.parametrize("backend", [
        TavilyBackend(api_key="tvly-test"),
        FirecrawlBackend(api_key="fc-test"),
        DevinBackend(api_key="cog-test", org_id="org-test"),
    ])
    def test_all_have_health_check(self, backend: WebBackend):
        assert hasattr(backend, "health_check")



# ---------------------------------------------------------------------------
# Context7Backend tests
# ---------------------------------------------------------------------------

class TestContext7Backend:
    def test_init_allows_empty_api_key(self):
        # Context7 auth is optional
        backend = Context7Backend(api_key="")
        assert backend.api_key == ""

    def test_resolve_library_success(self):
        backend = Context7Backend(api_key="ctx7sk-test")
        resp_body = {
            "libraryId": "/tiangolo/fastapi",
            "libraryName": "FastAPI",
            "libraryUrl": "https://github.com/tiangolo/fastapi",
        }
        with patch("urllib.request.urlopen", return_value=_mock_response(200, resp_body)):
            lib_id = backend.resolve_library("fastapi")
        assert lib_id == "/tiangolo/fastapi"

    def test_resolve_library_not_found(self):
        backend = Context7Backend(api_key="ctx7sk-test")
        with patch("urllib.request.urlopen", return_value=_mock_response(200, {})):
            lib_id = backend.resolve_library("nonexistent-lib")
        assert lib_id is None

    def test_query_docs_success(self):
        backend = Context7Backend(api_key="ctx7sk-test")
        resp_body = {
            "snippets": [
                {
                    "title": "Async Endpoints",
                    "description": "Using async def in FastAPI endpoints",
                    "code": "@app.get('/items')\nasync def read_items(): ...",
                    "sourceUrl": "https://fastapi.tiangolo.com/async/",
                },
                {
                    "title": "Dependency Injection",
                    "description": "FastAPI dependency injection system",
                    "code": "async def common_parameters(q: str | None = None): ...",
                    "sourceUrl": "https://fastapi.tiangolo.com/tutorial/dependencies/",
                },
            ],
        }
        with patch("urllib.request.urlopen", return_value=_mock_response(200, resp_body)):
            snippets = backend.query_docs("/tiangolo/fastapi", "async endpoints", tokens=2000)
        assert len(snippets) == 2
        assert snippets[0]["title"] == "Async Endpoints"

    def test_search_resolves_and_queries(self):
        backend = Context7Backend(api_key="ctx7sk-test")

        resolve_resp = {
            "libraryId": "/tiangolo/fastapi",
            "libraryName": "FastAPI",
        }
        docs_resp = {
            "snippets": [
                {
                    "title": "Getting Started",
                    "description": "FastAPI quick start guide",
                    "code": "from fastapi import FastAPI\napp = FastAPI()",
                    "sourceUrl": "https://fastapi.tiangolo.com/",
                },
            ],
        }

        call_count = 0
        def _side_effect(req, **kwargs):
            nonlocal call_count
            call_count += 1
            url = req.full_url if hasattr(req, "full_url") else req
            if "resolve" in url:
                return _mock_response(200, resolve_resp)
            return _mock_response(200, docs_resp)

        with patch("urllib.request.urlopen", side_effect=_side_effect):
            results = backend.search("fastapi getting started")

        assert len(results) == 1
        assert results[0].title == "FastAPI: Getting Started"
        assert "FastAPI quick start guide" in results[0].content
        assert results[0].source == "context7"
        assert results[0].url == "https://fastapi.tiangolo.com/"

    def test_search_library_not_found(self):
        backend = Context7Backend(api_key="ctx7sk-test")
        with patch("urllib.request.urlopen", return_value=_mock_response(200, {})):
            results = backend.search("nonexistent-library query")
        assert results == []

    def test_extract_with_topic(self):
        backend = Context7Backend(api_key="ctx7sk-test")
        resolve_resp = {"libraryId": "/vercel/nextjs", "libraryName": "Next.js"}
        docs_resp = {
            "snippets": [
                {
                    "title": "Middleware",
                    "description": "Next.js middleware docs",
                    "code": "export function middleware(request) { ... }",
                    "sourceUrl": "https://nextjs.org/docs/app/building-your-application/routing/middleware",
                },
            ],
        }

        def _side_effect(req, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else req
            if "resolve" in url:
                return _mock_response(200, resolve_resp)
            return _mock_response(200, docs_resp)

        with patch("urllib.request.urlopen", side_effect=_side_effect):
            result = backend.extract("nextjs middleware", schema={"type": "object"})

        assert result.structured_data["library"] == "Next.js"
        assert result.structured_data["topic"] == "middleware"
        assert len(result.structured_data["snippets"]) == 1
        assert result.source == "context7"

    def test_scrape_fetches_full_docs(self):
        backend = Context7Backend(api_key="ctx7sk-test")
        resolve_resp = {"libraryId": "/python/cpython", "libraryName": "Python"}
        docs_resp = {
            "snippets": [
                {"title": "T1", "description": "D1", "code": "code1", "sourceUrl": "https://docs.python.org/3/"},
                {"title": "T2", "description": "D2", "code": "code2", "sourceUrl": "https://docs.python.org/3/"},
            ],
        }

        def _side_effect(req, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else req
            if "resolve" in url:
                return _mock_response(200, resolve_resp)
            return _mock_response(200, docs_resp)

        with patch("urllib.request.urlopen", side_effect=_side_effect):
            result = backend.scrape("python asyncio documentation")

        assert "T1" in result.markdown
        assert "code1" in result.markdown
        assert result.source == "context7"

    def test_crawl_lists_libraries(self):
        backend = Context7Backend(api_key="ctx7sk-test")
        resp_body = {
            "libraries": [
                {"libraryId": "/tiangolo/fastapi", "libraryName": "FastAPI"},
                {"libraryId": "/vercel/nextjs", "libraryName": "Next.js"},
                {"libraryId": "/python/cpython", "libraryName": "Python"},
            ],
        }
        with patch("urllib.request.urlopen", return_value=_mock_response(200, resp_body)):
            result = backend.crawl("popular libraries", limit=10)
        assert len(result.urls_found) == 3
        assert "/tiangolo/fastapi" in result.urls_found
        assert result.source == "context7"

    def test_health_check_success(self):
        backend = Context7Backend(api_key="ctx7sk-test")
        with patch("urllib.request.urlopen", return_value=_mock_response(200, {"libraryId": "test"})):
            assert backend.health_check() is True

    def test_health_check_failure(self):
        backend = Context7Backend(api_key="ctx7sk-test")
        with patch("urllib.request.urlopen", side_effect=Exception("timeout")):
            assert backend.health_check() is False


# ---------------------------------------------------------------------------
# Updated BackendFactory tests for Context7
# ---------------------------------------------------------------------------

class TestBackendFactoryContext7:
    def test_create_context7(self):
        backend = BackendFactory.create("context7", api_key="ctx7sk-test")
        assert isinstance(backend, Context7Backend)

    def test_create_context7_from_env(self):
        with patch.dict("os.environ", {"CONTEXT7_API_KEY": "ctx7sk-env"}):
            backend = BackendFactory.create("context7")
        assert isinstance(backend, Context7Backend)
        assert backend.api_key == "ctx7sk-env"

    def test_create_context7_no_key_ok(self):
        # Context7 works without auth (lower rate limits)
        with patch.dict("os.environ", {}, clear=True):
            backend = BackendFactory.create("context7", api_key="")
        assert isinstance(backend, Context7Backend)

    def test_available_backends_includes_context7(self):
        names = BackendFactory.available_backends()
        assert "context7" in names


# ---------------------------------------------------------------------------
# Updated unified interface tests (all 4 backends)
# ---------------------------------------------------------------------------

class TestUnifiedInterfaceFourBackends:
    """All four backends implement the same protocol."""

    @pytest.mark.parametrize("backend", [
        TavilyBackend(api_key="tvly-test"),
        FirecrawlBackend(api_key="fc-test"),
        DevinBackend(api_key="cog-test", org_id="org-test"),
        Context7Backend(api_key="ctx7sk-test"),
    ])
    def test_all_have_search(self, backend: WebBackend):
        assert hasattr(backend, "search")

    @pytest.mark.parametrize("backend", [
        TavilyBackend(api_key="tvly-test"),
        FirecrawlBackend(api_key="fc-test"),
        DevinBackend(api_key="cog-test", org_id="org-test"),
        Context7Backend(api_key="ctx7sk-test"),
    ])
    def test_all_have_extract(self, backend: WebBackend):
        assert hasattr(backend, "extract")

    @pytest.mark.parametrize("backend", [
        TavilyBackend(api_key="tvly-test"),
        FirecrawlBackend(api_key="fc-test"),
        DevinBackend(api_key="cog-test", org_id="org-test"),
        Context7Backend(api_key="ctx7sk-test"),
    ])
    def test_all_have_health_check(self, backend: WebBackend):
        assert hasattr(backend, "health_check")
