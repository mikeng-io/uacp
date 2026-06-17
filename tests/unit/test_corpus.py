import textwrap
from engines.domain.corpus import Lesson, parse_okf, OKFParseError


def _lesson_md() -> str:
    return textwrap.dedent("""\
        ---
        type: lesson
        id: kanban-guard-resolve-bypass
        title: Kanban guard must not bypass resolve
        project: uacp
        domains: [kanban, runtime]
        invariants: [no-main-writes]
        affected_paths: ["state/**"]
        severity: HIGH
        source_run: phase5-kanban-guard-20260514
        extracted_at: "2026-05-14T00:00:00+00:00"
        eligible: 0
        recurrences: 0
        bes: 0.5
        promoted_to: null
        tags: [guard, resolve]
        ---
        ## description
        Doing X in run R caused failure F.

        ## prohibition
        Do not do X.
        """)


def test_parse_okf_splits_frontmatter_and_body():
    fm, body = parse_okf(_lesson_md())
    assert fm["type"] == "lesson"
    assert fm["domains"] == ["kanban", "runtime"]
    assert body.startswith("## description")


def test_parse_okf_rejects_missing_frontmatter():
    import pytest
    with pytest.raises(OKFParseError):
        parse_okf("no frontmatter here\n")


def test_lesson_from_okf_round_trip_fields():
    lesson = Lesson.from_okf(_lesson_md())
    assert lesson.id == "kanban-guard-resolve-bypass"
    assert lesson.project == "uacp"
    assert lesson.domains == ["kanban", "runtime"]
    assert lesson.invariants == ["no-main-writes"]
    assert lesson.severity == "HIGH"
    assert lesson.eligible == 0
    assert lesson.recurrences == 0
    assert lesson.bes == 0.5
    assert lesson.promoted_to is None
    assert "Do not do X." in lesson.body


def test_lesson_to_okf_round_trips():
    original = Lesson.from_okf(_lesson_md())
    serialized = original.to_okf()
    reparsed = Lesson.from_okf(serialized)
    assert reparsed == original


def test_lesson_to_okf_emits_type_lesson_first():
    serialized = Lesson.from_okf(_lesson_md()).to_okf()
    assert serialized.startswith("---\ntype: lesson\n")
