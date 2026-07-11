"""Tests for the Oracle aggregator."""
from __future__ import annotations


import engines.oracle.aggregator as agg
from engines.oracle.tier_config import OracleMode, mode_for_phase


def test_disabled_oracle_serves_floor(temp_uacp_root):
    # #100: on a RETRIEVAL phase, a disabled oracle now serves the DETERMINISTIC corpus
    # floor (empty here — no corpus seeded), reporting the phase's real mode (plan->full)
    # rather than NONE, with the floor note. (Content-serving is covered by
    # test_deterministic_floor.) Retrieval is no longer silenced just because the vector
    # store is off.
    result = agg.oracle_query(
        temp_uacp_root,
        phase="plan",
        project="proj",
        oracle_cfg={"enabled": False},
    )
    assert result["packets"] == []  # empty corpus -> empty floor
    assert result["metadata"]["mode"] == mode_for_phase("plan").value  # phase mode, not NONE
    assert "floor" in result["metadata"].get("note", "")
    assert "disabled" in result["metadata"].get("note", "")


def test_none_mode_phase_returns_empty(temp_uacp_root):
    # "execute" maps to NONE which has no external retrieval
    result = agg.oracle_query(
        temp_uacp_root,
        phase="execute",
        project="proj",
        oracle_cfg={"enabled": True},
    )
    assert result["packets"] == []
    assert "no external retrieval" in result["metadata"].get("note", "")


def test_unreachable_source_is_logged_not_fatal(temp_uacp_root, monkeypatch):
    """Monkeypatch _semantic_packets to throw OSError — must appear in sources_skipped."""
    monkeypatch.setattr(agg, "_semantic_packets", lambda *a, **k: (_ for _ in ()).throw(OSError("unreachable")))

    result = agg.oracle_query(
        temp_uacp_root,
        phase="plan",
        project="proj",
        oracle_cfg={"enabled": True},
    )
    assert "semantic" in result["metadata"]["sources_skipped"]
    # Should not raise
    assert "packets" in result


def test_advisory_phase_returns_metadata_mode(temp_uacp_root):
    result = agg.oracle_query(
        temp_uacp_root,
        phase="triage",
        project="proj",
        oracle_cfg={"enabled": True},
    )
    assert result["metadata"]["mode"] == OracleMode.ADVISORY.value


def test_full_phase_never_reads_run_state(temp_uacp_root):
    """Boundary: the oracle must NOT surface run-state packets.

    Run manifests under .uacp/state/runs/ belong to the state engine, not the
    Oracle. A FULL-tier query with manifests present must still emit zero
    'runstate' packets — the only sources are honcho (advisory) and the semantic
    corpus pipeline (skipped here: no vector store in the floor env).
    """
    import yaml
    runs_dir = temp_uacp_root / ".uacp" / "state" / "runs"
    (runs_dir / "run-001.yaml").write_text(yaml.dump({
        "project": "proj",
        "phase": "plan",
        "status": "active",
    }))

    result = agg.oracle_query(
        temp_uacp_root,
        phase="plan",
        project="proj",
        oracle_cfg={"enabled": True},
    )
    assert not any(p.source == "runstate" for p in result["packets"])
    assert "runstate" not in result["metadata"]["sources_skipped"]
