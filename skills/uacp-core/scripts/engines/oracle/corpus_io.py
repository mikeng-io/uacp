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
missing directory yields ``[]`` and malformed documents are skipped — but skips
are NEVER silent: the ``scan_*`` variants return ``(items, skipped)`` and every
skip batch is logged as a WARNING with filenames (the package logging idiom,
see ``index_build.py``), so a silently shrinking corpus is visible both to
callers (the conformance lint) and in runtime logs (#110).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from engines.domain.corpus import KnowledgeItem, Lesson, OKFParseError

logger = logging.getLogger(__name__)

# A skip report entry: (filename, "<ExceptionType>: <message>").
SkipReport = list[tuple[str, str]]


def _scan_okf_dir[T](
    directory: Path, parse: Callable[[str], T], label: str
) -> tuple[list[T], SkipReport]:
    """Parse every ``*.md`` OKF doc in ``directory``; never raise.

    Returns ``(items, skipped)``. Each unparseable document lands in ``skipped``
    as ``(filename, reason)`` and the batch is logged as one WARNING.
    Subdirectories (e.g. ``indexes/``) are ignored by the ``*.md`` glob.
    """
    items: list[T] = []
    skipped: SkipReport = []
    if not directory.is_dir():
        return items, skipped
    for path in sorted(directory.glob("*.md")):
        try:
            items.append(parse(path.read_text(encoding="utf-8")))
        except (OKFParseError, KeyError, ValueError, OSError) as exc:
            skipped.append((path.name, f"{type(exc).__name__}: {exc}"))
    if skipped:
        logger.warning(
            "%s: skipped %d unparseable OKF doc(s) in %s: %s",
            label,
            len(skipped),
            directory,
            "; ".join(f"{name} ({reason})" for name, reason in skipped),
        )
    return items, skipped


def scan_lessons_dir(directory: Path) -> tuple[list[Lesson], SkipReport]:
    """Load every ``*.md`` lesson in ``directory``; report (not hide) skips."""
    return _scan_okf_dir(directory, Lesson.from_okf, "load_lessons_dir")


def scan_knowledge_dir(directory: Path) -> tuple[list[KnowledgeItem], SkipReport]:
    """Load every ``*.md`` knowledge item in ``directory``; report (not hide) skips."""
    return _scan_okf_dir(directory, KnowledgeItem.from_okf, "load_knowledge_dir")


def load_lessons_dir(directory: Path) -> list[Lesson]:
    """Load every ``*.md`` lesson in ``directory``; skips are logged; never raise."""
    return scan_lessons_dir(directory)[0]


def load_knowledge_dir(directory: Path) -> list[KnowledgeItem]:
    """Load every ``*.md`` knowledge item in ``directory``; skips are logged; never raise.

    Subdirectories (e.g. ``indexes/``) are ignored by the ``*.md`` glob.
    """
    return scan_knowledge_dir(directory)[0]
