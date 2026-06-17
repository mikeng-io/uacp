"""Tests for the Oracle aggregator."""
from __future__ import annotations


import engines.oracle.aggregator as agg
from engines.oracle.tier_config import OracleMode


def test_disabled_oracle_serves_floor(temp_uacp_root):
    result = agg.oracle_query(
        temp_uacp_root,
        phase="plan",
        project="proj",
        oracle_cfg={"enabled": False},
    )
    assert result["packets"] == []
    assert result["metadata"]["mode"] == OracleMode.NONE.value
    assert "disabled" in result["metadata"].get("note", "")


def test_none_mode_phase_returns_empty(temp_uacp_root):
    # "execute" maps to WRITEBACK which has no external retrieval
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


def test_full_phase_collects_runstate(temp_uacp_root):
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
    assert len(result["packets"]) >= 1
    assert any(p.source == "runstate" for p in result["packets"])
