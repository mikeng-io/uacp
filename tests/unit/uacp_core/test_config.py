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
    # Override a single leaf inside a NESTED table ([council.roles]) that is NOT a
    # Paths field, so there is no Pydantic inline default to silently backfill a
    # dropped sibling. With a shallow {**base, **override} merge the whole `council`
    # table (and its `roles` subtable) would be wholesale-replaced by the override's
    # single leaf, dropping every sibling. Deep merge preserves them. This is what
    # gives the test teeth: assertion (b) below fails under a shallow merge.
    (tmp_path / ".uacp").mkdir()
    (tmp_path / ".uacp" / "config.toml").write_text(
        '[paths]\nbase = ".governed"\n[council.roles]\ndevils_advocate = false\n'
    )
    cfg = load_config(project_root=tmp_path)

    # (a) overridden leaves changed
    assert cfg.paths.base == ".governed"
    assert cfg.council["roles"]["devils_advocate"] is False

    # (b) sibling leaves in the overridden nested tables survive (deep merge, not
    # wholesale replace). A shallow merge would drop all of these.
    assert cfg.council["roles"]["integration_checker"] is True  # sibling in [council.roles]
    assert cfg.council["roles"]["domain_expert"] is True  # sibling in [council.roles]
    assert cfg.council["mode"] == "adaptive"  # sibling table under [council]
    assert cfg.council["debate"]["max_rounds_thorough"] == 3  # sibling subtable under [council]


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
