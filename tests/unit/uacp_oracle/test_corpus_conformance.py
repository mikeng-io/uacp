"""Corpus-conformance lint + skip-reporting loader tests (#110).

Two layers, mirroring the design-lint precedent (tests/unit/uacp_core/test_design_lint.py):

1. REAL-CORPUS CONFORMANCE LINT — every file under the repo's ``.uacp/knowledge/``
   and ``.uacp/lessons/`` must parse via ``from_okf``. This is the CI seam: the
   ``test`` job runs ``make test`` (pytest), so an unparseable corpus doc fails CI.
   The lint asserts:
   - zero skips on the real corpus (the loader is no longer allowed to silently
     shrink the corpus);
   - the knowledge corpus loads in full (>= 26 items — the #110 migration floor);
   - no corpus file dodges the ``*.md`` glob (a ``.yaml`` lesson would be
     invisible to the loader — that is a lint failure, not a skip).

2. FIXTURE TESTS for the skip-reporting loaders — a malformed doc is excluded
   from the items, COUNTED in the ``skipped`` report with its filename and
   reason, and logged as a WARNING (the oracle package's logging idiom, see
   ``engines/oracle/index_build.py``). Non-vacuity: the same corpus with the
   malformed doc removed reports zero skips.

``load_lessons_dir`` / ``load_knowledge_dir`` keep their original signatures
(items only) — existing callers are untouched; the scan variants expose skips.
"""

from __future__ import annotations

import logging
from pathlib import Path

from engines.oracle.corpus_io import (
    load_knowledge_dir,
    load_lessons_dir,
    scan_knowledge_dir,
    scan_lessons_dir,
)

# ---------------------------------------------------------------------------
# Repo corpus resolution
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
_KNOWLEDGE_DIR = _REPO_ROOT / ".uacp" / "knowledge"
_LESSONS_DIR = _REPO_ROOT / ".uacp" / "lessons"

# #110 floor: the knowledge corpus had 26 frontmatter docs + index.md at
# migration time. The corpus may only grow.
_KNOWLEDGE_FLOOR = 26
_LESSONS_FLOOR = 4


# ---------------------------------------------------------------------------
# 1. Real-corpus conformance lint (CI-wired via `make test`)
# ---------------------------------------------------------------------------


class TestRealCorpusConformance:
    def test_knowledge_corpus_fully_parses_no_skips(self):
        items, skipped = scan_knowledge_dir(_KNOWLEDGE_DIR)
        assert skipped == [], (
            f"unparseable knowledge doc(s) — every .uacp/knowledge/*.md must parse "
            f"via KnowledgeItem.from_okf: {skipped}"
        )
        assert len(items) >= _KNOWLEDGE_FLOOR
        # Full-corpus, not a subset: every *.md in the dir became an item.
        assert len(items) == len(list(_KNOWLEDGE_DIR.glob("*.md")))

    def test_knowledge_ids_present_and_unique(self):
        items, _ = scan_knowledge_dir(_KNOWLEDGE_DIR)
        ids = [item.id for item in items]
        assert all(ids), "every knowledge item must carry a non-empty id"
        assert len(set(ids)) == len(ids), f"duplicate knowledge ids: {ids}"

    def test_knowledge_id_equals_filename_stem(self):
        """``index_build`` reconstructs each item's source path as ``{id}.md``
        (engines/oracle/index_build.py:173-176) — id and filename stem are a
        load-bearing coupling, not a convention. A rename without an id update
        must be a red CI, never a silent identity change."""
        by_id = {item.id for item in scan_knowledge_dir(_KNOWLEDGE_DIR)[0]}
        stems = {p.stem for p in _KNOWLEDGE_DIR.glob("*.md")}
        assert by_id == stems, (
            f"knowledge id/filename-stem divergence — ids without a matching "
            f"file: {sorted(by_id - stems)}; files without a matching id: "
            f"{sorted(stems - by_id)}"
        )

    def test_lessons_corpus_fully_parses_no_skips(self):
        items, skipped = scan_lessons_dir(_LESSONS_DIR)
        assert skipped == [], (
            f"unparseable lesson doc(s) — every .uacp/lessons/*.md must parse "
            f"via Lesson.from_okf: {skipped}"
        )
        assert len(items) >= _LESSONS_FLOOR
        assert len(items) == len(list(_LESSONS_DIR.glob("*.md")))

    def test_lesson_ids_present_and_unique(self):
        items, _ = scan_lessons_dir(_LESSONS_DIR)
        ids = [lesson.id for lesson in items]
        assert all(ids), "every lesson must carry a non-empty id"
        assert len(set(ids)) == len(ids), f"duplicate lesson ids: {ids}"

    def test_lesson_id_equals_filename_stem(self):
        """Same id/stem coupling as knowledge (index_build reconstructs
        ``{id}.md`` for lessons too — engines/oracle/index_build.py:169-176)."""
        by_id = {lesson.id for lesson in scan_lessons_dir(_LESSONS_DIR)[0]}
        stems = {p.stem for p in _LESSONS_DIR.glob("*.md")}
        assert by_id == stems, (
            f"lesson id/filename-stem divergence — ids without a matching file: "
            f"{sorted(by_id - stems)}; files without a matching id: "
            f"{sorted(stems - by_id)}"
        )

    def test_no_corpus_file_dodges_the_loader_glob(self):
        """The loaders glob ``*.md`` only. Any other top-level FILE in a corpus
        dir (e.g. a ``.yaml`` lesson) would be invisible to the engine — that is
        a conformance failure, not a skip. Subdirectories (e.g. built
        ``knowledge/indexes/``) are legitimately outside the corpus."""
        for directory in (_KNOWLEDGE_DIR, _LESSONS_DIR):
            strays = [
                p.name
                for p in directory.iterdir()
                if p.is_file() and p.suffix != ".md" and not p.name.startswith(".")
            ]
            assert strays == [], f"non-.md corpus file(s) invisible to the loader in {directory}: {strays}"

    def test_load_dir_backcompat_returns_full_corpus(self):
        """Original entry points still return plain item lists (callers untouched)."""
        knowledge = load_knowledge_dir(_KNOWLEDGE_DIR)
        lessons = load_lessons_dir(_LESSONS_DIR)
        assert len(knowledge) >= _KNOWLEDGE_FLOOR
        assert len(lessons) >= _LESSONS_FLOOR


# ---------------------------------------------------------------------------
# 2. Skip-reporting loader fixtures
# ---------------------------------------------------------------------------

_GOOD_KNOWLEDGE = """---
type: pattern
id: good-doc
title: Good Doc
---
Body.
"""

_KNOWLEDGE_MISSING_ID = """---
type: pattern
title: No Id Doc
---
Body.
"""

_GOOD_LESSON = """---
type: lesson
id: good-lesson
title: Good Lesson
project: uacp
---
Body.
"""


class TestSkipReporting:
    def test_malformed_knowledge_is_counted_with_filename(self, tmp_path):
        d = tmp_path / "knowledge"
        d.mkdir()
        (d / "good.md").write_text(_GOOD_KNOWLEDGE, encoding="utf-8")
        (d / "bad.md").write_text("no frontmatter at all\n", encoding="utf-8")
        (d / "no-id.md").write_text(_KNOWLEDGE_MISSING_ID, encoding="utf-8")
        items, skipped = scan_knowledge_dir(d)
        assert [item.id for item in items] == ["good-doc"]
        assert sorted(name for name, _ in skipped) == ["bad.md", "no-id.md"]
        reasons = dict(skipped)
        assert "OKFParseError" in reasons["bad.md"]
        assert "KeyError" in reasons["no-id.md"] and "id" in reasons["no-id.md"]

    def test_yaml_and_type_errors_are_skips_not_raises(self, tmp_path):
        """Codex P2 (PR #123): malformed frontmatter YAML (unclosed flow list →
        yaml.parser.ParserError) and scalar-where-iterable values (`domains: 5`
        → TypeError) escaped the scanner's except tuple, breaking the
        never-raise floor. Both must be reported as skips."""
        d = tmp_path / "lessons"
        d.mkdir()
        (d / "good.md").write_text(_GOOD_LESSON, encoding="utf-8")
        (d / "unclosed.md").write_text(
            "---\nid: x\ntitle: t\nproject: p\nextracted_at: 2026-01-01\n"
            "tags: [unclosed\n---\nBody.\n",
            encoding="utf-8",
        )
        (d / "scalar-domains.md").write_text(
            "---\nid: y\ntitle: t\nproject: p\nextracted_at: 2026-01-01\n"
            "domains: 5\n---\nBody.\n",
            encoding="utf-8",
        )
        items, skipped = scan_lessons_dir(d)  # must not raise
        assert [lesson.id for lesson in items] == ["good-lesson"]
        reasons = dict(skipped)
        assert sorted(reasons) == ["scalar-domains.md", "unclosed.md"]
        assert "ParserError" in reasons["unclosed.md"]
        assert "TypeError" in reasons["scalar-domains.md"]

    def test_malformed_lesson_is_counted_with_filename(self, tmp_path):
        d = tmp_path / "lessons"
        d.mkdir()
        (d / "good.md").write_text(_GOOD_LESSON, encoding="utf-8")
        (d / "bad.md").write_text("# not OKF\n", encoding="utf-8")
        lessons, skipped = scan_lessons_dir(d)
        assert [lesson.id for lesson in lessons] == ["good-lesson"]
        assert [name for name, _ in skipped] == ["bad.md"]

    def test_skips_are_logged_as_warning(self, tmp_path, caplog):
        d = tmp_path / "knowledge"
        d.mkdir()
        (d / "bad.md").write_text("nope\n", encoding="utf-8")
        with caplog.at_level(logging.WARNING, logger="engines.oracle.corpus_io"):
            items, skipped = scan_knowledge_dir(d)
        assert items == [] and len(skipped) == 1
        warning = "\n".join(r.getMessage() for r in caplog.records if r.levelno == logging.WARNING)
        assert "bad.md" in warning and "skipped 1" in warning

    def test_clean_dir_reports_zero_skips_and_no_warning(self, tmp_path, caplog):
        """Non-vacuity: same shape, malformed doc absent -> zero skips, no log."""
        d = tmp_path / "knowledge"
        d.mkdir()
        (d / "good.md").write_text(_GOOD_KNOWLEDGE, encoding="utf-8")
        with caplog.at_level(logging.WARNING, logger="engines.oracle.corpus_io"):
            items, skipped = scan_knowledge_dir(d)
        assert len(items) == 1 and skipped == []
        assert not [r for r in caplog.records if r.levelno >= logging.WARNING]

    def test_missing_dir_scans_empty(self, tmp_path):
        assert scan_lessons_dir(tmp_path / "nope") == ([], [])
        assert scan_knowledge_dir(tmp_path / "nope") == ([], [])
