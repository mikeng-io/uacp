"""Tests for the per-role serving resolver: url override > embedded > floor.

Extends serving.py (the existing resolve_serving_url stays). resolve_role honors
the [oracle] config for each role (embedding/rerank): enabled=false
forces FLOOR; a non-empty url -> URL; else embedded if the binding is present,
else FLOOR. Per role it is exactly one mode, never both.
"""
from __future__ import annotations

import pytest

from engines.oracle.serving import RoleServing, ServingMode, resolve_role


def _cfg(**roles):
    return {"enabled": True, "store": "lancedb", **roles}


@pytest.mark.parametrize("role", ["embedding", "rerank"])
def test_floor_when_oracle_disabled(role):
    cfg = {"enabled": False, role: {"model": "m", "url": "http://x"}}
    r = resolve_role(role, cfg, deps_present=True)
    assert r.mode is ServingMode.FLOOR


@pytest.mark.parametrize("role", ["embedding", "rerank"])
def test_url_override_wins(role):
    cfg = _cfg(**{role: {"model": "m", "url": "http://localhost:8000/v1/x"}})
    r = resolve_role(role, cfg, deps_present=True)
    assert r.mode is ServingMode.URL
    assert r.url == "http://localhost:8000/v1/x"
    assert r.model == "m"


@pytest.mark.parametrize("role", ["embedding", "rerank"])
def test_embedded_when_no_url_and_deps_present(role):
    cfg = _cfg(**{role: {"model": "bge-m3", "url": ""}})
    r = resolve_role(role, cfg, deps_present=True)
    assert r.mode is ServingMode.EMBEDDED
    assert r.model == "bge-m3"


@pytest.mark.parametrize("role", ["embedding", "rerank"])
def test_floor_when_no_url_and_deps_absent(role):
    cfg = _cfg(**{role: {"model": "bge-m3", "url": ""}})
    r = resolve_role(role, cfg, deps_present=False)
    assert r.mode is ServingMode.FLOOR


def test_never_both_url_and_embedded():
    cfg = _cfg(rerank={"model": "qwen3-reranker-0.6b", "url": "http://x/v1/rerank"})
    r = resolve_role("rerank", cfg, deps_present=True)
    assert r.mode is ServingMode.URL


def test_resolve_role_returns_roleserving_dataclass():
    cfg = _cfg(embedding={"model": "bge-m3", "url": ""})
    r = resolve_role("embedding", cfg, deps_present=False)
    assert isinstance(r, RoleServing)
    assert r.role == "embedding"
