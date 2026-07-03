"""Unit tests for the BASELINE witness wire parser (design node 04).

``_parse_baseline_facts`` strictly parses the ``baseline_refs`` wire (incl. the mode key
check) and fails closed on garble / a diff-mode response. The full derivation envelope is
exercised e2e via the stub CLI in test_scope_conformance.py."""

from __future__ import annotations

import json

from engines.io.witnessio import BaselineFacts, _parse_baseline_facts


def _baseline_wire(**over) -> dict:
    wire = {
        "mode": "baseline_refs",
        "graph_stamp": {"commit": "deadbeef", "tree_token": "deadbeef"},
        "ingestion": "scip",
        "declared": [{"file": "src/a.py", "name": "Alpha", "resolved": True}],
        "neighborhood": [
            {
                "src": {"file": "src/a.py", "name": "Alpha"},
                "dst": {"file": "src/b.py", "name": "Beta"},
                "reason": "calls",
            }
        ],
        "inbound_counts": {"src/a.py:Alpha": 3},
        "workspace_dirty": False,
    }
    wire.update(over)
    return wire


def test_parses_valid_baseline():
    facts, err = _parse_baseline_facts(json.dumps(_baseline_wire()))
    assert err is None
    assert isinstance(facts, BaselineFacts)
    assert facts.ingestion == "scip"
    assert facts.workspace_dirty is False
    assert facts.inbound_counts == {"src/a.py:Alpha": 3}
    assert len(facts.declared) == 1
    assert len(facts.neighborhood) == 1


def test_rejects_wrong_mode():
    # A DIFF-mode response must never be read as a baseline one — mode key check.
    facts, err = _parse_baseline_facts(json.dumps(_baseline_wire(mode="witness")))
    assert facts is None
    assert err is not None and "baseline_refs" in err


def test_rejects_missing_mode():
    wire = _baseline_wire()
    del wire["mode"]
    facts, err = _parse_baseline_facts(json.dumps(wire))
    assert facts is None
    assert err is not None and "mode" in err


def test_rejects_non_json():
    facts, err = _parse_baseline_facts("not json {[")
    assert facts is None
    assert err is not None


def test_rejects_malformed_declared():
    facts, err = _parse_baseline_facts(
        json.dumps(_baseline_wire(declared=[{"file": "src/a.py", "name": "Alpha"}]))  # no resolved
    )
    assert facts is None
    assert err is not None and "declared" in err


def test_rejects_malformed_neighborhood_endpoint():
    bad = _baseline_wire(neighborhood=[{"src": {"file": "src/a.py"}, "dst": {}, "reason": "calls"}])
    facts, err = _parse_baseline_facts(json.dumps(bad))
    assert facts is None
    assert err is not None and "neighborhood" in err


def test_workspace_dirty_and_inbound_counts_optional():
    wire = _baseline_wire()
    del wire["workspace_dirty"]
    del wire["inbound_counts"]
    facts, err = _parse_baseline_facts(json.dumps(wire))
    assert err is None
    assert facts is not None
    assert facts.workspace_dirty is False  # defaulted
    assert facts.inbound_counts == {}


def test_workspace_dirty_true_preserved():
    facts, err = _parse_baseline_facts(json.dumps(_baseline_wire(workspace_dirty=True)))
    assert err is None and facts is not None
    assert facts.workspace_dirty is True


def test_reason_lenient_but_endpoints_strict():
    # The forecast reasons over hop-1 MEMBERSHIP, so an unusual reason string is tolerated
    # (endpoints are still validated).
    facts, err = _parse_baseline_facts(
        json.dumps(
            _baseline_wire(
                neighborhood=[
                    {
                        "src": {"file": "src/a.py", "name": "Alpha"},
                        "dst": {"file": "src/b.py", "name": "Beta"},
                        "reason": "imports",  # not in the diff-mode enum, but tolerated here
                    }
                ]
            )
        )
    )
    assert err is None
    assert facts is not None and len(facts.neighborhood) == 1
