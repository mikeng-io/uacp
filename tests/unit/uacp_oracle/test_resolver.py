"""Tests for oracle.serving resolver."""
from __future__ import annotations


from engines.oracle.serving import resolve_serving_url


def test_url_override_wins_over_config(temp_uacp_root):
    url = resolve_serving_url(temp_uacp_root, "embedding", url_override="http://custom:8080")
    assert url == "http://custom:8080"


def test_returns_empty_when_not_configured(temp_uacp_root):
    url = resolve_serving_url(temp_uacp_root, "embedding")
    assert url == ""


def test_reads_url_from_config(temp_uacp_root):
    config_path = temp_uacp_root / ".uacp" / "config.toml"
    config_path.write_text('[oracle.embedding]\nurl = "http://embed:9000"\n')
    url = resolve_serving_url(temp_uacp_root, "embedding")
    assert url == "http://embed:9000"


def test_unknown_role_returns_empty(temp_uacp_root):
    url = resolve_serving_url(temp_uacp_root, "unknown_service")
    assert url == ""


def test_explicit_empty_override_falls_through_to_config(temp_uacp_root):
    # url_override="" is falsy, so it falls through
    config_path = temp_uacp_root / ".uacp" / "config.toml"
    config_path.write_text('[oracle.honcho]\nurl = "http://honcho:4000"\n')
    url = resolve_serving_url(temp_uacp_root, "honcho", url_override="")
    assert url == "http://honcho:4000"
