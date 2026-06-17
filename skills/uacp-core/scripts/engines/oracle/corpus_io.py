"""Oracle corpus DISK loaders — the side-effecting read surface for the corpus.

The Oracle is the single owner of the knowledge/lesson corpus (``.uacp/lessons/``
and ``.uacp/knowledge/``). These loaders read OKF documents off disk and parse
them into the pure dataclasses defined in :mod:`engines.domain.corpus`.

They live INSIDE the oracle package (alongside ``corpus_writer.py``) — NOT in
``engines.domain.corpus`` — so that the corpus-ownership boundary is STRUCTURAL,
not merely grep-enforced: a module outside ``engines/oracle/`` cannot read the
corpus from disk without importing from the oracle package, which the boundary
test forbids.

``engines.domain.corpus`` keeps only pure, side-effect-free code (the dataclasses,
``parse_okf``, the BES math, and the in-memory ``*_for_project`` filters).

No heavy/ML imports here — this module is part of the floor. Never raises: a
missing directory yields ``[]`` and malformed documents are skipped.
"""
from __future__ import annotations

from pathlib import Path

from engines.domain.corpus import KnowledgeItem, Lesson, OKFParseError


def load_lessons_dir(directory: Path) -> list[Lesson]:
    """Load every ``*.md`` lesson in ``directory``; skip malformed; never raise."""
    out: list[Lesson] = []
    if not directory.is_dir():
        return out
    for path in sorted(directory.glob("*.md")):
        try:
            out.append(Lesson.from_okf(path.read_text(encoding="utf-8")))
        except (OKFParseError, KeyError, ValueError, OSError):
            continue
    return out


def load_knowledge_dir(directory: Path) -> list[KnowledgeItem]:
    """Load every ``*.md`` knowledge item in ``directory``; skip malformed; never raise.

    Subdirectories (e.g. ``indexes/``) are ignored by the ``*.md`` glob.
    """
    out: list[KnowledgeItem] = []
    if not directory.is_dir():
        return out
    for path in sorted(directory.glob("*.md")):
        try:
            out.append(KnowledgeItem.from_okf(path.read_text(encoding="utf-8")))
        except (OKFParseError, KeyError, ValueError, OSError):
            continue
    return out
