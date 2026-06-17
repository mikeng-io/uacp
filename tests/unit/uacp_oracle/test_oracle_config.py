"""Tests for [oracle] config section in uacp.toml."""
from __future__ import annotations



def test_oracle_section_exists_in_default_config():
    """Default config/uacp.toml must have an [oracle] section."""
    from config import load_config
    cfg = load_config()
    oracle = cfg.model_extra.get("oracle")
    assert oracle is not None, "Expected [oracle] section in config/uacp.toml"


def test_oracle_disabled_by_default():
    """Oracle must be disabled in the default config (no ML deps by default)."""
    from config import load_config
    cfg = load_config()
    oracle = cfg.model_extra.get("oracle", {})
    assert oracle.get("enabled") is False


def test_oracle_has_embedding_section():
    from config import load_config
    cfg = load_config()
    oracle = cfg.model_extra.get("oracle", {})
    assert "embedding" in oracle


def test_oracle_has_honcho_section():
    from config import load_config
    cfg = load_config()
    oracle = cfg.model_extra.get("oracle", {})
    assert "honcho" in oracle


def test_project_override_can_enable_oracle(temp_uacp_root):
    """A project .uacp/config.toml override can enable oracle."""
    config_path = temp_uacp_root / ".uacp" / "config.toml"
    config_path.write_text('[oracle]\nenabled = true\n')

    from config import get_config
    cfg = get_config(temp_uacp_root)
    oracle = cfg.model_extra.get("oracle", {})
    assert oracle.get("enabled") is True


def test_project_override_can_set_honcho_url(temp_uacp_root):
    """A project override can set honcho URL via deep merge."""
    config_path = temp_uacp_root / ".uacp" / "config.toml"
    config_path.write_text('[oracle.honcho]\nenabled = true\nurl = "http://my-honcho:4000"\n')

    from config import get_config
    cfg = get_config(temp_uacp_root)
    oracle = cfg.model_extra.get("oracle", {})
    honcho = oracle.get("honcho", {})
    assert honcho.get("url") == "http://my-honcho:4000"
    assert honcho.get("enabled") is True
