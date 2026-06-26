"""LSP overlay + the 3-zone reconcile (P2, gap #1 / OD-1 / 10-freshness).

LSP is ALWAYS live, NEVER persisted: every reconcile-aware query attempts the overlay and is
fail-soft. These tests drive a FAKE injected overlay (live / conflict / clean) and FAULT-INJECT
it (None / raises) — no live Serena required. The six acceptance behaviours of P2:

  1. dirty file + live overlay         -> node 'live'; the overlay SUPERSEDES the stale SCIP row
  2. SCIP <-> overlay conflict          -> node 'unreconciled'; BOTH views surfaced, not blended
  3. clean file                         -> 'trusted'; the overlay is NOT consulted for it
  4. overlay absent (None)              -> query succeeds (trusted/stale) + lsp_degraded warning
  5. overlay raises mid-query           -> query STILL returns + lsp_degraded, no exception escapes
  6. across all of the above            -> NO source="lsp" row is ever written to the store
"""

from __future__ import annotations

import pytest

from codeflair import (
    Edge,
    ExpandResult,
    SerenaOverlay,
    Store,
    Symbol,
    content_hash,
    expand,
    load_serena_overlay,
    reconcile_overlay,
)
from codeflair.query import heatmap

# f.go is the DIRTY file (indexed hash is of ORIGINAL_F; the working bytes are edited);
# g.go is CLEAN (working bytes == indexed bytes).
ORIGINAL_F = b"package p\nfunc X() { S() }\n"
EDITED_F = b"package p\nfunc X() { S(); More() }\n"  # edited -> hash diverges -> stale
ORIGINAL_G = b"package p\nfunc Y() { S() }\n"


def _store() -> Store:
    """X (in dirty f.go) and Y (in clean g.go) both call seed S. Indexed file hashes are of
    the ORIGINAL bytes, so EDITED f.go reads 'stale' while unchanged g.go reads 'clean'."""
    s = Store()
    s.add_symbol(Symbol(symbol="S", file="s.go", name="S"))
    s.add_symbol(Symbol(symbol="X", file="f.go", name="X"))
    s.add_symbol(Symbol(symbol="Y", file="g.go", name="Y"))
    s.add_edge(Edge("X", "S", "calls", "scip"))  # X calls S -> caller of S
    s.add_edge(Edge("Y", "S", "calls", "scip"))  # Y calls S -> caller of S
    s.record_file("f.go", content_hash(ORIGINAL_F))
    s.record_file("g.go", content_hash(ORIGINAL_G))
    s.commit()
    return s


def _working(edited: bytes = EDITED_F) -> dict[str, bytes]:
    return {"f.go": edited, "g.go": ORIGINAL_G}


class FakeOverlay:
    """An injectable live overlay returning a fixed symbol view per file, and recording which
    files it was asked about (so a test can prove a CLEAN file is never consulted)."""

    def __init__(self, view: dict[str, set[str]]) -> None:
        self.view = view
        self.calls: list[str] = []

    def refs_defs(self, file: str, working_bytes: bytes):
        self.calls.append(file)
        return self.view.get(file, set())


class RaisingOverlay:
    """Fault injection: a provider that crashes mid-query (Serena dies)."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def refs_defs(self, file: str, working_bytes: bytes):
        self.calls.append(file)
        raise RuntimeError("serena exploded mid-query")


def _tags(res) -> dict[str, str]:
    return {e.symbol: e.freshness for e in res.entries}


# -- 1. dirty file + live overlay -> 'live', overlay supersedes the stale SCIP row ----------
def test_dirty_file_live_overlay_tags_live_and_supersedes_stale():
    s = _store()
    entries = heatmap(s, "S")  # reaches X (dirty) and Y (clean), both hop 1

    live = reconcile_overlay(s, entries, _working(), FakeOverlay({"f.go": {"X"}}))
    assert _tags(live)["X"] == "live"  # live overlay confirms X on the dirty file
    assert _tags(live)["Y"] == "trusted"  # clean file stays store-authoritative
    assert live.lsp_degraded is False

    # SUPERSEDE, made concrete: with NO live overlay the SAME dirty node is only 'stale'
    # (flagged, not patched). The live overlay's view is what promotes X to 'live' — it
    # supersedes the stale SCIP row instead of trusting it blindly.
    degraded = reconcile_overlay(s, entries, _working(), overlay=None)
    assert _tags(degraded)["X"] == "stale"
    assert _tags(live)["X"] != _tags(degraded)["X"]


# -- 2. SCIP <-> overlay conflict -> 'unreconciled', BOTH surfaced, not blended -------------
def test_conflict_tags_unreconciled_and_surfaces_both_without_blending():
    s = _store()
    entries = heatmap(s, "S")
    baseline = {e.symbol: e for e in entries}  # pre-reconcile node, for the no-blend check

    # the live overlay does NOT see X (it sees only OTHER) -> SCIP says X, LSP says not-X.
    res = reconcile_overlay(s, entries, _working(), FakeOverlay({"f.go": {"OTHER"}}))
    assert _tags(res)["X"] == "unreconciled"

    # BOTH views surfaced — the conflict carries the SCIP claim AND the live-LSP view.
    assert len(res.conflicts) == 1
    c = res.conflicts[0]
    assert c.file == "f.go"
    assert c.scip_symbols == ("X",)  # what the (stale) store claims
    assert c.overlay_symbols == ("OTHER",)  # what live LSP sees — kept distinct, not merged
    assert any("unreconciled" in w for w in res.warnings)

    # NOT blended — the kept node's score/via are untouched; only its freshness changed.
    x = next(e for e in res.entries if e.symbol == "X")
    assert x.score == baseline["X"].score
    assert x.via == baseline["X"].via == "calls/scip"


# -- 3. clean file -> 'trusted'; the overlay is NOT consulted for it ------------------------
def test_clean_file_is_trusted_and_overlay_not_consulted():
    s = _store()
    entries = heatmap(s, "S")
    fake = FakeOverlay({"f.go": {"X"}})

    res = reconcile_overlay(s, entries, _working(), fake)
    assert _tags(res)["Y"] == "trusted"  # g.go is clean -> store authoritative
    # the overlay was consulted for the DIRTY file only, never for the clean one
    assert "f.go" in fake.calls
    assert "g.go" not in fake.calls


# -- 4. overlay absent (None) -> succeeds (trusted/stale only) + lsp_degraded warning -------
def test_overlay_absent_degrades_two_zone_with_warning():
    s = _store()
    entries = heatmap(s, "S")

    res = reconcile_overlay(s, entries, _working(), overlay=None)
    tags = _tags(res)
    assert tags["X"] == "stale"  # dirty, no overlay -> flagged
    assert tags["Y"] == "trusted"  # clean
    assert set(tags.values()) <= {"trusted", "stale"}  # strictly two-zone — no live/unreconciled
    assert res.lsp_degraded is True
    assert res.conflicts == []
    assert any("lsp_degraded" in w for w in res.warnings)


# -- 5. overlay raises mid-query -> STILL returns + lsp_degraded, no exception escapes ------
def test_overlay_raising_mid_query_is_fail_soft():
    s = _store()
    entries = heatmap(s, "S")
    boom = RaisingOverlay()

    res = reconcile_overlay(s, entries, _working(), boom)  # must NOT raise
    assert boom.calls == ["f.go"]  # it WAS attempted (then crashed) on the dirty file
    assert _tags(res)["X"] == "stale"  # crashed -> degrade that file, flag it
    assert res.lsp_degraded is True
    assert any("lsp_degraded" in w for w in res.warnings)


# -- 6. NO source="lsp" row is ever written, across every path -----------------------------
def test_no_lsp_edge_is_ever_persisted():
    s = _store()
    entries = heatmap(s, "S")
    before = s.count_edges()

    # run every reconcile path against the same store
    reconcile_overlay(s, entries, _working(), FakeOverlay({"f.go": {"X"}}))  # live
    reconcile_overlay(s, entries, _working(), FakeOverlay({"f.go": {"OTHER"}}))  # unreconciled
    reconcile_overlay(s, entries, _working(), overlay=None)  # degraded
    reconcile_overlay(s, entries, _working(), RaisingOverlay())  # degraded (crash)

    assert s.count_edges() == before  # the reconcile writes nothing
    assert s.con.execute("SELECT COUNT(*) FROM edges WHERE source='lsp'").fetchone()[0] == 0
    # and the store itself refuses a persisted lsp edge (the enum is closed — P0/D3)
    with pytest.raises(ValueError, match="unknown edge source 'lsp'"):
        s.add_edge(Edge("X", "S", "calls", "lsp"))


# == wiring through expand() ================================================================
def test_expand_reconciles_when_working_files_given():
    s = _store()
    res = expand(s, "S", working_files=_working(), overlay=FakeOverlay({"f.go": {"X"}}))
    assert isinstance(res, ExpandResult)
    tags = {e.symbol: e.freshness for e in res.heatmap}
    assert tags["X"] == "live" and tags["Y"] == "trusted"
    assert res.lsp_degraded is False and res.warnings == [] and res.conflicts == []


def test_expand_wiring_surfaces_degrade_and_conflict():
    s = _store()
    degraded = expand(s, "S", working_files=_working(), overlay=None)
    assert degraded.lsp_degraded is True
    assert any("lsp_degraded" in w for w in degraded.warnings)

    conflict = expand(s, "S", working_files=_working(), overlay=FakeOverlay({"f.go": {"Z"}}))
    assert {e.symbol for e in conflict.heatmap if e.freshness == "unreconciled"} == {"X"}
    assert len(conflict.conflicts) == 1


def test_expand_without_working_files_is_backward_compatible():
    """No working_files -> reconcile skipped entirely: every node 'trusted', no degrade,
    no warnings, no conflicts — byte-identical to the store-authoritative path (P0/P1)."""
    s = _store()
    res = expand(s, "S")
    assert all(e.freshness == "trusted" for e in res.heatmap)
    assert res.lsp_degraded is False
    assert res.warnings == [] and res.conflicts == []
    # an unindexed-file node also stays trusted when no bytes are supplied to compare it
    res2 = expand(s, "S", working_files={}, overlay=None)
    assert all(e.freshness == "trusted" for e in res2.heatmap)
    assert res2.lsp_degraded is False  # nothing dirty needed the overlay -> not degraded


# == the real Serena adapter (import-guarded; Serena is absent in the dev venv) ============
def test_load_serena_overlay_returns_none_when_serena_absent():
    """CF-D9: codeflair never hard-depends on Serena. With Serena unimportable (the dev venv
    and any host without uv/uvx), provisioning returns None -> the orchestrator passes
    overlay=None and the query degrades fail-soft. It must NOT raise ImportError."""
    assert load_serena_overlay() is None


def test_serena_overlay_unmapped_refs_defs_degrades_fail_soft():
    """The Serena adapter's Serena->SCIP-descriptor mapping is the gated follow-on, so an
    un-mapped SerenaOverlay raises NotImplementedError from refs_defs. The reconcile catches
    it like any provider failure: the query degrades fail-soft, never crashes."""
    overlay = SerenaOverlay(client=object())
    with pytest.raises(NotImplementedError):
        list(overlay.refs_defs("f.go", EDITED_F))

    s = _store()
    res = reconcile_overlay(s, heatmap(s, "S"), _working(), overlay)  # must NOT raise
    assert _tags(res)["X"] == "stale"
    assert res.lsp_degraded is True
