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


def _knowledge_md() -> str:
    return textwrap.dedent("""\
        ---
        type: pattern
        id: governed-writer-discipline
        title: Always route protected writes through a governed writer
        description: How to satisfy the no-raw-writes invariant.
        tags: [governance, writers]
        domains: [runtime, governance]
        scope: shared
        derived_from: [kanban-guard-resolve-bypass]
        timestamp: "2026-06-17"
        ---
        Body prose explaining the pattern.
        """)


def test_knowledge_from_okf():
    from engines.domain.corpus import KnowledgeItem
    k = KnowledgeItem.from_okf(_knowledge_md())
    assert k.type == "pattern"
    assert k.id == "governed-writer-discipline"
    assert k.scope == "shared"
    assert k.derived_from == ["kanban-guard-resolve-bypass"]
    assert k.domains == ["runtime", "governance"]
    assert "Body prose" in k.body


def test_knowledge_rejects_lesson_type():
    import pytest
    from engines.domain.corpus import KnowledgeItem
    bad = _knowledge_md().replace("type: pattern", "type: lesson")
    with pytest.raises(ValueError):
        KnowledgeItem.from_okf(bad)


def test_knowledge_to_okf_round_trips():
    from engines.domain.corpus import KnowledgeItem
    original = KnowledgeItem.from_okf(_knowledge_md())
    assert KnowledgeItem.from_okf(original.to_okf()) == original


from engines.domain.corpus import bes_score


def test_bes_prior_when_no_eligible_runs():
    # eligible == 0 -> prior 0.5, regardless of days
    assert bes_score(eligible=0, recurrences=0, days_since_extracted=0) == 0.5
    assert bes_score(eligible=0, recurrences=0, days_since_extracted=1000) == 0.5


def test_bes_smoothed_posterior_no_recurrence():
    # eligible=8, recurrences=0, days=0 (recency=1.0)
    # successes=8 ; smoothed=(8+1)/(8+2)=0.9 ; bes=0.9*1.0
    assert bes_score(eligible=8, recurrences=0, days_since_extracted=0) == 0.9


def test_bes_smoothed_posterior_with_recurrences():
    # eligible=8, recurrences=4, days=0
    # successes=4 ; smoothed=(4+1)/(8+2)=0.5 ; bes=0.5
    assert bes_score(eligible=8, recurrences=4, days_since_extracted=0) == 0.5


def test_bes_all_recurrences_floor_not_zero():
    # eligible=3, recurrences=3 -> successes=0 ; smoothed=(0+1)/(3+2)=0.2
    assert bes_score(eligible=3, recurrences=3, days_since_extracted=0) == 0.2


def test_bes_recency_floor_at_half():
    # eligible=8, recurrences=0, smoothed=0.9.
    # days=365 -> recency = max(0.5, 1-0.5) = 0.5 -> bes=0.45
    assert bes_score(eligible=8, recurrences=0, days_since_extracted=365) == 0.45
    # days far past 2*365 must NOT drop below floor: recency clamps to 0.5 -> 0.45
    assert bes_score(eligible=8, recurrences=0, days_since_extracted=100000) == 0.45


def test_bes_recency_partial_decay():
    # days=182.5 -> recency = 1-0.5*(0.5) = 0.75 ; smoothed=0.9 -> 0.675
    assert bes_score(eligible=8, recurrences=0, days_since_extracted=182.5) == 0.675


from engines.domain.corpus import bes_bonus


def test_bes_bonus_base_tiers():
    assert bes_bonus(bes=0.90, severity="LOW", eligible=10) == 5
    assert bes_bonus(bes=0.85, severity="LOW", eligible=10) == 5   # boundary inclusive
    assert bes_bonus(bes=0.70, severity="LOW", eligible=10) == 4   # boundary inclusive
    assert bes_bonus(bes=0.69, severity="LOW", eligible=10) == 3
    assert bes_bonus(bes=0.55, severity="LOW", eligible=10) == 3   # boundary inclusive
    assert bes_bonus(bes=0.40, severity="LOW", eligible=10) == 2   # boundary inclusive
    assert bes_bonus(bes=0.39, severity="LOW", eligible=3) == 1    # eligible<5 so no -2


def test_bes_bonus_severity_modifier():
    # +1 for CRITICAL/HIGH, applied on top of the tier
    assert bes_bonus(bes=0.90, severity="CRITICAL", eligible=10) == 6
    assert bes_bonus(bes=0.55, severity="HIGH", eligible=10) == 4
    assert bes_bonus(bes=0.55, severity="MEDIUM", eligible=10) == 3


def test_bes_bonus_chronic_penalty():
    # BES<.4 AND eligible>=5 -> -2, stacking with the base tier of 1
    assert bes_bonus(bes=0.30, severity="LOW", eligible=8) == -1
    # penalty does not apply below the eligibility floor
    assert bes_bonus(bes=0.30, severity="LOW", eligible=4) == 1
    # a CRITICAL chronic lesson: tier 1 +1 (sev) -2 (chronic) = 0
    assert bes_bonus(bes=0.30, severity="CRITICAL", eligible=8) == 0
