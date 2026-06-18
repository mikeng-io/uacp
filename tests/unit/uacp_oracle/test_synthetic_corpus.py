"""Unit tests for the deterministic synthetic OKF corpus generator.

NON-GATED: no heavy deps (no lancedb / sentence-transformers / network). Runs in
the default ``pytest`` suite. Proves the generator is fully deterministic in
``(n, seed)``, that its files load via ``corpus_io``, and that the frontmatter
satisfies the same OKF rules the repo-wide OKF lint enforces.
"""
from __future__ import annotations

import yaml

from engines.domain.corpus import KnowledgeItem, Lesson
from engines.oracle.corpus_io import load_knowledge_dir, load_lessons_dir
from engines.oracle.eval.synthetic import generate_corpus

# Mirror tests/unit/skills/test_okf_frontmatter.py's accepted type set.
_OKF_VALID_TYPES = {"contract", "pattern", "digest", "lessons", "analysis"}


def _all_files(root):
    return sorted(p for p in root.rglob("*.md"))


def test_same_seed_byte_identical_files_and_map(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    spec_a = generate_corpus(a, n=8, seed=7)
    spec_b = generate_corpus(b, n=8, seed=7)

    files_a = _all_files(a)
    files_b = _all_files(b)
    rel_a = [p.relative_to(a).as_posix() for p in files_a]
    rel_b = [p.relative_to(b).as_posix() for p in files_b]
    assert rel_a == rel_b, "same seed must produce the same file set"

    for pa, pb in zip(files_a, files_b, strict=True):
        assert pa.read_bytes() == pb.read_bytes(), f"byte mismatch for {pa.name}"

    # Relevance map identical.
    assert spec_a.relevance == spec_b.relevance
    assert [i.id for i in spec_a.items] == [i.id for i in spec_b.items]


def test_different_seed_changes_content(tmp_path):
    spec0 = generate_corpus(tmp_path / "s0", n=8, seed=0)
    spec1 = generate_corpus(tmp_path / "s1", n=8, seed=1)
    # Topic ordering differs -> at least the per-position topic assignment moves.
    assert spec0.relevance != spec1.relevance or [i.domain for i in spec0.items] != [
        i.domain for i in spec1.items
    ]


def test_relevance_map_is_unambiguous(tmp_path):
    # n beyond the topic count: topics repeat, but each query still maps to one id.
    spec = generate_corpus(tmp_path / "c", n=12, seed=3)
    queries = [q for q, _ in spec.relevance]
    expected_ids = [i for _, i in spec.relevance]
    assert len(queries) == len(set(queries)), "each query must be unique"
    item_ids = {i.id for i in spec.items}
    for eid in expected_ids:
        assert eid in item_ids, f"expected id {eid} must exist in the corpus"


def test_files_load_via_corpus_io(tmp_path):
    spec = generate_corpus(tmp_path / "c", n=10, seed=2)
    lessons = load_lessons_dir(spec.root / "lessons")
    knowledge = load_knowledge_dir(spec.root / "knowledge")

    assert lessons, "expected at least one lesson"
    assert knowledge, "expected at least one knowledge item"
    assert all(isinstance(x, Lesson) for x in lessons)
    assert all(isinstance(x, KnowledgeItem) for x in knowledge)

    loaded_ids = {x.id for x in lessons} | {x.id for x in knowledge}
    # Every generated item must round-trip through the loaders (none skipped).
    assert loaded_ids == {i.id for i in spec.items}

    # Lessons carry the BES / domain / invariant fields the pipeline reads.
    for lesson in lessons:
        assert lesson.domains, "lesson must declare a domain"
        assert lesson.invariants, "lesson must declare an invariant"
        assert 0.0 <= lesson.bes <= 1.0


def test_frontmatter_passes_okf_lint_rules(tmp_path):
    spec = generate_corpus(tmp_path / "c", n=8, seed=5)
    for path in _all_files(spec.root):
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---"), f"{path.name}: must start with OKF fence"
        parts = text.split("---", 2)
        assert len(parts) >= 3, f"{path.name}: missing closing fence"
        fm = yaml.safe_load(parts[1])
        assert isinstance(fm, dict)
        assert fm["type"] in _OKF_VALID_TYPES, f"{path.name}: bad type {fm['type']!r}"
        assert isinstance(fm["title"], str) and fm["title"].strip()
        assert isinstance(fm["description"], str) and fm["description"].strip()
        # We never emit a digest (which would require a 'resource' field).
        assert fm["type"] != "digest"


def test_empty_n_rejected(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        generate_corpus(tmp_path / "c", n=0, seed=0)
