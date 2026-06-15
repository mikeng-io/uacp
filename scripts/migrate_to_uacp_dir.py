#!/usr/bin/env python3
"""Hard-cut migration of a UACP repo's flat runtime dirs into the .uacp/ namespace.

Moves state/, .outputs/ (-> resolutions/), and the phase dirs under the governed
base, then rewrites the `.outputs/` token to `resolutions/` inside already-emitted
YAML/JSONL so in-flight runs stay resolvable (council finding C-2). No fallback /
dual-read.

Design — fixed config home vs. relocatable base:
    `.uacp/config.toml` is the FIXED bootstrap config home; config.py always reads
    the per-project override there. `[paths] base` relocates the RUNTIME DIRS only.
    So an operator who wants a custom base creates `.uacp/config.toml` with
    `[paths] base = "..."` BEFORE migrating; this script then honors that base for
    the runtime dirs (council B1) while keeping the override file itself at the
    fixed `.uacp/config.toml`. By default base == `.uacp`, so the two coincide.

Resumability (council Gap-4): each move is independent. If a re-run finds a move's
source gone and destination present it skips it; a true src/dst collision is
collected and reported at the end without aborting the other moves, so a half-
migrated repo (e.g. interrupted) completes on re-run.

Usage:  python3 scripts/migrate_to_uacp_dir.py [REPO_ROOT]   (default: cwd)
"""
from __future__ import annotations

import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parents[1] / "skills" / "uacp-core" / "scripts"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))
from config import base_dir  # noqa: E402

# (dir-name-at-old-root, subdir-name-under-base)
_MOVES = [
    ("state", "state"),
    (".outputs", "resolutions"),
    ("proposals", "proposals"),
    ("plans", "plans"),
    ("executions", "executions"),
    ("verification", "verification"),
    ("knowledge", "knowledge"),
]
# Old `.outputs/` nested these sub-trees; once `.outputs/` -> `resolutions/`, lift
# them back to the top of the base where config/uacp.toml declares them to live
# (council Gap-1). (under-resolutions-subdir, subdir-under-base)
_NESTED_LIFTS = [
    ("bridges", "bridges"),
    ("councils", "councils"),
]
_REWRITE_SUFFIXES = {".yaml", ".yml", ".jsonl", ".json", ".md"}

# Runtime-dir ignore block appended to a migrating repo's .gitignore (council 1e).
# Kept in sync with the repo's own .gitignore.
_GITIGNORE_BLOCK = """
# UACP runtime artifacts — generated during execution, not source of truth.
# Under the .uacp/ namespace, the per-phase run dirs are runtime; config.toml
# (knob overrides) and knowledge/ (project-learned) are project-level and tracked.
.uacp/state/
.uacp/proposals/
.uacp/plans/
.uacp/executions/
.uacp/verification/
.uacp/resolutions/
.uacp/bridges/
.uacp/councils/
"""
# Idempotency sentinel: presence of this entry means the block is already applied.
_GITIGNORE_SENTINEL = ".uacp/state/"


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


def _warn_non_canonical(repo_root: Path) -> None:
    """Detect & announce a non-canonical legacy layout (council Gap-2).

    The canonical pre-migration shape is FLAT top-level dirs. If NONE of those
    exist but a non-empty `.outputs/` holds a nested governed tree (state/,
    plans/, …), warn rather than silently doing a surprising partial move.
    """
    flat = [repo_root / old for old, _ in _MOVES]
    if any(p.exists() for p in flat):
        return
    legacy = repo_root / ".outputs"
    if not legacy.is_dir():
        return
    nested = [d.name for d in legacy.iterdir() if d.is_dir()
              and d.name in {"state", "proposals", "plans", "executions",
                             "verification", "resolutions", "knowledge"}]
    if nested:
        print(
            f"WARNING: non-canonical layout: no flat top-level dirs, but "
            f".outputs/ contains a nested governed tree {sorted(nested)}. "
            f"This script migrates FLAT layouts; the nested tree will NOT be "
            f"auto-relocated — relocate it manually."
        )


def _move(src: Path, dst: Path, conflicts: list[Path]) -> None:
    """Resumable single move. Skip if already done; collect (don't raise) on
    a true src/dst collision so other moves still run (council Gap-4)."""
    src_exists = src.exists()
    dst_exists = dst.exists()
    if src_exists and not dst_exists:
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
    elif not src_exists and dst_exists:
        return  # already migrated
    elif src_exists and dst_exists:
        conflicts.append(dst)
    # neither exists: nothing to do


def _append_gitignore(repo_root: Path) -> None:
    """Idempotently append the runtime-dir ignore block to an existing
    .gitignore so migrated runtime state isn't accidentally committed (1e)."""
    gi = repo_root / ".gitignore"
    if not gi.exists():
        return
    text = gi.read_text(encoding="utf-8")
    if _GITIGNORE_SENTINEL in text:
        return  # already applied
    sep = "" if text.endswith("\n") or text == "" else "\n"
    gi.write_text(text + sep + _GITIGNORE_BLOCK, encoding="utf-8")


def migrate(repo_root: Path) -> None:
    repo_root = Path(repo_root).resolve()
    _warn_non_canonical(repo_root)
    # `base` honors a pre-existing `.uacp/config.toml` [paths] base override
    # (council B1); default resolves to <root>/.uacp.
    base = base_dir(repo_root)
    base.mkdir(parents=True, exist_ok=True)

    conflicts: list[Path] = []
    for old_name, sub in _MOVES:
        _move(repo_root / old_name, base / sub, conflicts)

    # Lift bridges/councils out of the wholesale-moved resolutions/ (Gap-1):
    # their OLD home was .outputs/{bridges,councils}, now resolutions/{...}.
    for nested, sub in _NESTED_LIFTS:
        _move(base / "resolutions" / nested, base / sub, conflicts)

    _rewrite_outputs_token(base)

    # Starter override lives at the FIXED bootstrap config home, NOT under `base`
    # — config.py always reads it there. When base == .uacp these coincide.
    starter = repo_root / ".uacp" / "config.toml"
    starter.parent.mkdir(parents=True, exist_ok=True)
    if not starter.exists():
        starter.write_text(
            "# UACP per-project config overrides. Defaults ship with the kernel.\n"
            "# Example:\n#   [paths]\n#   base = \".uacp\"\n",
            encoding="utf-8",
        )

    _append_gitignore(repo_root)

    if conflicts:
        listing = "\n  ".join(str(p) for p in conflicts)
        raise SystemExit(
            "migration completed the un-done moves but found existing "
            f"destinations (resolve manually, then re-run):\n  {listing}"
        )


if __name__ == "__main__":
    migrate(Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd())
    print("migrated to .uacp/")
