"""One-time migration: legacy top-level knowledge/ -> .uacp/ corpora (idempotent).

Classification rules:
  knowledge/lessons/*          -> .uacp/lessons/   (pre-OKF YAML lessons)
  knowledge/*-lessons*.md      -> .uacp/lessons/   (root-level lesson prose — FIX 1)
  knowledge/*.md (other)       -> .uacp/knowledge/ (knowledge items)
  knowledge/scenarios/         -> NOT moved (config still points here — FIX 5)
  knowledge/gate-templates/    -> NOT moved (config still points here — FIX 5)
"""

from __future__ import annotations

import shutil
from pathlib import Path

def _is_lesson_file(path: Path) -> bool:
    """True if a root-level file should be classified as a lesson (FIX 1)."""
    return "-lessons" in path.name


def migrate(root: Path) -> None:
    root = Path(root)
    base = root / ".uacp"
    legacy = root / "knowledge"
    if not legacy.exists():
        return
    lessons_dst = base / "lessons"
    knowledge_dst = base / "knowledge"
    lessons_dst.mkdir(parents=True, exist_ok=True)
    knowledge_dst.mkdir(parents=True, exist_ok=True)
    (knowledge_dst / "indexes").mkdir(exist_ok=True)

    # Move knowledge/lessons/* -> .uacp/lessons/
    legacy_lessons = legacy / "lessons"
    if legacy_lessons.is_dir():
        for item in legacy_lessons.iterdir():
            dst = lessons_dst / item.name
            if not dst.exists():
                shutil.move(str(item), str(dst))

    # Move root-level files, classifying by name (FIX 1)
    for item in legacy.iterdir():
        if item.is_dir():
            # Skip all subdirs including scenarios/ and gate-templates/ (FIX 5)
            continue
        if item.name.startswith("."):
            continue
        if _is_lesson_file(item):
            dst = lessons_dst / item.name
        else:
            dst = knowledge_dst / item.name
        if not dst.exists():
            shutil.move(str(item), str(dst))

    # Remove lessons/ subdir if now empty (idempotent: missing is fine)
    if legacy_lessons.is_dir() and not any(legacy_lessons.iterdir()):
        legacy_lessons.rmdir()
    # Do NOT rmtree legacy/ — scenarios/ and gate-templates/ still live there (FIX 5)


if __name__ == "__main__":
    migrate(Path.cwd())
