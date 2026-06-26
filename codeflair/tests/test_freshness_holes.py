"""Council repro tests for the STALE-SERVED-AS-FRESH holes in the P1+P2 freshness layer.

Each test targets one finding (F1..F5) and asserts the FIXED behaviour; each fails if its
fix is reverted (the assertion pins the exact hole). The shared failure mode the layer exists
to prevent: a stale edge/symbol returned with a 'trusted'/clean tag. Non-vacuity: every test
also shows the pre-fix signal (e.g. the global hash that the old path WOULD have trusted).
"""

from __future__ import annotations

import os
from pathlib import Path

from codeflair import (
    Edge,
    Store,
    Symbol,
    content_hash,
    expand,
    reconcile_overlay,
)
from codeflair.query import heatmap
from codeflair.scip_ingest import _modified_during_index, _read_repo_bytes

ORIGINAL = b"package p\nfunc X() { S() }\n"
EDITED = b"package p\nfunc X() { S(); More() }\n"


class _FakeOverlay:
    def __init__(self, view: dict[str, set[str]]) -> None:
        self.view = view

    def refs_defs(self, file: str, working_bytes: bytes):
        return self.view.get(file, set())


def _tags(res) -> dict[str, str]:
    return {e.symbol: e.freshness for e in res.entries}


# == F1 [blocker] per-source freshness is stored but never read =============================
def test_f1_source_scoped_freshness_catches_stale_scip_edge_after_other_source_reingest():
    """SCIP indexes X->S in f.go; f.go is edited; tree-sitter re-ingests f.go (overwriting the
    GLOBAL files.hash to the NEW bytes). The OLD reconcile compared the global hash, saw it
    match the working bytes, and tagged X 'trusted' — serving the stale SCIP edge as fresh.
    The fix judges X against ITS OWN source's (scip) recorded hash, which still reflects the
    pre-edit content -> X is correctly NOT trusted."""
    s = Store()
    s.add_symbol(Symbol(symbol="S", file="s.go", name="S"))
    s.add_symbol(Symbol(symbol="X", file="f.go", name="X"))
    s.add_edge(Edge("X", "S", "calls", "scip"))
    # scip's view of f.go is the ORIGINAL (pre-edit) content
    s.record_freshness("scip", "f.go", content_hash(ORIGINAL))
    # tree-sitter later re-ingests the EDITED file: it advances ITS own row AND the global one
    s.record_freshness("tree_sitter", "f.go", content_hash(EDITED))
    s.record_file("f.go", content_hash(EDITED))  # global files.hash now = post-edit bytes
    s.commit()

    # non-vacuity: the global hash DOES match the working bytes — the exact trap the old
    # global-hash reconcile fell into (it would have said "clean" -> trusted).
    assert s.file_hash("f.go") == content_hash(EDITED)

    res = reconcile_overlay(s, heatmap(s, "S"), {"f.go": EDITED}, overlay=None)
    assert _tags(res)["X"] != "trusted"  # the stale SCIP edge is NOT served as fresh
    assert _tags(res)["X"] == "stale"  # dirty for scip + no overlay -> flagged
    assert res.lsp_degraded is True


# == F2 [major] 'unknown' hash collapsed into 'trusted' =====================================
def test_f2_unknown_hash_is_unverified_not_trusted():
    """A symbol whose file has NO recorded hash, with divergent working bytes supplied, was
    tagged 'trusted' (unknown collapsed into clean). 'Cannot certify' is the opposite of
    clean: the fix tags it 'unverified' and warns, never 'trusted'."""
    s = Store()
    s.add_symbol(Symbol(symbol="S", file="s.go", name="S"))
    s.add_symbol(Symbol(symbol="X", file="f.go", name="X"))
    s.add_edge(Edge("X", "S", "calls", "scip"))  # X's source is scip, but no freshness row
    s.commit()
    assert s.source_file_hash("scip", "f.go") is None  # genuinely nothing to certify against

    res = reconcile_overlay(s, heatmap(s, "S"), {"f.go": b"anything at all"}, overlay=None)
    assert _tags(res)["X"] == "unverified"
    assert _tags(res)["X"] != "trusted"
    assert any("unverified" in w for w in res.warnings)


# == F3 [blocker/major] 'live' certifies presence, not edge currency ========================
def test_f3_live_is_presence_only_and_warns_edge_currency_unverified():
    """A presence-only overlay confirms the symbol still EXISTS, not that the edge that put
    the node in the blast radius is current. 'live' must therefore not be read as full
    freshness: the fix keeps the tag but emits an explicit edge-currency-unverified warning."""
    s = Store()
    s.add_symbol(Symbol(symbol="S", file="s.go", name="S"))
    s.add_symbol(Symbol(symbol="X", file="f.go", name="X"))
    s.add_edge(Edge("X", "S", "calls", "scip"))
    s.record_freshness("scip", "f.go", content_hash(ORIGINAL))
    s.commit()

    res = reconcile_overlay(s, heatmap(s, "S"), {"f.go": EDITED}, _FakeOverlay({"f.go": {"X"}}))
    assert _tags(res)["X"] == "live"
    live_warnings = [w for w in res.warnings if w.startswith("live:")]
    assert live_warnings, "a 'live' node must surface that edge-currency is unverified"
    assert "edge-currency" in live_warnings[0]


# == F4 [major] overlay-only NEW symbols silently dropped ===================================
def test_f4_overlay_only_new_symbol_is_surfaced_not_dropped():
    """The edit adds a NEW caller the store has never seen. The overlay sees it in the dirty
    file; the old reconcile only re-tagged existing nodes, so the new dependency vanished with
    no warning. The fix surfaces it on overlay_only and warns — even on the clean 'live' path
    where no conflict is emitted."""
    s = Store()
    s.add_symbol(Symbol(symbol="S", file="s.go", name="S"))
    s.add_symbol(Symbol(symbol="X", file="f.go", name="X"))
    s.add_edge(Edge("X", "S", "calls", "scip"))
    s.record_freshness("scip", "f.go", content_hash(ORIGINAL))
    s.commit()

    # overlay sees X (known) AND NEWCALLER (a brand-new symbol the store lacks)
    overlay = _FakeOverlay({"f.go": {"X", "NEWCALLER"}})
    res = reconcile_overlay(s, heatmap(s, "S"), {"f.go": EDITED}, overlay)
    assert _tags(res)["X"] == "live"  # the clean-live path: no conflict emitted
    assert "NEWCALLER" in res.overlay_only  # ...yet the new dependency is NOT dropped
    assert res.conflicts == []
    assert any("overlay_only" in w for w in res.warnings)

    # and it threads through expand()
    er = expand(s, "S", working_files={"f.go": EDITED}, overlay=overlay)
    assert "NEWCALLER" in er.overlay_only


# == F5 [major] index-time TOCTOU: bytes read after the indexer ran =========================
def test_f5_modified_during_index_is_pure_and_flags_suspects():
    """A file whose mtime is at/after index start was edited DURING the index window, so its
    SCIP edges and the bytes we hash may disagree. Pure + deterministic detection."""
    mtimes = {"stable.go": 1000.0, "edited.go": 3000.0}
    assert _modified_during_index(mtimes, 2000.0) == {"edited.go"}
    assert _modified_during_index(mtimes, 5000.0) == set()  # all predate index start
    assert _modified_during_index({"x.go": 2000.0}, 2000.0) == {"x.go"}  # boundary = suspect


def test_f5_read_repo_bytes_withholds_freshness_for_files_edited_during_index(tmp_path: Path):
    """End-to-end of the F5 fix at the seam: a file modified during indexing is EXCLUDED from
    the hashed bytes, so it gets no freshness row and a later query treats it 'unverified'
    rather than trusting its possibly-stale SCIP edges. Without the guard it is included (the
    hole) — proving the guard is what closes it."""
    (tmp_path / "stable.go").write_bytes(b"package p\nfunc Stable() {}\n")
    (tmp_path / "edited.go").write_bytes(b"package p\nfunc Edited() {}\n")
    index = {
        "documents": [
            {"relative_path": "stable.go", "occurrences": []},
            {"relative_path": "edited.go", "occurrences": []},
        ]
    }
    # stable.go predates index start; edited.go was touched DURING the index window
    os.utime(tmp_path / "stable.go", (1000.0, 1000.0))
    os.utime(tmp_path / "edited.go", (3000.0, 3000.0))
    index_started = 2000.0

    guarded = _read_repo_bytes(str(tmp_path), index, index_started=index_started)
    assert set(guarded) == {"stable.go"}  # the suspect file's freshness is withheld

    # the hole, made explicit: with NO guard the mid-index-edited file IS hashed and would be
    # recorded as fresh, vindicating its stale SCIP edges.
    unguarded = _read_repo_bytes(str(tmp_path), index, index_started=None)
    assert set(unguarded) == {"stable.go", "edited.go"}
