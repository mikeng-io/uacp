"""Unit tests for the UACP config resolver (skills/uacp-core/scripts/config.py)."""

from __future__ import annotations

import pytest
from config import UacpConfig, load_config


def test_loads_default():
    cfg = load_config(project_root=None)
    assert isinstance(cfg, UacpConfig)
    assert cfg.paths.base == ".uacp"
    assert cfg.paths.resolutions == "resolutions"


def test_project_override_deep_merges(tmp_path):
    (tmp_path / ".uacp").mkdir()
    (tmp_path / ".uacp" / "config.toml").write_text('[paths]\nbase = ".governed"\n')
    cfg = load_config(project_root=tmp_path)
    assert cfg.paths.base == ".governed"  # overridden
    assert (
        cfg.paths.proposals == "proposals"
    )  # default preserved (deep merge, not wholesale replace)


def test_missing_override_is_default_only(tmp_path):
    cfg = load_config(project_root=tmp_path)  # no .uacp/config.toml
    assert cfg.paths.base == ".uacp"


def test_resolve_phase_dir(tmp_path):
    cfg = load_config(project_root=tmp_path)
    p = cfg.resolve(tmp_path, "resolutions", "run-1-closure.yaml")
    assert p == tmp_path / ".uacp" / "resolutions" / "run-1-closure.yaml"


def test_resolve_rejects_traversal(tmp_path):
    cfg = load_config(project_root=tmp_path)
    with pytest.raises(ValueError):
        cfg.resolve(tmp_path, "state", "../../etc/passwd")
