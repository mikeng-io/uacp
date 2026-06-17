"""Tests for the Honcho memory source."""
from __future__ import annotations

from unittest.mock import MagicMock


from engines.oracle.sources.honcho import query_honcho, packets_from_honcho
from engines.oracle.packets import TrustClass


def test_query_honcho_returns_empty_when_no_url():
    result = query_honcho(url="", project="proj", phase="plan")
    assert result == []


def test_query_honcho_returns_empty_when_httpx_unavailable(monkeypatch):
    monkeypatch.setattr("engines.oracle.sources.honcho._httpx_client", lambda *a, **k: None)
    result = query_honcho(url="http://honcho:4000", project="proj", phase="plan")
    assert result == []


def test_query_honcho_returns_list_on_success(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.json.return_value = [{"id": "1", "content": "prior art", "score": 0.9}]
    mock_resp.raise_for_status.return_value = None

    mock_client_instance = MagicMock()
    mock_client_instance.__enter__ = lambda s: s
    mock_client_instance.__exit__ = MagicMock(return_value=False)
    mock_client_instance.get.return_value = mock_resp

    monkeypatch.setattr("engines.oracle.sources.honcho._httpx_client", lambda *a, **k: mock_client_instance)

    result = query_honcho(url="http://honcho:4000", project="proj", phase="plan")
    assert result == [{"id": "1", "content": "prior art", "score": 0.9}]


def test_query_honcho_returns_empty_on_http_error(monkeypatch):
    mock_client_instance = MagicMock()
    mock_client_instance.__enter__ = lambda s: s
    mock_client_instance.__exit__ = MagicMock(return_value=False)
    mock_client_instance.get.side_effect = OSError("connection refused")

    monkeypatch.setattr("engines.oracle.sources.honcho._httpx_client", lambda *a, **k: mock_client_instance)

    result = query_honcho(url="http://honcho:4000", project="proj", phase="plan")
    assert result == []


def test_packets_from_honcho_trust_class_is_advisory(monkeypatch):
    monkeypatch.setattr(
        "engines.oracle.sources.honcho.query_honcho",
        lambda **k: [{"id": "1", "content": "text", "score": 0.8}],
    )
    packets = packets_from_honcho(url="http://h:4000", project="p", phase="plan")
    assert len(packets) == 1
    assert packets[0].trust_class == TrustClass.advisory
    assert packets[0].evidence_required is True
    assert packets[0].source == "honcho"
