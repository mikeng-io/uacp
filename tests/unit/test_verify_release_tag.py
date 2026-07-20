"""Unit tests for scripts/verify_release_tag.py — the release-tag / manifest version guard.

Regression anchor: a real release-pipeline run rejected the pre-release tag ``v0.1.0-rc.1`` against
a repo at ``0.1.0`` because the old inline check compared the full ``0.1.0-rc.1`` string. The guard
must compare the semver RELEASE CORE, so a pre-release tag matches its base version.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "verify_release_tag", ROOT / "scripts" / "verify_release_tag.py"
)
assert _spec and _spec.loader
vrt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vrt)


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("v0.2.0", "0.2.0"),
        ("0.2.0", "0.2.0"),
        ("v0.2.0-rc.1", "0.2.0"),  # the bug: pre-release core is the base version
        ("v0.2.0-alpha.3", "0.2.0"),
        ("v1.2.3+build.7", "1.2.3"),  # build metadata stripped too
        ("v1.2.3-rc.1+build.7", "1.2.3"),
        ("v10.20.30", "10.20.30"),
    ],
)
def test_release_core(version: str, expected: str) -> None:
    assert vrt.release_core(version) == expected


def _write_manifests(root: Path, version: str) -> None:
    (root / "pyproject.toml").write_text(f'[project]\nname = "uacp"\nversion = "{version}"\n')
    (root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (root / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": version}))
    (root / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps({"plugins": [{"version": version}]})
    )


def test_stable_tag_matches(monkeypatch, tmp_path) -> None:
    _write_manifests(tmp_path, "0.2.0")
    monkeypatch.setattr(vrt, "ROOT", tmp_path)
    ok, msgs = vrt.verify("v0.2.0")
    assert ok, msgs
    assert msgs[0].startswith("OK:")


def test_prerelease_tag_matches_base_version(monkeypatch, tmp_path) -> None:
    """THE regression: v0.2.0-rc.1 against a 0.2.0 repo must PASS (it used to fail)."""
    _write_manifests(tmp_path, "0.2.0")
    monkeypatch.setattr(vrt, "ROOT", tmp_path)
    ok, msgs = vrt.verify("v0.2.0-rc.1")
    assert ok, msgs


def test_wrong_version_tag_is_blocked(monkeypatch, tmp_path) -> None:
    _write_manifests(tmp_path, "0.2.0")
    monkeypatch.setattr(vrt, "ROOT", tmp_path)
    ok, msgs = vrt.verify("v0.9.9")
    assert not ok
    assert any("Version mismatch" in m for m in msgs)


def test_manifest_drift_is_blocked(monkeypatch, tmp_path) -> None:
    """A partial bump (pyproject moved, plugin.json didn't) must be caught."""
    _write_manifests(tmp_path, "0.2.0")
    (tmp_path / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": "0.1.0"}))
    monkeypatch.setattr(vrt, "ROOT", tmp_path)
    ok, msgs = vrt.verify("v0.2.0")
    assert not ok
    assert any("Manifest drift" in m and "plugin.json" in m for m in msgs)


def test_prerelease_still_catches_drift(monkeypatch, tmp_path) -> None:
    """Stripping the suffix must not weaken the drift check for pre-release tags."""
    _write_manifests(tmp_path, "0.2.0")
    (tmp_path / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps({"plugins": [{"version": "0.1.0"}]})
    )
    monkeypatch.setattr(vrt, "ROOT", tmp_path)
    ok, msgs = vrt.verify("v0.2.0-rc.1")
    assert not ok
    assert any("marketplace.json" in m for m in msgs)
