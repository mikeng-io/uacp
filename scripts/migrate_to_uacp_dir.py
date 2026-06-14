#!/usr/bin/env python3
"""Hard-cut migration of a UACP repo's flat runtime dirs into the .uacp/ namespace.

Moves state/, .outputs/ (-> resolutions/), and the phase dirs under .uacp/, then
rewrites the `.outputs/` token to `resolutions/` inside already-emitted YAML/JSONL
so in-flight runs stay resolvable (council finding C-2). No fallback / dual-read.

Usage:  python3 scripts/migrate_to_uacp_dir.py [REPO_ROOT]   (default: cwd)
"""
from __future__ import annotations

import sys
from pathlib import Path

# (dir-name-at-old-root, subdir-name-under-.uacp)
_MOVES = [
    ("state", "state"),
    (".outputs", "resolutions"),
    ("proposals", "proposals"),
    ("plans", "plans"),
    ("executions", "executions"),
    ("verification", "verification"),
    ("knowledge", "knowledge"),
]
_REWRITE_SUFFIXES = {".yaml", ".yml", ".jsonl", ".json", ".md"}


def _rewrite_outputs_token(base: Path) -> None:
    """Replace base-relative `.outputs/` with `resolutions/` in moved text files."""
    for path in base.rglob("*"):
        if not path.is_file() or path.suffix not in _REWRITE_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if ".outputs/" not in text:
            continue
        new = text.replace(".outputs/", "resolutions/")
        if new != text:
            path.write_text(new, encoding="utf-8")


def migrate(repo_root: Path) -> None:
    repo_root = Path(repo_root).resolve()
    base = repo_root / ".uacp"
    base.mkdir(exist_ok=True)
    for old_name, sub in _MOVES:
        src = repo_root / old_name
        dst = base / sub
        if not src.exists():
            continue  # idempotent: already migrated or never existed
        if dst.exists():
            raise SystemExit(f"refusing to overwrite existing {dst}; resolve manually")
        src.rename(dst)
    _rewrite_outputs_token(base)
    starter = base / "config.toml"
    if not starter.exists():
        starter.write_text(
            "# UACP per-project config overrides. Defaults ship with the kernel.\n"
            "# Example:\n#   [paths]\n#   base = \".uacp\"\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    migrate(Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd())
    print("migrated to .uacp/")
