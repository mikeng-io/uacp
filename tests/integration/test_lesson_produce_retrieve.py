"""Integration: lesson produce → store → retrieve loop through real corpus + oracle.

Proves that a lesson written to .uacp/lessons/ (RESOLVE-phase output) is:
  1. Loadable by the real corpus loader  (engines.domain.corpus.load_lessons_dir)
  2. Retrievable by the real oracle aggregator (engines.oracle.aggregator.oracle_query)
     when the oracle is enabled for a FULL-tier phase (propose/plan/verify).

Seam used: the lesson OKF document is written DIRECTLY to the resolved governed
path (.uacp/lessons/<id>.md) because uacp_artifact_write does NOT support the
lessons/ root (allowed: plans/proposals/executions/verification/resolutions/
knowledge).  This is documented as intentional: the artifact-writer boundary
sits at the adapters layer; the corpus loader and oracle aggregator consume the
filesystem directly.  The test validates the end-to-end produce→retrieve path
at the filesystem seam, which IS the real handler contract a RESOLVE-phase
coding agent exercises.

Oracle floor guarantee (from aggregator.py): the oracle must import and run
clean with lancedb/llama_cpp/httpx all poisoned (they aren't installed in the
test env).  We pass oracle_cfg={'enabled': True} with no honcho/semantic keys
so semantic and honcho sources are skipped gracefully; runstate is queried but
there are no matching manifests, yielding empty packets.  The lesson retrieval
assertion uses the corpus loader directly (load_lessons_dir) as the definitive
retrieval surface — the oracle's lesson channel is the semantic pipeline
(requires a built vector store), which is correctly skipped in the floor env.
The test therefore asserts:
  - load_lessons_dir returns the lesson (corpus is the structured retrieval surface)
  - oracle_query returns without error in FULL mode with semantic skipped (floor)
  - lesson content is intact round-trip (id, title, project, body)
"""

from __future__ import annotations

from pathlib import Path


from engines.domain.corpus import Lesson, load_lessons_dir, parse_okf
from engines.oracle.aggregator import oracle_query


# ── Fixture helpers ──────────────────────────────────────────────────────────

_LESSON_ID = "e2e-lesson-001"
_PROJECT = "uacp-integration-test"

_LESSON_OKF = """\
---
id: {id}
title: "Guardian guardian-policy.yaml is no longer the authority source"
project: {project}
domains:
  - governance
  - config
invariants:
  - "GuardianPolicy.load reads from config/uacp.toml [guardian], not guardian-policy.yaml"
affected_paths:
  - config/uacp.toml
  - runtime-adapters/hermes/plugins/uacp_guardian/__init__.py
severity: HIGH
source_run: uacp-test-r42
extracted_at: "2026-06-01T00:00:00Z"
eligible: 3
recurrences: 1
bes: 0.72
promoted_to: null
tags:
  - config-collapse
  - slice-3
---
## Context

The legacy `config/guardian-policy.yaml` was removed in the Slice 3 config-collapse.
GuardianPolicy.load() now reads exclusively from `config/uacp.toml [guardian]`.

## Action

When adding or modifying guardian policy, update `config/uacp.toml` — not any
legacy YAML file.

## Evidence

- `skills/uacp-core/scripts/core.py` `GuardianPolicy.load` reads `[guardian]`.
- `config/guardian-policy.yaml` does not exist in the repo.
""".format(id=_LESSON_ID, project=_PROJECT)


def _write_lesson_to_governed_path(root: Path) -> Path:
    """Write the lesson OKF to .uacp/lessons/<id>.md — the resolved governed path.

    SEAM NOTE: uacp_artifact_write does not support lessons/ (its allowed set is
    plans/proposals/executions/verification/resolutions/knowledge).  We write
    directly to the filesystem path that corpus.load_lessons_dir() globs.  This
    is the real seam a RESOLVE-phase coding agent uses (the writer tool boundary
    is the adapter layer; the corpus + oracle consumers read the filesystem).
    """
    lessons_dir = root / ".uacp" / "lessons"
    lessons_dir.mkdir(parents=True, exist_ok=True)
    lesson_path = lessons_dir / f"{_LESSON_ID}.md"
    lesson_path.write_text(_LESSON_OKF, encoding="utf-8")
    return lesson_path


# ── Tests ────────────────────────────────────────────────────────────────────

class TestLessonProduceRetrieve:
    """Lesson OKF round-trip: write to governed path → load via corpus → oracle floor."""

    def test_lesson_roundtrip_via_okf_parser(self) -> None:
        """OKF parse + Lesson.from_okf are lossless for the test document."""
        fm, body = parse_okf(_LESSON_OKF)
        lesson = Lesson.from_okf(_LESSON_OKF)
        assert lesson.id == _LESSON_ID
        assert lesson.project == _PROJECT
        assert lesson.severity == "HIGH"
        assert lesson.bes == 0.72
        assert "governance" in lesson.domains
        assert body.startswith("## Context")

    def test_corpus_loads_lesson_from_governed_path(self, temp_uacp_root: Path) -> None:
        """load_lessons_dir returns the lesson written to .uacp/lessons/."""
        _write_lesson_to_governed_path(temp_uacp_root)
        lessons_dir = temp_uacp_root / ".uacp" / "lessons"
        lessons = load_lessons_dir(lessons_dir)
        assert len(lessons) == 1, f"Expected 1 lesson, got {len(lessons)}: {lessons}"
        lesson = lessons[0]
        assert lesson.id == _LESSON_ID
        assert lesson.project == _PROJECT
        assert lesson.title == "Guardian guardian-policy.yaml is no longer the authority source"
        assert "config-collapse" in lesson.tags
        assert "slice-3" in lesson.tags

    def test_corpus_ignores_malformed_lesson(self, temp_uacp_root: Path) -> None:
        """load_lessons_dir skips malformed OKF files without raising."""
        lessons_dir = temp_uacp_root / ".uacp" / "lessons"
        lessons_dir.mkdir(parents=True, exist_ok=True)
        # Write a valid lesson first
        (lessons_dir / f"{_LESSON_ID}.md").write_text(_LESSON_OKF, encoding="utf-8")
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
          - no state files are written (oracle is read-only)
        """
        _write_lesson_to_governed_path(temp_uacp_root)
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

        # Read-only: no new state files created
        state_files_after = list((temp_uacp_root / ".uacp" / "state").rglob("*"))
        assert state_files_before == state_files_after, (
            f"oracle_query wrote state files (must be read-only): "
            f"new={set(str(f) for f in state_files_after) - set(str(f) for f in state_files_before)}"
        )

    def test_oracle_query_returns_correct_modes(self, temp_uacp_root: Path) -> None:
        """oracle_query respects PHASE_TIERS: FULL phases return mode='full',
        NONE/WRITEBACK phases return early with no retrieval."""
        _write_lesson_to_governed_path(temp_uacp_root)
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
        _write_lesson_to_governed_path(temp_uacp_root)
        result = oracle_query(
            workspace=temp_uacp_root,
            phase="propose",
            project=_PROJECT,
            oracle_cfg={"enabled": False},
        )
        assert result["packets"] == []
        assert "disabled" in result["metadata"].get("note", "").lower()
