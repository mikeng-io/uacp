#!/usr/bin/env python3
"""
Bump UACP version across all plugin manifests.

Usage:
    python3 scripts/bump_version.py major|minor|patch [--dry-run]

Files updated (must all match, or no file is touched):
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
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version = "([^"]+)"', text, re.MULTILINE)
    if not m:
        raise RuntimeError("version not found in pyproject.toml")
    ver = m.group(1)
    if not re.fullmatch(r"\d+\.\d+\.\d+", ver):
        raise RuntimeError(
            f"Current version '{ver}' is not X.Y.Z format. "
            "Pre-release or custom versions cannot be bumped by this script — "
            "edit pyproject.toml and the manifests manually, then push the tag."
        )
    return ver


def validate_update(path: Path, pattern: str, new_ver: str) -> tuple[str, str]:
    """
    Validate that `pattern` matches exactly once.
    Returns (original_text, new_text).
    Raises RuntimeError on miss or multiple matches — caller aborts all writes.
    """
    rel = path.relative_to(ROOT)
    text = path.read_text(encoding="utf-8")
    new_text, n = re.subn(pattern, rf"\g<1>{new_ver}\g<2>", text, flags=re.MULTILINE)
    if n == 0:
        raise RuntimeError(f"{rel}: version pattern not found — aborting, no files written")
    if n > 1:
        raise RuntimeError(
            f"{rel}: pattern matched {n} times (expected 1) — aborting, no files written"
        )
    return text, new_text


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

    # Pass 1: validate all targets before touching any file.
    pending: list[tuple[Path, str, str]] = []
    try:
        for path, pattern in TARGETS:
            orig, updated = validate_update(path, pattern, new_ver)
            pending.append((path, orig, updated))
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    # Pass 2: write (skipped in dry-run mode).
    for path, orig, updated in pending:
        rel = path.relative_to(ROOT)
        if orig == updated:
            print(f"  SKIP  {rel}  — already at {new_ver}")
            continue
        if not dry_run:
            path.write_text(updated, encoding="utf-8")
        print(f"  {'[dry]' if dry_run else 'UPD  '}  {rel}")

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
