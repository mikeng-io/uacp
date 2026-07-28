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


@pytest.mark.parametrize(
    ("manifest", "tag", "expected"),
    [
        ("0.2.0", "v0.2.0", True),  # stable == stable
        ("0.2.0", "v0.2.0-rc.1", True),  # manifest at stable base, tag is a prerelease of it
        ("0.2.0-rc.1", "v0.2.0-rc.1", True),  # manifest declares the exact prerelease
        ("0.2.0-rc.1", "v0.2.0-rc.2", False),  # THE Codex P1: rc.1 metadata under an rc.2 tag
        ("0.2.0-rc.2", "v0.2.0-rc.1", False),  # and the reverse
        ("0.1.0", "v0.2.0", False),  # plain drift
        ("0.2.0-rc.1", "v0.2.0", False),  # stable tag must not ship prerelease metadata
    ],
)
def test_version_matches_tag_rule(manifest: str, tag: str, expected: bool) -> None:
    """Only the TAG is normalized. A manifest must equal the exact tag version or its stable core —
    never a *different* prerelease of the same core (Codex P1 on PR #159)."""
    assert vrt.version_matches_tag(manifest, tag) is expected


def test_different_prerelease_in_manifests_is_blocked(monkeypatch, tmp_path) -> None:
    """End-to-end: tag v0.2.0-rc.2 with manifests at 0.2.0-rc.1 must FAIL, or we would publish an
    rc.2 release whose shipped package/plugin metadata declares rc.1."""
    _write_manifests(tmp_path, "0.2.0-rc.1")
    monkeypatch.setattr(vrt, "ROOT", tmp_path)
    ok, msgs = vrt.verify("v0.2.0-rc.2")
    assert not ok
    assert any("pyproject.toml" in m for m in msgs)
    assert any("plugin.json" in m for m in msgs)
    assert any("marketplace.json" in m for m in msgs)


def test_exact_prerelease_manifests_accepted(monkeypatch, tmp_path) -> None:
    """A repo that deliberately declares the prerelease is valid for that exact tag."""
    _write_manifests(tmp_path, "0.2.0-rc.1")
    monkeypatch.setattr(vrt, "ROOT", tmp_path)
    ok, msgs = vrt.verify("v0.2.0-rc.1")
    assert ok, msgs


@pytest.mark.parametrize(
    "bad_tag",
    [
        "v0.1.0-",  # empty prerelease identifier (Codex P2)
        "v0.1.0+",  # empty build identifier
        "v0.1.0-+build",  # empty prerelease, then build
        "v0.1.0-rc..1",  # empty dot-separated identifier
        "v0.1.0-rc.01",  # numeric identifier with a leading zero
        "v01.2.3",  # leading zero in the release core
        "v1.2",  # not MAJOR.MINOR.PATCH
        "v1.2.3.4",
        "vX.Y.Z",
        "",
    ],
)
def test_malformed_semver_tags_are_rejected(bad_tag: str) -> None:
    """Malformed tags must NOT be reduced to a valid core — they match the workflow's `v*.*.*-*`
    trigger, so a lenient parse would publish a release for them (Codex P2 on PR #159)."""
    assert vrt.release_core(bad_tag) is None
    assert vrt.version_matches_tag("0.1.0", bad_tag) is False


@pytest.mark.parametrize("good_tag", ["v0.1.0", "v0.1.0-rc.1", "v1.2.3+build.7", "v10.20.30-a.1"])
def test_wellformed_semver_tags_accepted(good_tag: str) -> None:
    assert vrt.release_core(good_tag) is not None


def test_malformed_tag_hard_stops_verify(monkeypatch, tmp_path) -> None:
    """verify() refuses a malformed tag outright — even when every manifest is at the core it
    would have been reduced to."""
    _write_manifests(tmp_path, "0.1.0")
    monkeypatch.setattr(vrt, "ROOT", tmp_path)
    ok, msgs = vrt.verify("v0.1.0-")
    assert not ok
    assert any("Malformed tag" in m for m in msgs)
