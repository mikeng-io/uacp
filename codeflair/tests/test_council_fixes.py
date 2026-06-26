"""Cross-provider final-council fixes (F1–F6): a failing-repro-then-fix test per finding.

F1 — delta GC of phantom symbols + dangling cross-file edges on intra-file deletion.
F2 — index_repo TOCTOU threshold is injectable -> deterministic freshness by construction.
F3 — replay reproduces the POST-reconcile ranking (no re-added bonus on an unreconciled node).
F4 — a failed/empty index build does NOT advance the watermark (surfaced nonzero).
F5 — the unreconciled bonus-strip is applied BEFORE the top-k cut (rightful node not displaced).
F6 — the eval baseline disclosure (circular by-construction) is unmistakable.
"""

from __future__ import annotations

import json
import os
import time

import codeflair.cli as cli
import codeflair.scip_ingest as si
from codeflair import Edge, Store, Symbol, content_hash, expand, replay
from codeflair.delta import FileIndex, delta_reindex
from codeflair.eval import EvalReport, format_report
from codeflair.probes import ProbeRegistry
from codeflair.query import HeatmapEntry
from codeflair.scip_ingest import ingest_scip_json
from codeflair.store import default_store_path

# --------------------------------------------------------------------------- #
# F1 — phantom symbol + dangling cross-file edge GC on intra-file deletion
# --------------------------------------------------------------------------- #
_M = "scip-go gomod example.com/m v1.0.0 `example.com/m/p`"
_A, _B, _X, _Y = f"{_M}/A().", f"{_M}/B().", f"{_M}/X().", f"{_M}/Y()."
_DEF, _REF = 1, 0


def _occ(symbol: str, line: int, role: int) -> dict:
    return {"symbol": symbol, "range": [line, 0, 10], "symbol_roles": role}


def test_f1_delta_gcs_phantom_symbol_and_dangling_crossfile_edge():
    """REPRO: f.go defines {A,B}; g.go has edge Y->B; f.go is edited to drop B (add X). After
    a delta of f.go ONLY, B must be a gone (phantom) symbol AND Y->B (in untouched g.go) must
    be gone — matching a full rebuild's symbol set {A,X,Y}. Before the fix B + Y->B leak."""
    s = Store()
    s.set_watermark("c0", "t0")
    index = {
        "documents": [
            {"relative_path": "f.go", "occurrences": [_occ(_A, 1, _DEF), _occ(_B, 2, _DEF)]},
            {"relative_path": "g.go", "occurrences": [_occ(_Y, 1, _DEF), _occ(_B, 2, _REF)]},
        ]
    }
    ingest_scip_json(s, index, file_contents={"f.go": b"f0", "g.go": b"g0"}, commit_sha="c0")

    # precondition: B is a real symbol and the cross-file edge Y->B exists
    assert s.symbol(_B) is not None
    assert s.con.execute("SELECT 1 FROM edges WHERE src=? AND dst=?", (_Y, _B)).fetchone()

    def producer(path: str, data: bytes) -> FileIndex:
        # f.go now defines {A, X} — B is gone from f.go
        return FileIndex(
            symbols=[
                Symbol(symbol=_A, lang="go", file="f.go", name="A", line=1),
                Symbol(symbol=_X, lang="go", file="f.go", name="X", line=2),
            ],
            edges=[Edge(src=_A, dst=_X, rel="calls", source="scip", provenance="parsed")],
        )

    delta_reindex(
        s,
        {"f.go": b"f1", "g.go": b"g0"},  # only f.go changed; g.go is byte-identical
        source="scip",
        reindex_file=producer,
        commit_sha="c1",
        built_at="t1",
    )

    assert s.symbol(_B) is None  # phantom symbol GC'd (no source defines it)
    assert s.con.execute("SELECT 1 FROM edges WHERE src=? AND dst=?", (_Y, _B)).fetchone() is None
    repo_syms = {r[0] for r in s.con.execute("SELECT symbol FROM symbols WHERE file != ''")}
    assert repo_syms == {_A, _X, _Y}  # matches a full rebuild


def test_f1_multi_source_ownership_guard_keeps_a_symbol_another_source_defines():
    """A symbol the scip delta drops is KEPT if another source (tree_sitter) still defines it —
    the multi-source guard. Only when NO source owns it is it GC'd."""
    s = Store()
    s.set_watermark("c0", "t0")
    index = {"documents": [{"relative_path": "f.go", "occurrences": [_occ(_B, 1, _DEF)]}]}
    ingest_scip_json(s, index, file_contents={"f.go": b"f0"}, commit_sha="c0")
    # tree_sitter ALSO defines B (a second owner)
    s.record_symbol_source("tree_sitter", _B)
    s.commit()

    def producer(path: str, data: bytes) -> FileIndex:
        return FileIndex(symbols=[], edges=[])  # scip no longer defines B

    delta_reindex(
        s, {"f.go": b"f1"}, source="scip", reindex_file=producer, commit_sha="c1", built_at="t1"
    )
    assert s.symbol(_B) is not None  # tree_sitter still owns B -> kept
    assert s.symbol_owners(_B) == {"tree_sitter"}  # scip ownership released, tree_sitter remains


# --------------------------------------------------------------------------- #
# F2 — index_repo TOCTOU threshold injected -> deterministic freshness
# --------------------------------------------------------------------------- #
def test_f2_index_repo_freshness_deterministic_with_injected_threshold(tmp_path, monkeypatch):
    """REPRO: the F5 mtime-withhold threshold must be INJECTABLE (no internal time.time()), so
    freshness population is deterministic by construction. Two runs with the same injected
    threshold produce identical rows; the threshold deterministically controls the withhold."""
    repo = tmp_path
    (repo / "a.go").write_bytes(b"package p\n")
    (repo / "b.go").write_bytes(b"package q\n")
    index = {
        "documents": [
            {"relative_path": "a.go", "occurrences": [_occ(_A, 1, _DEF)]},
            {"relative_path": "b.go", "occurrences": [_occ(_B, 1, _DEF)]},
        ]
    }
    monkeypatch.setattr(si, "_indexer_cmd", lambda *a, **k: ["true"])
    monkeypatch.setattr(si, "_resolve_bin", lambda b: "true")

    def fake_run(cmd, **kw):
        class _R:
            stdout = json.dumps(index).encode()
            returncode = 0

        return _R()

    monkeypatch.setattr(si.subprocess, "run", fake_run)

    future = time.time() + 10_000.0  # threshold AFTER all mtimes -> nothing withheld
    s1, s2 = Store(), Store()
    si.index_repo(s1, str(repo), "go", index_started=future, commit_sha="c")
    si.index_repo(s2, str(repo), "go", index_started=future, commit_sha="c")
    rows1 = sorted(s1.con.execute("SELECT source,file,content_hash FROM freshness"))
    rows2 = sorted(s2.con.execute("SELECT source,file,content_hash FROM freshness"))
    assert rows1 == rows2 and len(rows1) == 2  # deterministic; both files fresh

    s3 = Store()
    si.index_repo(s3, str(repo), "go", index_started=0.0, commit_sha="c")  # before all mtimes
    assert s3.con.execute("SELECT COUNT(*) FROM freshness").fetchone()[0] == 0  # all withheld


# --------------------------------------------------------------------------- #
# F3 / F5 — overlay reconcile: strip-before-cut + replayable post-reconcile rank
# --------------------------------------------------------------------------- #
class _FixedProbe:
    """A probe that yields a fixed list of candidates (full control over corroboration)."""

    kind = "precise"

    def __init__(self, name: str, entries: list[HeatmapEntry]) -> None:
        self.name = name
        self._entries = entries

    def expand(self, ctx):
        return list(self._entries)


class _Overlay:
    def __init__(self, view: dict[str, set[str]]) -> None:
        self._view = view

    def refs_defs(self, file: str, working_bytes: bytes):
        return self._view.get(file, set())


def _conflict_store() -> Store:
    """P lives in a dirty file the overlay will NOT confirm (-> unreconciled); Q lives in a
    clean/untouched file (-> trusted). scip recorded a clean hash for p.go."""
    s = Store()
    s.add_symbol(Symbol(symbol="P", file="p.go", name="P"))
    s.add_symbol(Symbol(symbol="Q", file="q.go", name="Q"))
    s.record_freshness("scip", "p.go", content_hash(b"clean"))
    s.commit()
    return s


def _two_probe_registry() -> ProbeRegistry:
    # P found by BOTH probes (corroboration -> agreement bonus); Q found by ONE.
    p = HeatmapEntry(symbol="P", hop=1, score=0.40, via="x/scip", source="scip")
    q = HeatmapEntry(symbol="Q", hop=1, score=0.45, via="y", source="")
    p2 = HeatmapEntry(symbol="P", hop=1, score=0.40, via="x/scip", source="scip")
    reg = ProbeRegistry()
    reg.register(_FixedProbe("a", [p, q]))
    reg.register(_FixedProbe("b", [p2]))
    return reg


def test_f5_unreconciled_strip_applied_before_topk_cut():
    """REPRO: P is promoted into the top-1 slot purely by the corroboration bonus (0.50 > Q
    0.45). The overlay tags P unreconciled and strips the bonus (P -> 0.40). With the strip
    applied BEFORE the top-k cut, the rightful node Q wins the single slot. Before the fix
    (strip after cut) P kept its slot."""
    s = _conflict_store()
    res = expand(
        s,
        "S",
        registry=_two_probe_registry(),
        working_files={"p.go": b"dirty"},
        overlay=_Overlay({}),  # overlay does NOT see P -> unreconciled
        k=1,
    )
    assert [e.symbol for e in res.heatmap] == ["Q"]  # rightful node, not bonus-promoted P


def test_f3_replay_reproduces_post_reconcile_ranking_on_overlay_query():
    """REPRO: on an overlay query, P is unreconciled and its bonus stripped (final score 0.40).
    replay(trace) must reproduce that EXACT ranking/scores — not re-add the bonus (0.50). Before
    the fix replay diverged (live P=0.40 vs replay P=0.50)."""
    s = _conflict_store()
    res = expand(
        s,
        "S",
        registry=_two_probe_registry(),
        working_files={"p.go": b"dirty"},
        overlay=_Overlay({}),
        k=2,
        capture_trace=True,
    )
    # P is tagged unreconciled and its bonus is stripped in the live result
    p = next(e for e in res.heatmap if e.symbol == "P")
    assert p.freshness == "unreconciled" and p.score == 0.40
    assert res.trace is not None

    replayed = replay(res.trace)
    assert [(n.symbol, n.score) for n in replayed] == [(e.symbol, e.score) for e in res.heatmap]


# --------------------------------------------------------------------------- #
# F4 — a failed index build does not advance the watermark
# --------------------------------------------------------------------------- #
def test_f4_failed_index_does_not_advance_watermark(tmp_path, monkeypatch):
    """REPRO: when the SCIP ingest RAISES and nothing else indexes anything, build_index must
    NOT advance the watermark and the CLI must exit nonzero. Before the fix it swallowed the
    error and watermarked a partial/empty index authoritative-for-HEAD."""
    def boom(*a, **k):
        raise RuntimeError("scip exploded mid-ingest")

    monkeypatch.setattr(cli, "index_repo", boom)
    rc = cli.main(["index", str(tmp_path), "--lang", "python"])  # empty dir -> nothing indexed
    assert rc != 0  # surfaced as a nonzero exit

    db = default_store_path(str(tmp_path))
    assert os.path.exists(db)
    with Store(db, read_only=True) as s:
        assert s.watermark() is None  # no authoritative-for-HEAD watermark on failure


def test_f4_partial_floor_build_still_watermarks_and_succeeds(tmp_path):
    """The legitimate degrade-to-floor path is preserved: SCIP absent but the shared-string
    floor produced a coupling -> the build IS a valid (floor-level) index of HEAD, watermarked,
    indexed=True, rc 0. (Guards against F4 over-correcting into a regression.)"""
    (tmp_path / "h.py").write_text('R = "/api/v1/cancel-order"\n')
    (tmp_path / "k.py").write_text('u = "/api/v1/cancel-order"\n')
    summary = cli.build_index(str(tmp_path), lang="python")
    assert summary["indexed"] is True
    with Store(default_store_path(str(tmp_path)), read_only=True) as s:
        assert s.watermark() is not None


# --------------------------------------------------------------------------- #
# F6 — the eval baseline disclosure is unmistakable
# --------------------------------------------------------------------------- #
def test_f6_eval_report_discloses_circular_baseline():
    report = EvalReport(
        n_pairs=1,
        n_exercised=1,
        n_gated=0,
        baseline_overall=0.833,
        baseline_parsed=1.0,
        baseline_inferred=0.5,
        parsed_gt=2,
        parsed_hit=2,
        inferred_gt=2,
        inferred_hit=1,
    )
    text = format_report(report)
    assert "CIRCULAR" in text  # unmistakable, not buried
    assert "do NOT cite" in text  # explicit instruction not to read it as retrieval quality
