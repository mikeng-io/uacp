"""Tests for the Oracle query expansion helper (Task 8a — expansion stub)."""
from __future__ import annotations

from engines.oracle.expansion import expand_query
from engines.oracle.serving import RoleServing, ServingMode


def test_floor_mode_returns_raw_query_only() -> None:
    """FLOOR serving -> no expansion model -> raw query passthrough."""
    result = expand_query("auth bug", RoleServing("query_expansion", ServingMode.FLOOR))
    assert result == ["auth bug"]


def test_disabled_via_enabled_false_returns_raw() -> None:
    """enabled=False kwarg gates the expansion regardless of mode."""
    result = expand_query(
        "auth bug",
        RoleServing("query_expansion", ServingMode.EMBEDDED),
        enabled=False,
    )
    assert result == ["auth bug"]


def test_url_mode_without_client_falls_back_to_raw(monkeypatch) -> None:
    """URL mode with no reachable endpoint degrades to raw query (never raises)."""
    import engines.oracle.expansion as ex

    monkeypatch.setattr(ex, "_try_expand_url", lambda *a, **k: None)
    result = expand_query(
        "auth bug",
        RoleServing("query_expansion", ServingMode.URL, url="http://x/chat"),
        enabled=True,
    )
    assert "auth bug" in result


def test_embedded_mode_without_binding_falls_back_to_raw(monkeypatch) -> None:
    """EMBEDDED mode with absent binding degrades to raw query (never raises)."""
    import engines.oracle.expansion as ex

    monkeypatch.setattr(ex, "_try_expand_embedded", lambda *a, **k: None)
    result = expand_query(
        "auth bug",
        RoleServing("query_expansion", ServingMode.EMBEDDED, model="m"),
        enabled=True,
    )
    assert "auth bug" in result


def test_result_always_contains_original_query() -> None:
    """Original query is always in the result list regardless of expansion outcome."""
    result = expand_query("anything", RoleServing("query_expansion", ServingMode.FLOOR))
    assert "anything" in result
