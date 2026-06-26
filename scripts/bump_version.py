#!/usr/bin/env python3
"""
Bump UACP version across all plugin manifests.

Usage:
    python3 scripts/bump_version.py major|minor|patch [--dry-run]

Files updated:
    pyproject.toml                      (source of truth)
    .claude-plugin/plugin.json          (Claude Code plugin)
    .claude-plugin/marketplace.json     (Claude Code marketplace)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TARGETS = [
    (ROOT / "pyproject.toml",                    r'^(version = ")[^"]+(")'  ),
    (ROOT / ".claude-plugin/plugin.json",         r'("version":\s*")[^"]+(")'),
    (ROOT / ".claude-plugin/marketplace.json",    r'("version":\s*")[^"]+(")'),
]


def bump(version: str, part: str) -> str:
    major, minor, patch = map(int, version.split("."))
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def read_current_version() -> str:
    text = (ROOT / "pyproject.toml").read_text()
    m = re.search(r'^version = "([^"]+)"', text, re.MULTILINE)
    if not m:
        raise RuntimeError("version not found in pyproject.toml")
    return m.group(1)


def update(path: Path, pattern: str, new_ver: str, dry_run: bool) -> None:
    rel = path.relative_to(ROOT)
    text = path.read_text()
    new_text, n = re.subn(pattern, rf"\g<1>{new_ver}\g<2>", text, flags=re.MULTILINE)
    if n == 0:
        print(f"  WARN  {rel}  — pattern not found, check manually")
        return
    if text == new_text:
        print(f"  SKIP  {rel}  — already at {new_ver}")
        return
    if not dry_run:
        path.write_text(new_text)
    print(f"  {'[dry]' if dry_run else 'UPD  '}  {rel}")


def main() -> None:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    parts = [a for a in args if a != "--dry-run"]

    if len(parts) != 1 or parts[0] not in ("major", "minor", "patch"):
        print("Usage: bump_version.py major|minor|patch [--dry-run]")
        sys.exit(1)

    old_ver = read_current_version()
    new_ver = bump(old_ver, parts[0])

    print(f"{'[dry run] ' if dry_run else ''}Bumping {old_ver} → {new_ver}\n")

    for path, pattern in TARGETS:
        update(path, pattern, new_ver, dry_run)

    print()
    if dry_run:
        print("No files written. Re-run without --dry-run to apply.")
        return

    print("Next steps:")
    print(f"  git add pyproject.toml .claude-plugin/plugin.json .claude-plugin/marketplace.json")
    print(f"  git commit -m 'chore(release): bump version {old_ver} → {new_ver}'")
    print(f"  # open PR → merge → then:")
    print(f"  git pull --ff-only origin main")
    print(f"  git tag v{new_ver} && git push origin v{new_ver}")


if __name__ == "__main__":
    main()
