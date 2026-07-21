#!/usr/bin/env python3
"""Verify a release tag against the version declared in all shipped manifests.

Called by ``.github/workflows/release.yml`` on a pushed ``v*`` tag. A tag may be a stable release
(``v0.2.0``) or a pre-release (``v0.2.0-rc.1``, ``v0.2.0-alpha.1``, ``v0.2.0+build.7``). Per semver,
a pre-release/build tag qualifies a release version, so a manifest at the stable release ``0.2.0``
satisfies tag ``v0.2.0-rc.1``.

**Only the tag is normalized — never the manifest.** A manifest value must equal either the exact
tag version or the tag's stable release core (see ``version_matches_tag``). Normalizing the
manifest too would let ``v0.2.0-rc.2`` pass against manifests still declaring ``0.2.0-rc.1``,
publishing an rc.2 release whose shipped metadata says rc.1.

Previously the workflow compared the whole ``0.2.0-rc.1`` string against pyproject's ``0.2.0`` and
so rejected every pre-release tag — even though the workflow's own trigger advertises them. This
script is the single, unit-tested source of that comparison for both the pyproject and the
manifest checks.

Manifests checked (each must satisfy the rule above):
  * ``pyproject.toml``                     — ``version = "X"``          (source of truth)
  * ``.claude-plugin/plugin.json``         — ``version``
  * ``.claude-plugin/marketplace.json``    — ``plugins[0].version``

Usage:  python3 scripts/verify_release_tag.py <tag>          (e.g. v0.2.0-rc.1)
        TAG_NAME=v0.2.0 python3 scripts/verify_release_tag.py

Exit 0 with an ``OK:`` line when all agree; exit 1 with GitHub ``::error::`` annotations otherwise.
stdlib only.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# The official semver.org grammar. Identifiers must be NON-EMPTY, so malformed tags like
# `v0.1.0-`, `v0.1.0+` or `v0.1.0-+build` are rejected rather than silently reduced to `0.1.0`
# (they match the workflow's `v*.*.*-*` trigger, so a lenient parse would let them publish).
_SEMVER_RE = re.compile(
    r"^(?P<core>(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


def parse_semver(version: str) -> re.Match[str] | None:
    """Match ``version`` (a leading ``v`` is allowed) against the full semver grammar, else None."""
    return _SEMVER_RE.match(version.removeprefix("v"))


def release_core(version: str) -> str | None:
    """The semver release core, or ``None`` when ``version`` is not valid semver.

    ``v0.2.0-rc.1`` -> ``0.2.0``;  ``0.2.0+build.7`` -> ``0.2.0``;  ``v1.2.3`` -> ``1.2.3``;
    ``v0.1.0-`` / ``v0.1.0+`` / ``v1.2`` / ``v01.2.3`` -> ``None`` (malformed).
    """
    m = parse_semver(version)
    return m.group("core") if m else None


def _pyproject_version() -> str | None:
    m = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.MULTILINE)
    return m.group(1) if m else None


def version_matches_tag(manifest_version: str, tag: str) -> bool:
    """Is ``manifest_version`` an acceptable declared version for release ``tag``?

    Only the TAG is normalized — never the manifest. A manifest may declare either:

    * the **exact** tag version (``0.2.0-rc.1`` for tag ``v0.2.0-rc.1``), or
    * the **stable release core** (``0.2.0``), the usual case since ``bump_version.py`` writes
      release versions and a pre-release tag qualifies that same release.

    Stripping the suffix from the MANIFEST too would let tag ``v0.2.0-rc.2`` pass against manifests
    still declaring ``0.2.0-rc.1`` — publishing an rc.2 release whose shipped metadata says rc.1,
    defeating the drift guard. So the manifest value is compared verbatim against both accepted
    forms.
    """
    core = release_core(tag)
    if core is None:  # malformed tag -> fail closed; verify() reports the specific error
        return False
    return manifest_version in (tag.removeprefix("v"), core)


def verify(tag: str) -> tuple[bool, list[str]]:
    """Return (ok, messages). messages are ``::error::``-prefixed on failure, one ``OK:`` on pass."""
    tag_core = release_core(tag)
    if tag_core is None:
        return False, [
            f"::error title=Malformed tag::Tag {tag!r} is not valid SemVer "
            "(MAJOR.MINOR.PATCH with optional non-empty -prerelease / +build). "
            "Refusing to publish a release for it.",
        ]
    errors: list[str] = []

    pkg = _pyproject_version()
    if pkg is None:
        errors.append("::error::Cannot find version in pyproject.toml")
    elif not version_matches_tag(pkg, tag):
        errors.append(
            f"::error title=Version mismatch::Tag {tag} does not match pyproject.toml {pkg} "
            f"(expected {tag.removeprefix('v')!r} or {tag_core!r})."
        )
        errors.append(
            "::error title=Version mismatch::Run make release-prep TYPE=..., merge the PR, then "
            "push the tag."
        )

    try:
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        v = plugin.get("version", "MISSING")
        if not version_matches_tag(str(v), tag):
            errors.append(
                f"::error title=Manifest drift::.claude-plugin/plugin.json version={v!r}, "
                f"expected {tag.removeprefix('v')!r} or {tag_core!r}"
            )
    except Exception as exc:  # noqa: BLE001 — any read/parse failure is a manifest finding
        errors.append(f"::error title=Manifest drift::.claude-plugin/plugin.json: {exc}")

    try:
        market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
        plugins = market.get("plugins", [])
        if not plugins:
            errors.append(
                "::error title=Manifest drift::.claude-plugin/marketplace.json: plugins array is "
                "empty or missing"
            )
        else:
            v = plugins[0].get("version", "MISSING")
            if not version_matches_tag(str(v), tag):
                errors.append(
                    f"::error title=Manifest drift::.claude-plugin/marketplace.json "
                    f"plugins[0].version={v!r}, expected {tag.removeprefix('v')!r} or {tag_core!r}"
                )
    except Exception as exc:  # noqa: BLE001
        errors.append(f"::error title=Manifest drift::.claude-plugin/marketplace.json: {exc}")

    if errors:
        errors.append(
            "::error title=Manifest drift::Run make release-prep TYPE=... to sync all manifests, "
            "then re-push the tag."
        )
        return False, errors
    return True, [f"OK: tag {tag} (release {tag_core}) matches pyproject.toml and all manifests"]


def main(argv: list[str]) -> int:
    tag = argv[1] if len(argv) > 1 else os.environ.get("TAG_NAME", "")
    if not tag:
        print("::error::No tag provided (arg or TAG_NAME env)")
        return 1
    ok, messages = verify(tag)
    for m in messages:
        print(m)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
