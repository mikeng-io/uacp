"""#100 read-floor: the deterministic corpus tier surfaces lessons/knowledge even when
the semantic Oracle is OFF ([oracle].enabled=false) — retrieval is never empty just
because the vector store is absent. No ML deps on this path (the floor guarantee)."""

from __future__ import annotations

import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parents[3] / "skills" / "uacp-core" / "scripts"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from engines.domain.corpus import KnowledgeItem, Lesson  # noqa: E402
from engines.oracle.aggregator import oracle_query  # noqa: E402
from engines.oracle.deterministic import deterministic_corpus_packets  # noqa: E402


def _write_lesson(root: Path, **kw) -> None:
    d = root / ".uacp" / "lessons"
    d.mkdir(parents=True, exist_ok=True)
    lesson = Lesson(**kw)
    (d / f"{lesson.id}.md").write_text(lesson.to_okf(), encoding="utf-8")


def _write_knowledge(root: Path, **kw) -> None:
    d = root / ".uacp" / "knowledge"
    d.mkdir(parents=True, exist_ok=True)
    item = KnowledgeItem(**kw)
    (d / f"{item.id}.md").write_text(item.to_okf(), encoding="utf-8")


# ------------------------------------------------------- the floor fires when disabled
def test_oracle_query_returns_floor_when_disabled(temp_uacp_root: Path):
    """oracle_query with [oracle].enabled=false previously returned []; now it returns the
    deterministic corpus floor so retrieval is never empty on a fresh clone."""
    _write_lesson(
        temp_uacp_root,
        id="governed-writer-discipline",
        title="Use governed writers",
        project="uacp",
        domains=["lifecycle"],
        body="Never raw-write .uacp state.",
    )
    _write_knowledge(
        temp_uacp_root,
        id="lifecycle-pattern",
        title="Lifecycle pattern",
        type="pattern",
        domains=["lifecycle"],
        scope="shared",
        body="TRIAGE-first governance.",
    )
    out = oracle_query(
        temp_uacp_root, phase="triage", project="uacp", domains=["lifecycle"], oracle_cfg=None
    )
    ids = {p.payload["id"] for p in out["packets"]}
    assert "governed-writer-discipline" in ids, out["metadata"]  # lesson surfaces
    assert "lifecycle-pattern" in ids, out["metadata"]  # shared knowledge surfaces
    assert out["metadata"]["note"] == "deterministic corpus floor (oracle disabled)", out
    # advisory trust (heuristic, not verified).
    assert all(p.trust_class.value == "advisory" for p in out["packets"])


def test_floor_ranks_domain_and_keyword_matches_above_others(temp_uacp_root: Path):
    _write_lesson(
        temp_uacp_root,
        id="relevant",
        title="lock ordering",
        project="uacp",
        domains=["concurrency"],
        body="acquire the outer lock first",
        bes=0.9,
    )
    _write_lesson(
        temp_uacp_root,
        id="offtopic",
        title="something else",
        project="uacp",
        domains=["docs"],
        body="unrelated content",
        bes=0.9,
    )
    packets = deterministic_corpus_packets(
        temp_uacp_root, "uacp", domains=["concurrency"], query="lock ordering"
    )
    assert packets, "floor returned nothing for a matching query"
    assert packets[0].payload["id"] == "relevant", [p.payload["id"] for p in packets]
    assert "offtopic" not in {p.payload["id"] for p in packets}, "off-domain lesson surfaced"


def test_floor_scopes_by_project(temp_uacp_root: Path):
    _write_lesson(temp_uacp_root, id="mine", title="t", project="uacp", domains=["x"])
    _write_lesson(temp_uacp_root, id="theirs", title="t", project="other-proj", domains=["x"])
    ids = {
        p.payload["id"] for p in deterministic_corpus_packets(temp_uacp_root, "uacp", domains=["x"])
    }
    assert "mine" in ids and "theirs" not in ids, ids


def test_floor_surfaces_top_bes_when_unfiltered(temp_uacp_root: Path):
    _write_lesson(temp_uacp_root, id="weak", title="t", project="uacp", bes=0.2)
    _write_lesson(temp_uacp_root, id="strong", title="t", project="uacp", bes=0.95)
    packets = deterministic_corpus_packets(temp_uacp_root, "uacp")  # no domains, no query
    assert packets[0].payload["id"] == "strong", [p.payload["id"] for p in packets]


def test_floor_empty_corpus_returns_nothing(temp_uacp_root: Path):
    assert deterministic_corpus_packets(temp_uacp_root, "uacp", query="anything") == []


def test_floor_import_is_ml_free():
    """The floor guarantee: engines.oracle.deterministic must import without any ML deps
    (lancedb / llama_cpp / httpx), so it runs on a bare clone."""
    import importlib

    mod = importlib.import_module("engines.oracle.deterministic")
    loaded = set(sys.modules)
    for heavy in ("lancedb", "llama_cpp", "httpx"):
        assert heavy not in loaded or getattr(mod, heavy, None) is None, (
            f"deterministic floor must not pull in {heavy}"
        )
