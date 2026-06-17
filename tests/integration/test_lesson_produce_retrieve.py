"""Integration: lesson produce -> store -> retrieve loop through the REAL Oracle path.

Proves that a lesson produced at RESOLVE is:
  1. Persisted via the REAL Oracle corpus-write surface
     (engines.oracle.corpus_writer.persist_lesson), which serializes the OKF doc
     and routes it through the GOVERNED artifact writer (Guardian-audited) into
     .uacp/lessons/<id>.md.
  2. Loadable by the real corpus loader (engines.domain.corpus.load_lessons_dir)
     and by the Oracle's own read accessor (corpus_writer.load_lessons).
  3. Survivable through the real oracle aggregator (engines.oracle.aggregator.oracle_query)
     when the oracle is enabled for a FULL-tier phase (propose/plan/verify).

Seam used: the REAL governed write path. The Oracle is the single owner of corpus
read+write; persist_lesson is the production seam a RESOLVE-phase agent uses. The
prior version wrote the file directly to the filesystem because the
uacp_artifact_write handler did NOT support the lessons/ root — that bug is now
fixed (allowed_roots includes 'lessons'), so this test drives the governed write
end-to-end.

Oracle floor guarantee (from aggregator.py): the oracle must import and run clean
with lancedb/llama_cpp/httpx all poisoned (they aren't installed in the test env).
We pass oracle_cfg={'enabled': True} with no honcho/semantic keys so semantic and
honcho sources are skipped gracefully. The Oracle no longer reads run-state — the
data-ownership boundary keeps state/manifest out of the Oracle — so a FULL query
emits no 'runstate' packet and runstate is never in sources_skipped.

The test asserts:
  - persist_lesson returns ok=True and the governed path
  - load_lessons_dir / corpus_writer.load_lessons return the lesson (corpus is
    the structured retrieval surface)
  - oracle_query returns without error in FULL mode with semantic skipped (floor)
  - the Oracle never surfaces or skips a 'runstate' source
  - lesson content is intact round-trip (id, title, project, body)
"""

from __future__ import annotations

from pathlib import Path

from engines.domain.corpus import Lesson, load_lessons_dir, parse_okf
from engines.oracle import corpus_writer
from engines.oracle.aggregator import oracle_query


# -- Fixture helpers ----------------------------------------------------------

_LESSON_ID = "e2e-lesson-001"
_PROJECT = "uacp-integration-test"
_RUN_ID = "uacp-test-r42"

_LESSON_BODY = """\
## Context

The legacy `config/guardian-policy.yaml` was removed in the Slice 3 config-collapse.
GuardianPolicy.load() now reads exclusively from `config/uacp.toml [guardian]`.

## Action

When adding or modifying guardian policy, update `config/uacp.toml` — not any
legacy YAML file.

## Evidence

- `skills/uacp-core/scripts/core.py` `GuardianPolicy.load` reads `[guardian]`.
- `config/guardian-policy.yaml` does not exist in the repo.
"""


def _lesson() -> Lesson:
    return Lesson(
        id=_LESSON_ID,
        title="Guardian guardian-policy.yaml is no longer the authority source",
        project=_PROJECT,
        domains=["governance", "config"],
        invariants=[
            "GuardianPolicy.load reads from config/uacp.toml [guardian], not guardian-policy.yaml"
        ],
        affected_paths=[
            "config/uacp.toml",
            "runtime-adapters/hermes/plugins/uacp_guardian/__init__.py",
        ],
        severity="HIGH",
        source_run=_RUN_ID,
        extracted_at="2026-06-01T00:00:00Z",
        eligible=3,
        recurrences=1,
        bes=0.72,
        tags=["config-collapse", "slice-3"],
        body=_LESSON_BODY,
    )


def _persist_lesson(root: Path) -> dict:
    """Persist the lesson via the REAL Oracle corpus-write surface (governed write)."""
    return corpus_writer.persist_lesson(
        root,
        _lesson(),
        run_id=_RUN_ID,
        phase="resolve",
        reason="extract durable lesson at RESOLVE",
        authority_artifact=f"resolutions/{_RUN_ID}-lessons.yaml",
    )


# -- Tests --------------------------------------------------------------------

class TestLessonProduceRetrieve:
    """Lesson OKF round-trip: persist via Oracle governed write -> load -> oracle floor."""

    def test_lesson_roundtrip_via_okf_parser(self) -> None:
        """OKF parse + Lesson.from_okf are lossless for the produced document."""
        okf = _lesson().to_okf()
        fm, body = parse_okf(okf)
        lesson = Lesson.from_okf(okf)
        assert lesson.id == _LESSON_ID
        assert lesson.project == _PROJECT
        assert lesson.severity == "HIGH"
        assert lesson.bes == 0.72
        assert "governance" in lesson.domains
        assert body.startswith("## Context")

    def test_persist_lesson_through_governed_write(self, temp_uacp_root: Path) -> None:
        """persist_lesson drives the REAL governed artifact writer into .uacp/lessons/."""
        result = _persist_lesson(temp_uacp_root)
        assert result.get("ok") is True, f"governed corpus write failed: {result}"
        assert result.get("path") == f"lessons/{_LESSON_ID}.md"
        # The governed write actually landed the file.
        assert (temp_uacp_root / ".uacp" / "lessons" / f"{_LESSON_ID}.md").is_file()

    def test_corpus_loads_lesson_after_governed_write(self, temp_uacp_root: Path) -> None:
        """load_lessons_dir + the Oracle read accessor return the governed-written lesson."""
        _persist_lesson(temp_uacp_root)
        lessons_dir = temp_uacp_root / ".uacp" / "lessons"
        lessons = load_lessons_dir(lessons_dir)
        assert len(lessons) == 1, f"Expected 1 lesson, got {len(lessons)}: {lessons}"
        lesson = lessons[0]
        assert lesson.id == _LESSON_ID
        assert lesson.project == _PROJECT
        assert lesson.title == "Guardian guardian-policy.yaml is no longer the authority source"
        assert "config-collapse" in lesson.tags
        assert "slice-3" in lesson.tags

        # The Oracle's own read accessor returns the same lesson (single owner).
        via_oracle = corpus_writer.load_lessons(temp_uacp_root)
        assert [item.id for item in via_oracle] == [_LESSON_ID]

    def test_corpus_ignores_malformed_lesson(self, temp_uacp_root: Path) -> None:
        """load_lessons_dir skips malformed OKF files without raising."""
        _persist_lesson(temp_uacp_root)
        lessons_dir = temp_uacp_root / ".uacp" / "lessons"
        # Write a malformed OKF (no frontmatter)
        (lessons_dir / "bad-lesson.md").write_text("no frontmatter here\n", encoding="utf-8")
        # Write another malformed OKF (missing id field)
        (lessons_dir / "no-id.md").write_text("---\ntitle: missing id\n---\nbody\n", encoding="utf-8")
        lessons = load_lessons_dir(lessons_dir)
        # Only the valid lesson should be loaded
        assert len(lessons) == 1
        assert lessons[0].id == _LESSON_ID

    def test_oracle_query_floor_returns_without_error(self, temp_uacp_root: Path) -> None:
        """oracle_query in FULL mode (propose) runs clean with semantic skipped.

        This is the oracle FLOOR guarantee: the aggregator must not raise even when
        lancedb/llama_cpp/httpx are absent.  We verify:
          - returns a dict with 'packets' and 'metadata' keys
          - metadata.mode == 'full' (propose is FULL tier)
          - metadata.sources_skipped may include 'semantic' (store not built)
          - the Oracle never reads state: no 'runstate' source/packet
          - no state files are written (oracle is read-only)
        """
        _persist_lesson(temp_uacp_root)
        state_files_before = list((temp_uacp_root / ".uacp" / "state").rglob("*"))

        result = oracle_query(
            workspace=temp_uacp_root,
            phase="propose",
            project=_PROJECT,
            oracle_cfg={"enabled": True},  # enable oracle, no semantic/honcho config
        )

        # Structure assertions
        assert "packets" in result, f"oracle_query missing 'packets' key: {result}"
        assert "metadata" in result, f"oracle_query missing 'metadata' key: {result}"
        meta = result["metadata"]
        assert meta.get("phase") == "propose"
        assert meta.get("mode") == "full"

        # Data-ownership boundary: the Oracle does not read state/manifests.
        assert not any(p.source == "runstate" for p in result["packets"])
        assert "runstate" not in meta.get("sources_skipped", [])

        # Read-only: no new state files created
        state_files_after = list((temp_uacp_root / ".uacp" / "state").rglob("*"))
        assert state_files_before == state_files_after, (
            f"oracle_query wrote state files (must be read-only): "
            f"new={set(str(f) for f in state_files_after) - set(str(f) for f in state_files_before)}"
        )

    def test_oracle_query_returns_correct_modes(self, temp_uacp_root: Path) -> None:
        """oracle_query respects PHASE_TIERS: FULL phases return mode='full',
        NONE/WRITEBACK phases return early with no retrieval."""
        _persist_lesson(temp_uacp_root)
        cfg = {"enabled": True}

        # FULL phases: propose, plan, verify
        for phase in ("propose", "plan", "verify"):
            result = oracle_query(workspace=temp_uacp_root, phase=phase, project=_PROJECT, oracle_cfg=cfg)
            assert result["metadata"]["mode"] == "full", (
                f"Phase '{phase}' should be FULL, got {result['metadata']['mode']!r}"
            )

        # NONE phase: execute
        result = oracle_query(workspace=temp_uacp_root, phase="execute", project=_PROJECT, oracle_cfg=cfg)
        assert result["metadata"]["mode"] == "none", (
            f"Phase 'execute' should be NONE, got {result['metadata']['mode']!r}"
        )

        # WRITEBACK phase: resolve
        result = oracle_query(workspace=temp_uacp_root, phase="resolve", project=_PROJECT, oracle_cfg=cfg)
        assert result["metadata"]["mode"] == "writeback", (
            f"Phase 'resolve' should be WRITEBACK, got {result['metadata']['mode']!r}"
        )

        # ADVISORY phase: brainstorm
        result = oracle_query(workspace=temp_uacp_root, phase="brainstorm", project=_PROJECT, oracle_cfg=cfg)
        assert result["metadata"]["mode"] == "advisory", (
            f"Phase 'brainstorm' should be ADVISORY, got {result['metadata']['mode']!r}"
        )

    def test_oracle_disabled_returns_empty(self, temp_uacp_root: Path) -> None:
        """oracle_query with oracle disabled returns empty packets and disabled note."""
        _persist_lesson(temp_uacp_root)
        result = oracle_query(
            workspace=temp_uacp_root,
            phase="propose",
            project=_PROJECT,
            oracle_cfg={"enabled": False},
        )
        assert result["packets"] == []
        assert "disabled" in result["metadata"].get("note", "").lower()
