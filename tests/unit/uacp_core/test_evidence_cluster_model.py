"""Unit tests for the EvidenceCluster domain model (Slice 4a).

These tests assert the codified schema from config/evidence-clusters.yaml:
- ClusterState Literal covers exactly the 5 states
- EvidenceCluster validates a correct artifact and rejects bad state / missing required fields
- INVARIANT_CLUSTER_FAMILIES matches the 6 invariant=true families from the YAML
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from typing import get_args

from engines.domain import ClusterState, EvidenceCluster, INVARIANT_CLUSTER_FAMILIES


# ---------------------------------------------------------------------------
# ClusterState enum
# ---------------------------------------------------------------------------

def test_cluster_state_has_exactly_five_values():
    assert set(get_args(ClusterState)) == {"pass", "warn", "block", "not_applicable", "deferred"}


# ---------------------------------------------------------------------------
# EvidenceCluster — happy path
# ---------------------------------------------------------------------------

VALID_CLUSTER: dict = {
    "cluster_id": "verify.runtime_validation",
    "phase": "verify",
    "family": "verification_strategy",
    "purpose": "Validate that a completed runtime-facing change behaves as intended.",
    "state": "pass",
    "findings": [{"severity": "info", "summary": "All checks passed."}],
}


def test_evidence_cluster_accepts_valid_artifact():
    ec = EvidenceCluster.model_validate(VALID_CLUSTER)
    assert ec.cluster_id == "verify.runtime_validation"
    assert ec.state == "pass"


def test_evidence_cluster_allows_extra_fields():
    data = {**VALID_CLUSTER, "trigger_conditions": ["artifact changes runtime"], "concurrency": {"can_run_parallel": True}}
    ec = EvidenceCluster.model_validate(data)
    assert ec.trigger_conditions == ["artifact changes runtime"]  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# EvidenceCluster — bad state rejected
# ---------------------------------------------------------------------------

def test_evidence_cluster_rejects_invalid_state():
    bad = {**VALID_CLUSTER, "state": "unknown_state"}
    with pytest.raises(ValidationError):
        EvidenceCluster.model_validate(bad)


# ---------------------------------------------------------------------------
# EvidenceCluster — missing required fields each raise ValidationError
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("field", ["cluster_id", "phase", "family", "purpose", "state", "findings"])
def test_evidence_cluster_rejects_missing_required_field(field: str):
    data = {k: v for k, v in VALID_CLUSTER.items() if k != field}
    with pytest.raises(ValidationError):
        EvidenceCluster.model_validate(data)


# ---------------------------------------------------------------------------
# INVARIANT_CLUSTER_FAMILIES frozenset
# ---------------------------------------------------------------------------

# The 6 universal_cluster_families flagged invariant: true (NOT gate-selection's
# 7 non_waivable_invariants — a different set). handled_negative_result_followthrough
# is not a universal_cluster_family and is intentionally excluded.
EXPECTED_INVARIANT_FAMILIES = frozenset({
    "authority",
    "side_effects",
    "write_containment",
    "privacy_safety",
    "traceable_state",
    "conservative_failure",
})


def test_invariant_cluster_families_is_frozenset():
    assert isinstance(INVARIANT_CLUSTER_FAMILIES, frozenset)


def test_invariant_cluster_families_has_exactly_six():
    assert len(INVARIANT_CLUSTER_FAMILIES) == 6


def test_invariant_cluster_families_matches_yaml():
    assert INVARIANT_CLUSTER_FAMILIES == EXPECTED_INVARIANT_FAMILIES
