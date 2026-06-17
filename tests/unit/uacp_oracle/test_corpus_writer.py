"""Tests for the Oracle corpus-write surface (engines.oracle.corpus_writer).

The Oracle is the only code that writes the knowledge/lesson corpus. It does so
through the GOVERNED artifact writer (uacp_artifact_write handler) so Guardian
still audits the write — never via a raw filesystem write.

These tests prove:
  - persist_lesson serializes a corpus.Lesson to OKF and writes it to
    .uacp/lessons/<id>.md through the governed writer (handler returns ok=True)
  - the written lesson is loadable by corpus.load_lessons_dir (round-trip)
  - persist_knowledge does the same for .uacp/knowledge/<id>.md
"""
from __future__ import annotations

from pathlib import Path

from engines.domain.corpus import KnowledgeItem, Lesson
from engines.oracle import corpus_writer
from engines.oracle.corpus_io import load_knowledge_dir, load_lessons_dir


def _lesson() -> Lesson:
    return Lesson(
        id="governed-writer-discipline",
        title="Use governed writers for corpus, never raw FS",
        project="uacp-oracle-test",
        domains=["governance"],
        invariants=["governed-writers-only"],
        severity="HIGH",
        source_run="uacp-test-r1",
        extracted_at="2026-06-01T00:00:00Z",
        body="## Context\nThe Oracle owns corpus writes.\n",
    )


def _knowledge() -> KnowledgeItem:
    return KnowledgeItem(
        id="corpus-ownership-pattern",
        title="Single-owner corpus boundary",
        type="pattern",
        description="The Oracle is the sole reader/writer of the corpus.",
        domains=["governance"],
        scope="shared",
        body="## Pattern\nRoute corpus access through engines.oracle.\n",
    )


def test_corpus_writer_declared_side_effects_match_schema_type(monkeypatch):
    """MED-1: the corpus writer must pass declared_side_effects as the type the
    registered uacp_artifact_write schema declares (string), not a list — so a
    schema-validating runtime won't reject the corpus write.

    Intercepts the governed handler and inspects the args it was called with.
    """
    captured: dict = {}

    def _fake_handler(args):
        captured.update(args)
        import json

        return json.dumps({"ok": True, "path": args["target_path"]})

    # _resolve_handler returns (handler, plugin); plugin=None is tolerated by the
    # writer's env/policy restore branch.
    monkeypatch.setattr(
        corpus_writer, "_resolve_handler", lambda: (_fake_handler, None)
    )

    corpus_writer.persist_lesson(
        Path("/tmp/ws"),
        _lesson(),
        run_id="uacp-test-r1",
        phase="resolve",
        reason="x",
        authority_artifact="resolutions/uacp-test-r1-lessons.yaml",
    )

    assert "declared_side_effects" in captured
    assert isinstance(captured["declared_side_effects"], str), (
        "declared_side_effects must be a str to match the uacp_artifact_write "
        f"schema; got {type(captured['declared_side_effects']).__name__}"
    )


def test_persist_lesson_round_trips_through_governed_writer(temp_uacp_root: Path):
    lesson = _lesson()
    result = corpus_writer.persist_lesson(
        temp_uacp_root,
        lesson,
        run_id="uacp-test-r1",
        phase="resolve",
        reason="extract durable lesson at RESOLVE",
        authority_artifact="resolutions/uacp-test-r1-lessons.yaml",
    )
    assert result.get("ok") is True, f"governed write failed: {result}"
    assert result.get("path") == "lessons/governed-writer-discipline.md"

    # Loadable by the real corpus loader.
    lessons_dir = temp_uacp_root / ".uacp" / "lessons"
    loaded = load_lessons_dir(lessons_dir)
    assert len(loaded) == 1
    assert loaded[0].id == "governed-writer-discipline"
    assert loaded[0].project == "uacp-oracle-test"
    assert loaded[0].severity == "HIGH"
    assert "governed writers" in loaded[0].title


def test_persist_knowledge_round_trips_through_governed_writer(temp_uacp_root: Path):
    item = _knowledge()
    result = corpus_writer.persist_knowledge(
        temp_uacp_root,
        item,
        run_id="uacp-test-r1",
        phase="resolve",
        reason="distill knowledge at RESOLVE",
        authority_artifact="resolutions/uacp-test-r1-lessons.yaml",
    )
    assert result.get("ok") is True, f"governed write failed: {result}"
    assert result.get("path") == "knowledge/corpus-ownership-pattern.md"

    knowledge_dir = temp_uacp_root / ".uacp" / "knowledge"
    loaded = load_knowledge_dir(knowledge_dir)
    assert len(loaded) == 1
    assert loaded[0].id == "corpus-ownership-pattern"
    assert loaded[0].type == "pattern"


def test_persist_lesson_failure_surfaces_error(temp_uacp_root: Path):
    """A malformed id (path traversal) is rejected by the governed writer, not raw-written."""
    bad = _lesson()
    bad.id = "../escape"
    result = corpus_writer.persist_lesson(
        temp_uacp_root,
        bad,
        run_id="uacp-test-r1",
        phase="resolve",
        reason="x",
        authority_artifact="resolutions/uacp-test-r1-lessons.yaml",
    )
    assert "error" in result
    # nothing escaped the governed namespace
    assert not (temp_uacp_root.parent / "escape.md").exists()


def test_resolver_import_failure_degrades_to_error_dict(
    temp_uacp_root: Path, monkeypatch
):
    """If the governed-writer handler cannot be resolved (e.g. ModuleNotFoundError
    under a pip-install layout where the path math is wrong), the writer must
    DEGRADE to a compliant error dict — never raise to the caller (floor-safety).
    """

    def _boom():
        raise ModuleNotFoundError("uacp_guardian")

    monkeypatch.setattr(corpus_writer, "_resolve_handler", _boom)

    result = corpus_writer.persist_lesson(
        temp_uacp_root,
        _lesson(),
        run_id="uacp-test-r1",
        phase="resolve",
        reason="x",
        authority_artifact="resolutions/uacp-test-r1-lessons.yaml",
    )
    assert result.get("ok") is False
    assert "error" in result
    assert "uacp_guardian" in result["error"] or "handler" in result["error"].lower()


def test_governed_write_restores_prior_policy_and_env(
    temp_uacp_root: Path, monkeypatch
):
    """The writer must restore the PREVIOUS plugin._POLICY object and the previous
    UACP_ROOT env after the call — not leave them as None / clobbered (no race
    fallout for a concurrent context that already cached a policy).
    """
    _handler, plugin = corpus_writer._resolve_handler()

    sentinel_policy = object()
    plugin._POLICY = sentinel_policy
    monkeypatch.setenv("UACP_ROOT", "/some/other/root")

    result = corpus_writer.persist_lesson(
        temp_uacp_root,
        _lesson(),
        run_id="uacp-test-r1",
        phase="resolve",
        reason="restore check",
        authority_artifact="resolutions/uacp-test-r1-lessons.yaml",
    )
    assert result.get("ok") is True

    # Prior cache + env restored exactly (not None, not the workspace).
    assert plugin._POLICY is sentinel_policy
    import os

    assert os.environ.get("UACP_ROOT") == "/some/other/root"
