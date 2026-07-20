#!/usr/bin/env python3
"""Verify a release tag against the version declared in all shipped manifests.

Called by ``.github/workflows/release.yml`` on a pushed ``v*`` tag. A tag may be a stable release
(``v0.2.0``) or a pre-release (``v0.2.0-rc.1``, ``v0.2.0-alpha.1``, ``v0.2.0+build.7``). Per semver,
a pre-release/build tag is a qualifier *of* a release version, so the comparison is on the
**release core** only: ``v0.2.0-rc.1`` releases version ``0.2.0`` and must match a repo at ``0.2.0``.

Previously the workflow compared the whole ``0.2.0-rc.1`` string against pyproject's ``0.2.0`` and
so rejected every pre-release tag — even though the workflow's own trigger advertises them. This
script is the single, unit-tested source of that comparison for both the pyproject and the
manifest checks.

Manifests checked (all must agree with the tag's release core):
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


def release_core(version: str) -> str:
    """The semver release core: strip a leading ``v`` and any ``-prerelease`` / ``+build`` suffix.

    ``v0.2.0-rc.1`` -> ``0.2.0``;  ``0.2.0+build.7`` -> ``0.2.0``;  ``v1.2.3`` -> ``1.2.3``.
    """
    core = version.removeprefix("v")
    # Prerelease starts at the first '-', build metadata at the first '+'; either ends the core.
    core = re.split(r"[-+]", core, maxsplit=1)[0]
    return core


def _pyproject_version() -> str | None:
    m = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.MULTILINE)
    return m.group(1) if m else None


def verify(tag: str) -> tuple[bool, list[str]]:
    """Return (ok, messages). messages are ``::error::``-prefixed on failure, one ``OK:`` on pass."""
    tag_core = release_core(tag)
    errors: list[str] = []

    pkg = _pyproject_version()
    if pkg is None:
        errors.append("::error::Cannot find version in pyproject.toml")
    elif release_core(pkg) != tag_core:
        errors.append(
            f"::error title=Version mismatch::Tag {tag} (release {tag_core}) does not match "
            f"pyproject.toml {pkg}."
        )
        errors.append(
            "::error title=Version mismatch::Run make release-prep TYPE=..., merge the PR, then "
            "push the tag."
        )

    try:
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        v = plugin.get("version", "MISSING")
        if release_core(str(v)) != tag_core:
            errors.append(
                f"::error title=Manifest drift::.claude-plugin/plugin.json version={v!r}, "
                f"expected release {tag_core!r}"
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
            if release_core(str(v)) != tag_core:
                errors.append(
                    f"::error title=Manifest drift::.claude-plugin/marketplace.json "
                    f"plugins[0].version={v!r}, expected release {tag_core!r}"
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
